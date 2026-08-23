"""OpenRouter API provider (last-resort fallback)."""
import os
import logging
import requests as _http

from content_generator.rotation import WEBSITE_URL

logger = logging.getLogger(__name__)

_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS: list[str] = os.getenv(
    "OPENROUTER_MODELS",
    "meta-llama/llama-3.3-70b-instruct:free",
).split(",")


def get_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def call(prompt: str, max_tokens: int) -> tuple[str | None, dict]:
    """
    Returns (text | None, usage_dict).
    Tries each model once — retry logic is handled by the router.
    """
    key = get_key()
    if not key:
        return None, {}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  f"https://{WEBSITE_URL}",
        "X-Title":       "Purity Beans Social Engine",
    }

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
            logger.error("OpenRouter %s request exception: %s", model, e)
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

        logger.warning("OpenRouter %s %s: %s", model, resp.status_code, resp.text[:200])
        return None, {"status_code": resp.status_code, "model": model,
                      "error": resp.text}

    return None, {}
