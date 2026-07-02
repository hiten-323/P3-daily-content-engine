"""
Continuous Learning Engine — closes the loop between published content
and future generation.

Flow:
  1. record_performance() — store metrics for a published asset
     (called manually or by an insights fetcher when metrics are available)
  2. analyze() — classify each recorded post as WINNER / NEUTRAL / FAILED
     based on relative engagement
  3. get_learning_block() — returns a text block injected into every
     generation prompt: patterns to repeat, patterns to never repeat

Storage: output/learning/performance_log.json (append-only, survives runs
because output/ is committed by the GitHub Actions workflow).
"""
import datetime
import json
import logging
import os

logger = logging.getLogger(__name__)

_LEARNING_DIR = os.getenv("LEARNING_DIR", os.path.join("output", "learning"))
_LOG_PATH     = os.path.join(_LEARNING_DIR, "performance_log.json")

# Metrics we track per post
METRIC_FIELDS = [
    "views", "reach", "watch_time_s", "avg_view_duration_s", "completion_rate",
    "shares", "saves", "comments", "profile_visits", "follows_gained", "likes",
]


def _load_log() -> list[dict]:
    if not os.path.exists(_LOG_PATH):
        return []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("[learning] Could not read log: %s", e)
        return []


def _save_log(entries: list[dict]) -> None:
    os.makedirs(_LEARNING_DIR, exist_ok=True)
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def record_performance(
    asset_id: str,
    track: str,
    hook: str = "",
    topic: str = "",
    format_used: str = "",
    posted_at: str = "",
    metrics: dict = None,
    notes: str = "",
) -> dict:
    """
    Record performance metrics for a published post.

    asset_id : e.g. "growth_reel_day172" or "reel_1_day172"
    track    : "growth" or "brand"
    metrics  : dict with any of METRIC_FIELDS
    """
    entries = _load_log()
    entry = {
        "asset_id":   asset_id,
        "track":      track,
        "hook":       hook,
        "topic":      topic,
        "format":     format_used,
        "posted_at":  posted_at or datetime.date.today().isoformat(),
        "recorded_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "metrics":    {k: v for k, v in (metrics or {}).items() if k in METRIC_FIELDS},
        "notes":      notes,
    }
    entries.append(entry)
    _save_log(entries)
    logger.info("[learning] Recorded performance for %s (%s)", asset_id, track)
    return entry


def _engagement_score(m: dict) -> float:
    """Weighted engagement score. Follows and shares weigh most — they compound."""
    return (
        m.get("follows_gained", 0) * 10.0
        + m.get("shares", 0)        * 5.0
        + m.get("saves", 0)         * 4.0
        + m.get("comments", 0)      * 3.0
        + m.get("profile_visits", 0) * 2.0
        + m.get("likes", 0)         * 1.0
        + m.get("views", 0)         * 0.01
    )


def analyze() -> dict:
    """
    Classify all recorded posts relative to the account's own median.
    Returns {"winners": [...], "failed": [...], "median_score": float, "count": int}
    """
    entries = _load_log()
    scored = [(e, _engagement_score(e.get("metrics", {}))) for e in entries if e.get("metrics")]
    if not scored:
        return {"winners": [], "failed": [], "median_score": 0.0, "count": 0}

    scores = sorted(s for _, s in scored)
    median = scores[len(scores) // 2]

    winners = [e for e, s in scored if s >= median and s > 0]
    failed  = [e for e, s in scored if s <= median * 0.5]
    return {"winners": winners, "failed": failed, "median_score": median, "count": len(scored)}


def get_learning_block(max_items: int = 5) -> str:
    """
    Return a prompt-injectable text block summarizing what worked and what failed.
    Empty string when there is not enough data yet — prompts stay clean early on.
    """
    result = analyze()
    if result["count"] < 3:
        return ""  # not enough data to learn from yet

    lines = ["PERFORMANCE LEARNINGS (from this account's actual published posts):"]

    if result["winners"]:
        lines.append("PATTERNS THAT WORKED — lean into these:")
        for e in result["winners"][:max_items]:
            desc = " | ".join(filter(None, [e.get("hook"), e.get("topic"), e.get("format")]))
            if desc:
                lines.append(f"  + {desc}")

    if result["failed"]:
        lines.append("PATTERNS THAT FAILED — never repeat these:")
        for e in result["failed"][:max_items]:
            desc = " | ".join(filter(None, [e.get("hook"), e.get("topic"), e.get("format")]))
            if desc:
                lines.append(f"  - {desc}")

    return "\n".join(lines) if len(lines) > 1 else ""
