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

    for model in MODELS:
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
            continue

        if resp.status_code == 200:
            body  = resp.json()
            text  = body["choices"][0]["message"]["content"]
            u     = body.get("usage", {})
            return text, {
                "prompt_tokens":     u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens"),
            }

        logger.warning("DeepSeek %s %s: %s", model, resp.status_code, resp.text[:200])
        return None, {"status_code": resp.status_code}

    return None, {}
