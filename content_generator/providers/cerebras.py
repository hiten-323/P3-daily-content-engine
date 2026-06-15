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
            logger.error("Cerebras %s request exception: %s", model, e)
            continue

        if resp.status_code == 200:
            body = resp.json()
            msg  = body["choices"][0]["message"]
            # reasoning models put output in reasoning_content when content is empty
            text = msg.get("content") or msg.get("reasoning_content") or ""
            if not text:
                logger.warning("Cerebras %s returned empty content", model)
                continue
            u = body.get("usage", {})
            return text, {
                "prompt_tokens":     u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens"),
            }

        logger.warning("Cerebras %s %s: %s", model, resp.status_code, resp.text[:200])
        continue

    return None, {}
