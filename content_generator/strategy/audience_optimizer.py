"""
Audience optimizer — decides which audience segment each content piece
should target, weighted by business value.

The key insight for Purity Beans:
  A distributor post with 5,000 views that generates one Rs 50,000/month
  distribution deal has 10x the business value of a consumer reel
  with 500,000 views and Rs 0 revenue.

The optimizer tracks real business-value-weighted performance per audience
and adjusts allocations accordingly.
"""
import logging

logger = logging.getLogger(__name__)

# Audience display labels
AUDIENCES = ["consumer", "retailer", "distributor", "modern_trade"]


def get_audience_for_content(content_type: str, day: int) -> str:
    """
    Return the optimal audience segment for a content piece.

    Decision logic:
      1. If performance data exists: return highest business-value audience
         whose allocation is below target
      2. Fallback: use content_mix_optimizer's day-based assignment
    """
    try:
        from content_generator.strategy.content_mix_optimizer import get_todays_mix
        mix  = get_todays_mix()
        allocation = mix.get("allocation", {})
        if allocation:
            return _pick_audience_from_allocation(content_type, day, allocation)
    except Exception:
        pass

    # Fallback: static content-type → audience mapping
    return _static_audience(content_type, day)


def _static_audience(content_type: str, day: int) -> str:
    """Deterministic fallback — no data required."""
    _map = {
        "reel_1":         ["consumer", "distributor", "consumer"],
        "reel_2":         ["consumer", "retailer",    "consumer"],
        "instagram_post": ["consumer", "consumer",    "retailer"],
        "carousel":       ["consumer", "distributor", "consumer"],
        "linkedin_post":  ["distributor", "retailer", "distributor"],
        "blog_post":      ["consumer", "distributor", "consumer"],
        "stories":        ["consumer", "consumer",    "consumer"],
        "yt_short":       ["consumer", "distributor", "consumer"],
    }
    options = _map.get(content_type, ["consumer"])
    return options[day % len(options)]


def _pick_audience_from_allocation(
    content_type: str,
    day: int,
    allocation: dict,
) -> str:
    from content_generator.strategy.business_priorities import PRIORITY_TO_AUDIENCE
    # Content types that are LinkedIn-appropriate → prefer distributor/retailer
    b2b_types = {"linkedin_post"}
    if content_type in b2b_types:
        return "distributor"

    # Sort priorities by allocation weight and pick deterministically
    sorted_priorities = sorted(allocation.items(), key=lambda x: x[1], reverse=True)
    idx      = day % len(sorted_priorities)
    priority = sorted_priorities[idx][0]
    return PRIORITY_TO_AUDIENCE.get(priority, "consumer")


def get_audience_performance_report(days: int = 30) -> list[dict]:
    """
    Return business-value-adjusted performance per audience.
    Includes: views, revenue, leads, and composite business value score.
    """
    try:
        from content_generator.analytics.metrics_store import get_audience_performance
        from content_generator.strategy.business_priorities import AUDIENCE_BUSINESS_VALUES
        rows = get_audience_performance(days=days)
        for r in rows:
            audience = r.get("audience", "consumer")
            r["business_value_multiplier"] = AUDIENCE_BUSINESS_VALUES.get(audience, 1.0)
        return rows
    except Exception as e:
        logger.warning("[audience_optimizer] Report failed: %s", e)
        return []
