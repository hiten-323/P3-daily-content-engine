"""DeepSeek API provider — free tier, strong content generation."""
import os
import logging
import requests as _http

logger = logging.getLogger(__name__)

_URL = "https://api.deepseek.com/chat/completions"

MODELS: list[str] = os.getenv(
    "DEEPSEEK_MODELS",
    "deepseek-chat",
).split(",")


def get_key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def call(prompt: str, max_tokens: int) -> tuple[str | None, dict]:
    key = get_key()
    if not key:
        return None, {}

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_failure: dict = {}

    for model in (m.strip() for m in MODELS if m.strip()):
        try:
            resp = _http.post(
                _URL,
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.92,
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
        except Exception as e:
            logger.error("DeepSeek %s request exception: %s", model, e)
            last_failure = {"status_code": 0, "model": model, "error": str(e)}
            continue

        if resp.status_code == 200:
            try:
                body = resp.json()
                text = body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.warning("DeepSeek %s returned malformed success payload: %s", model, e)
                last_failure = {"status_code": 200, "model": model,
                                "error": f"malformed success payload: {e}"}
                continue
            u = body.get("usage", {})
            return text, {
                "prompt_tokens": u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens"),
                "model": model,
            }

        last_failure = {"status_code": resp.status_code, "model": model,
                        "error": resp.text}
        if resp.status_code == 402:
            # Insufficient balance — treat same as quota exhaustion, skip provider.
            logger.warning("DeepSeek %s: 402 Insufficient Balance — skipping provider", model)
            last_failure["status_code"] = 429
            continue
        logger.warning("DeepSeek %s %s: %s", model, resp.status_code, resp.text[:200])
        if resp.status_code in (401, 403):
            return None, last_failure
        # Model/client/server errors may affect only this model; continue.
        continue

    return None, last_failure
