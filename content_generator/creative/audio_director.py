"""
Audio Director — picks background audio for content, in two compliant modes.

Mode A (automatable): for reel VIDEOS the engine renders itself, embed a
mood-matched royalty-free track from music_library/.

Mode B (recommendation): Instagram/Facebook do NOT allow third-party apps to
attach in-app library music via API — so for content you post by hand, the
engine outputs the content category + the exact TYPE of trending audio to pick
in-app (one tap). This is the only compliant way to use trending audio.

No trend-scraping (no compliant free API for "trending IG audio"; scraping is
ToS-risky). Selection = brand fit + audience match + learned performance.
"""
from __future__ import annotations
import glob as _glob
import logging
import os

logger = logging.getLogger(__name__)

def _music_dir() -> str:
    return os.getenv("MUSIC_LIBRARY_DIR", "music_library")

# Content category -> (mood tag used to pick a local track, in-app audio
# recommendation for the manual posting path).
AUDIO_MAP = {
    "coffee_aesthetic": ("lofi",      "trending lo-fi / café instrumental"),
    "morning_routine":  ("calm",      "soft trending piano / acoustic"),
    "productivity":     ("upbeat",    "light trending upbeat instrumental"),
    "health_wellness":  ("calm",      "calm ambient trending audio"),
    "behind_scenes":    ("upbeat",    "trending instrumental (mid-energy)"),
    "educational":      ("ambient",   "light ambient trending audio (low, non-distracting)"),
    "founder_story":    ("cinematic", "soft cinematic / emotional trending audio"),
    "motivation":       ("cinematic", "motivational cinematic trending audio"),
    "product_showcase": ("premium",   "premium trending audio / high-energy for launches"),
    "recipe":           ("upbeat",    "kitchen/food trending audio or ASMR"),
    "lifestyle":        ("lofi",      "aesthetic trending lo-fi"),
    "meme":             ("upbeat",    "the current viral meme sound (highest reach)"),
    "trend":            ("upbeat",    "the exact trending audio the format uses"),
}

# Keyword -> category, for auto-classifying a piece of content.
_KEYWORDS = {
    "founder_story":   ["founder", "i started", "my journey", "built", "bootstrap", "lesson"],
    "recipe":          ["recipe", "brew", "how to make", "barista", "2-minute", "cold brew"],
    "educational":     ["did you know", "how to", "what is", "guide", "read the label", "chicory", "freeze"],
    "morning_routine": ["morning", "routine", "start your day", "wake"],
    "product_showcase":["shop", "buy", "launch", "new", "gifting", "variant"],
    "motivation":      ["grind", "hustle", "focus", "discipline"],
    "meme":            ["pov", "when you", "nobody:", "me:"],
}
_DEFAULT_CATEGORY = "coffee_aesthetic"


def detect_category(text: str) -> str:
    t = (text or "").lower()
    for cat, kws in _KEYWORDS.items():
        if any(k in t for k in kws):
            return cat
    return _DEFAULT_CATEGORY


def _learned_bias() -> dict:
    """Avg engagement score per audio_category from past posts (learning loop)."""
    scores: dict[str, list] = {}
    try:
        from content_generator.core.learning_engine import _load_log, _engagement_score
        for e in _load_log():
            cat = (e.get("audio_category") or "").strip()
            if cat and e.get("metrics"):
                scores.setdefault(cat, []).append(_engagement_score(e["metrics"]))
    except Exception:
        return {}
    return {c: sum(v) / len(v) for c, v in scores.items() if v}


def select_local_track(category: str, day: int = 0) -> str | None:
    """
    Pick a royalty-free track from music_library/ matching the category's mood.
    Founder drops files named like 'lofi_1.mp3', 'calm_cafe.mp3' etc.
    Returns a path or None. Reels without embedded audio must be flagged for manual in-app audio before publishing.
    """
    if not os.path.isdir(_music_dir()):
        return None
    mood = AUDIO_MAP.get(category, AUDIO_MAP[_DEFAULT_CATEGORY])[0]
    files = []
    for ext in ("*.mp3", "*.m4a", "*.wav", "*.aac"):
        files += _glob.glob(os.path.join(_music_dir(), ext))
    if not files:
        return None
    # Prefer files whose name contains the mood; else any track.
    mood_files = [f for f in files if mood in os.path.basename(f).lower()]
    pool = mood_files or files
    return sorted(pool)[day % len(pool)]


def get_audio_plan(text: str, day: int = 0) -> dict:
    """
    Full audio decision for one piece of content.
    Returns: category, mood, local_track (auto-embed path or None),
    recommendation (in-app manual instruction), confidence, reason.
    """
    category = detect_category(text)
    mood, recommendation = AUDIO_MAP.get(category, AUDIO_MAP[_DEFAULT_CATEGORY])
    track = select_local_track(category, day)

    bias = _learned_bias()
    confidence = 0.5
    reason = f"Content classified as '{category}' -> {mood} mood."
    if category in bias:
        # scale confidence by how this category ranks vs others
        best = max(bias.values()) or 1
        confidence = round(min(0.9, 0.5 + 0.4 * (bias[category] / best)), 2)
        reason += f" Past '{category}' audio posts perform at {bias[category]:.0f} avg score."
    else:
        reason += " No performance history yet — exploring."

    return {
        "audio_category": category,
        "mood": mood,
        "local_track": track,                    # Mode A: auto-embed (or None)
        "recommendation": recommendation,         # Mode B: pick this in-app
        "manual_instruction": (
            f"When posting by hand, add {recommendation} from the app's music "
            f"library (trending audio gives the reach boost the API can't)."
        ),
        "confidence": confidence,
        "reason": reason,
    }
