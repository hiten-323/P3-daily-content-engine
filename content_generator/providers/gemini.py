"""Gemini API provider."""
import os
import logging
import requests as _http

logger = logging.getLogger(__name__)

_BASE  = "https://generativelanguage.googleapis.com/v1beta/models"
_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def get_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def call(prompt: str, max_tokens: int) -> tuple[str | None, dict]:
    """
    Returns (text | None, usage_dict).
    usage_dict is empty if the provider doesn't return token counts.
    """
    key = get_key()
    if not key:
        return None, {}

    url = f"{_BASE}/{_MODEL}:generateContent?key={key}"
    try:
        resp = _http.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.92},
            },
            timeout=120,
        )
    except Exception as e:
        logger.error("Gemini request exception: %s", e)
        return None, {}

    if resp.status_code != 200:
        logger.warning("Gemini %s: %s", resp.status_code, resp.text[:200])
        return None, {"status_code": resp.status_code}

    data       = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        logger.warning("Gemini returned no candidates")
        return None, {}

    text = (
        candidates[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text")
    )

    # Gemini returns usageMetadata on the response root
    meta  = data.get("usageMetadata", {})
    usage = {
        "prompt_tokens":     meta.get("promptTokenCount"),
        "completion_tokens": meta.get("candidatesTokenCount"),
    }

    if not text:
        logger.warning("Gemini candidate had no text")
        return None, usage

    return text, usage
