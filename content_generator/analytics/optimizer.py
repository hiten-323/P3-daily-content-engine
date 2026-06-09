"""
Dynamic content strategy optimizer.

Biases today's hook / emotion / angle selections toward historically
high-performing archetypes while preserving creative diversity via
deterministic exploration every 5th day.

Gracefully falls back to round-robin rotation when performance data
is insufficient (< MIN_DATA_SAMPLES entries per archetype).
"""
import logging

logger = logging.getLogger(__name__)

_MIN_DATA_SAMPLES = 3   # trust performance data only after 3+ samples
_EXPLORE_EVERY_N  = 5   # explore a non-top-performer every N days


def get_optimized_pick(bank: list, day: int, label: str = "", offset: int = 0) -> object:
    """
    Return a bank item biased toward high-performing archetypes.

    bank:   list of (name, description) tuples or plain values
    day:    day_number used for deterministic selection
    label:  human label for debug logging
    offset: applied to day before selection (same as rotation.pick offset)
    """
    effective_day = day + offset

    try:
        from content_generator.analytics.metrics_store import get_hook_performance
        perf = get_hook_performance(min_samples=_MIN_DATA_SAMPLES)
    except Exception:
        perf = []

    if not perf:
        # No data yet — plain round-robin
        return bank[effective_day % len(bank)]

    score_map = {p["archetype"]: p["avg_viral_score"] for p in perf}

    # Score every bank item; default 50 for items with no data yet
    scored = []
    for item in bank:
        name = item[0] if isinstance(item, (tuple, list)) else str(item)
        score = score_map.get(name, 50.0)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Exploration day — pick outside top-third to discover new winners
    if effective_day % _EXPLORE_EVERY_N == 0:
        idx = effective_day % len(scored)
        chosen = scored[idx][1]
        logger.debug("[optimizer] %s EXPLORE → %s", label, _name(chosen))
        return chosen

    # Exploitation — top-third with deterministic cycling
    top_n  = max(1, len(scored) // 3)
    idx    = effective_day % top_n
    chosen = scored[idx][1]
    logger.debug(
        "[optimizer] %s EXPLOIT → %s (score=%.1f)",
        label, _name(chosen), scored[idx][0],
    )
    return chosen


def _name(item) -> str:
    if isinstance(item, (tuple, list)):
        return str(item[0])
    return str(item)


def get_strategy_context() -> dict:
    """
    Return a summary of winning strategy for injection into prompts.
    Returns empty dict if no performance data is available yet.
    """
    try:
        from content_generator.analytics.metrics_store import get_hook_performance, get_recent_metrics
        hooks  = get_hook_performance(min_samples=3)
        recent = get_recent_metrics(days=7)
    except Exception:
        return {}

    if not hooks:
        return {}

    top   = hooks[0]
    avg_s = sum(r.get("viral_score", 0) for r in recent) / max(len(recent), 1)

    return {
        "top_performing_hook":    top.get("archetype", ""),
        "top_hook_avg_views":     round(top.get("avg_views", 0)),
        "top_hook_viral_score":   round(top.get("avg_viral_score", 0), 1),
        "all_hooks_ranked":       [h["archetype"] for h in hooks],
        "recent_avg_viral_score": round(avg_s, 1),
        "total_pieces_tracked":   len(recent),
    }
