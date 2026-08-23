"""Groq API provider."""
import os
import logging
import requests as _http

logger = logging.getLogger(__name__)

_URL = "https://api.groq.com/openai/v1/chat/completions"

# Env-configurable so models can be updated without a code change
MODELS: list[str] = os.getenv(
    "GROQ_MODELS",
    "llama-3.3-70b-versatile,llama-3.1-8b-instant",
).split(",")


def get_key() -> str:
    return os.environ.get("GROQ_API_KEY", "").strip()


def call(prompt: str, max_tokens: int) -> tuple[str | None, dict]:
    """
    Tries each model in MODELS in order.
    Returns (text | None, usage_dict) for the first successful response.
    """
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
            logger.error("Groq %s request exception: %s", model, e)
            continue

        if resp.status_code == 200:
            body  = resp.json()
            text  = body["choices"][0]["message"]["content"]
            u     = body.get("usage", {})
            usage = {
                "prompt_tokens":     u.get("prompt_tokens"),
                "completion_tokens": u.get("completion_tokens"),
            }
            return text, usage

        logger.warning("Groq %s %s: %s", model, resp.status_code, resp.text[:200])
        return None, {"status_code": resp.status_code, "model": model,
                      "error": resp.text}

    return None, {}
