"""
Hook optimizer — selects the best hook archetype for a given audience + day.

Combines three signals:
  1. Historical viral score (from analytics/metrics_store)
  2. Historical revenue attribution (which hooks actually drove purchases)
  3. Business priority weight for the target audience

When data is sparse, falls back to deterministic rotation.
"""
import logging

logger = logging.getLogger(__name__)

_MIN_SAMPLES = 3


def get_best_hook(
    bank: list[tuple],
    day: int,
    audience: str = "consumer",
    offset: int   = 0,
) -> tuple:
    """
    Return the optimal hook for given audience + day.

    Scoring formula:
        hook_score = viral_score * 0.5 + revenue_score * 0.3 + audience_fit * 0.2

    Falls back to plain round-robin when < MIN_SAMPLES data available.
    """
    scores = _score_hooks(bank, audience)
    if not scores:
        return bank[(day + offset) % len(bank)]

    # Sort by composite score descending
    scores.sort(key=lambda x: x["score"], reverse=True)

    # Top third pool, cycle by day for diversity
    top_n  = max(1, len(scores) // 3)
    idx    = (day + offset) % top_n
    winner = scores[idx]

    logger.debug(
        "[hook_optimizer] audience=%s → %s (score=%.1f)",
        audience, winner["name"], winner["score"],
    )
    return winner["item"]


def _score_hooks(bank: list[tuple], audience: str) -> list[dict]:
    """Score each hook in the bank using available performance data."""
    try:
        from content_generator.analytics.metrics_store import get_hook_performance
        from content_generator.analytics.conversion_analyzer import get_hook_roi
        from content_generator.strategy.business_priorities import AUDIENCE_BUSINESS_VALUES

        perf_data = {p["archetype"]: p for p in get_hook_performance(min_samples=_MIN_SAMPLES)}
        roi_data  = {r["hook_archetype"]: r for r in get_hook_roi(days=60)}
        if not perf_data:
            return []

        audience_w = AUDIENCE_BUSINESS_VALUES.get(audience, 1.0) / 10.0

    except Exception:
        return []

    results = []
    for item in bank:
        name = item[0] if isinstance(item, (tuple, list)) else str(item)
        p    = perf_data.get(name, {})
        r    = roi_data.get(name, {})

        viral_score   = p.get("avg_viral_score", 50.0)
        revenue       = float(r.get("total_revenue", 0))
        revenue_score = min(revenue / 10_000, 1.0) * 100  # normalise to 0-100

        composite = (viral_score * 0.50 + revenue_score * 0.30 + audience_w * 100 * 0.20)
        results.append({"name": name, "score": round(composite, 1), "item": item})

    return results


def get_hook_performance_table() -> list[dict]:
    """
    Return a ranked table of hooks with both viral and revenue scores.
    Used by the dashboard.
    """
    try:
        from content_generator.analytics.metrics_store import get_hook_performance
        from content_generator.analytics.conversion_analyzer import get_hook_roi
        perf = {p["archetype"]: p for p in get_hook_performance(min_samples=1)}
        roi  = {r["hook_archetype"]: r for r in get_hook_roi(days=90)}

        combined = []
        for name, p in perf.items():
            r = roi.get(name, {})
            combined.append({
                "hook":           name,
                "avg_views":      round(p.get("avg_views", 0)),
                "avg_viral_score": round(p.get("avg_viral_score", 0), 1),
                "total_revenue":  round(float(r.get("total_revenue", 0)), 2),
                "samples":        p.get("sample_count", 0),
            })
        return sorted(combined, key=lambda x: x["avg_viral_score"], reverse=True)
    except Exception:
        return []
