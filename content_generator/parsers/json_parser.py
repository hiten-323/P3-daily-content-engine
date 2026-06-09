"""
JSON extraction with json_repair as primary strategy, multi-strategy fallback.
json_repair is an optional dependency — if not installed, falls back to
regex-based extraction with trailing-comma repair.
"""
import re
import json
import logging

logger = logging.getLogger(__name__)

# Optional dependency — graceful fallback if not installed
try:
    import json_repair as _json_repair
    _HAS_JSON_REPAIR = True
except ImportError:
    _json_repair = None
    _HAS_JSON_REPAIR = False
    logger.debug("json_repair not installed — using built-in fallback parser")


def _sanitize_control_chars(text: str) -> str:
    """Replace literal control characters inside JSON string values."""
    _ESC = {'\n': '\\n', '\t': '\\t', '\r': '\\r', '\b': '\\b', '\f': '\\f'}
    result = []
    in_str = escaping = False
    for ch in text:
        if escaping:
            result.append(ch); escaping = False; continue
        if ch == '\\':
            escaping = True; result.append(ch); continue
        if ch == '"':
            in_str = not in_str; result.append(ch); continue
        if in_str and ord(ch) < 0x20:
            result.append(_ESC.get(ch, '')); continue
        result.append(ch)
    return ''.join(result)


def _legacy_extract(raw: str) -> dict:
    """
    Regex-based extraction — three strategies in order:
    1. Direct parse
    2. Strip markdown fences
    3. Outermost { ... } with trailing-comma repair
    """
    cleaned = raw.strip()

    try:
        return json.loads(_sanitize_control_chars(cleaned))
    except json.JSONDecodeError:
        pass

    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
    if fence:
        try:
            return json.loads(_sanitize_control_chars(fence.group(1).strip()))
        except json.JSONDecodeError:
            pass

    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        candidate = _sanitize_control_chars(match.group(0))
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Fallback extraction failed: {e}. First 400 chars: {raw[:400]}",
                candidate, e.pos,
            ) from e

    raise ValueError(f"No JSON object found. First 300 chars: {raw[:300]}")


def extract(raw: str) -> dict:
    """
    Parse JSON from a raw LLM response string.
    Uses json_repair if available (handles malformed JSON automatically),
    otherwise falls back to the legacy multi-strategy extractor.
    """
    if _HAS_JSON_REPAIR:
        try:
            result = _json_repair.loads(raw)
            if isinstance(result, dict):
                return result
            # json_repair may return a list for malformed input — handle it
            logger.warning("json_repair returned non-dict — falling back to legacy extractor")
        except Exception as e:
            logger.warning("json_repair failed (%s) — falling back to legacy extractor", e)

    return _legacy_extract(raw)
