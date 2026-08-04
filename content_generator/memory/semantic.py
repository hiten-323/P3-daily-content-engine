"""
Semantic memory for permanent content deduplication.

Similarity engine priority (best → always-available fallback):
  1. sentence-transformers  — pip install sentence-transformers
  2. scikit-learn TF-IDF    — pip install scikit-learn
  3. character n-gram Jaccard — zero dependencies, always works

Memory store: output/content_memory.json  (or SEMANTIC_MEMORY_PATH env var)
Threshold:    0.85 by default              (or SEMANTIC_SIMILARITY_THRESHOLD env var)

Usage:
    from content_generator.memory.semantic import is_too_similar, store_content

    dup, sim = is_too_similar(new_piece)
    if not dup:
        store_content("reel_1_day42", new_piece)
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

_MEMORY_PATH = os.getenv(
    "SEMANTIC_MEMORY_PATH",
    os.path.join("output", "content_memory.json"),
)
_THRESHOLD = float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.85"))
_MAX_STORED = 1000   # rolling window; oldest entries dropped beyond this


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if os.path.exists(_MEMORY_PATH):
        try:
            with open(_MEMORY_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as _e:
            logger.debug("[semantic] optional step failed: %s", _e)
    return []


def _save(memory: list[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(_MEMORY_PATH)), exist_ok=True)
    with open(_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory[-_MAX_STORED:], f, ensure_ascii=False)


# ── Similarity engines ────────────────────────────────────────────────────────

def _ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    """Character n-gram Jaccard similarity. Zero dependencies."""
    def _ngrams(s):
        s = s.lower()
        return set(s[i:i + n] for i in range(max(0, len(s) - n + 1)))
    sa, sb = _ngrams(a), _ngrams(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _tfidf_cosine(a: str, b: str) -> float:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec   = TfidfVectorizer(min_df=1)
        mat   = vec.fit_transform([a, b])
        return float(cosine_similarity(mat[0], mat[1])[0][0])
    except Exception:
        return _ngram_jaccard(a, b)


_st_model = None

def _embed_cosine(a: str, b: str) -> float:
    global _st_model
    try:
        from sentence_transformers import SentenceTransformer, util
        if _st_model is None:
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        embs = _st_model.encode([a, b], convert_to_tensor=True)
        return float(util.cos_sim(embs[0], embs[1]))
    except Exception:
        return _tfidf_cosine(a, b)


def compute_similarity(text_a: str, text_b: str) -> float:
    """Return 0.0–1.0 semantic similarity using the best available engine."""
    if not text_a or not text_b:
        return 0.0
    try:
        import sentence_transformers  # noqa: F401
        return _embed_cosine(text_a, text_b)
    except ImportError:
        pass
    try:
        import sklearn  # noqa: F401
        return _tfidf_cosine(text_a, text_b)
    except ImportError:
        pass
    return _ngram_jaccard(text_a, text_b)


# ── Content text extraction ───────────────────────────────────────────────────

def _extract_text(content: dict) -> str:
    """Pull representative text fields from a content dict."""
    fields = ("hook_text", "hook_spoken", "caption", "content", "body", "title", "headline")
    parts  = [str(content[f]) for f in fields if content.get(f)]
    return " ".join(parts)[:1200]


# ── Public API ────────────────────────────────────────────────────────────────

def is_too_similar(
    new_content: dict,
    threshold: float = None,
) -> tuple[bool, float]:
    """
    Check if new_content is too similar to any stored piece.

    Returns:
        (is_duplicate, max_similarity_score)
        is_duplicate = True means content is too similar; consider regenerating.
    """
    thresh    = threshold if threshold is not None else _THRESHOLD
    new_text  = _extract_text(new_content)
    if not new_text:
        return False, 0.0

    memory  = _load()
    max_sim = 0.0

    for stored in memory:
        stored_text = stored.get("text", "")
        if not stored_text:
            continue
        sim = compute_similarity(new_text, stored_text)
        if sim > max_sim:
            max_sim = sim
        if sim >= thresh:
            logger.warning(
                "[memory] Duplicate (sim=%.2f ≥ %.2f): '%s...'",
                sim, thresh, new_text[:60],
            )
            return True, sim

    return False, round(max_sim, 3)


def store_content(content_id: str, content: dict) -> None:
    """
    Persist a content piece in semantic memory.
    Call after generation, before publishing.
    """
    text = _extract_text(content)
    if not text:
        return
    memory = _load()
    memory.append({"id": content_id, "text": text})
    _save(memory)
    logger.debug("[memory] Stored '%s' (%d chars)", content_id, len(text))


def memory_stats() -> dict:
    """Return stats about the current memory store."""
    mem = _load()
    return {
        "total_stored":    len(mem),
        "similarity_engine": _detect_engine(),
        "threshold":       _THRESHOLD,
    }


def _detect_engine() -> str:
    try:
        import sentence_transformers  # noqa: F401
        return "sentence-transformers"
    except ImportError:
        pass
    try:
        import sklearn  # noqa: F401
        return "sklearn-tfidf"
    except ImportError:
        pass
    return "ngram-jaccard"
