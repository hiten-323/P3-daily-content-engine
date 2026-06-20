"""Cerebras Cloud API provider — generous free tier, very fast inference."""
import os
import logging
import requests as _http

logger = logging.getLogger(__name__)

_URL = "https://api.cerebras.ai/v1/chat/completions"

MODELS: list[str] = os.getenv(
    "CEREBRAS_MODELS",
    "gpt-oss-120b,zai-glm-4.7",
).split(",")


def get_key() -> str:
    return os.environ.get("CEREBRAS_API_KEY", "").strip()


def call(prompt: str, max_tokens: int) -> tuple[str | None, dict]:
    import time
    BACKOFF = [5, 15, 30, 60]
    key = get_key()
    if not key:
        return None, {}

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    for model in MODELS:
        for attempt in range(4):
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
                logger.error("Cerebras %s request exception (attempt %d/4): %s", model, attempt + 1, e)
                if attempt < 3:
                    time.sleep(BACKOFF[attempt])
                    continue
                break

            if resp.status_code == 200:
                body = resp.json()
                msg  = body["choices"][0]["message"]
                # reasoning models put output in reasoning_content when content is empty
                text = msg.get("content") or msg.get("reasoning_content") or ""
                if not text:
                    logger.warning("Cerebras %s returned empty content", model)
                    break
                u = body.get("usage", {})
                return text, {
                    "prompt_tokens":     u.get("prompt_tokens"),
                    "completion_tokens": u.get("completion_tokens"),
                }

            if resp.status_code == 429:
                logger.warning("Cerebras %s rate limited (429) — attempt %d/4 — sleeping", model, attempt + 1)
                if attempt < 3:
                    time.sleep(BACKOFF[attempt])
                    continue
                return None, {"status_code": 429}

            logger.warning("Cerebras %s %s: %s", model, resp.status_code, resp.text[:200])
            return None, {"status_code": resp.status_code}

    return None, {}
