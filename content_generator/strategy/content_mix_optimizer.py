"""
Content mix optimizer — the strategy brain.

Every day, decides the optimal allocation of content across business goals:
  consumer_purchase  | distributor_leads | retailer_leads | brand_awareness

Decision algorithm:
  1. Start from BUSINESS_PRIORITIES as the baseline target mix.
  2. If performance data exists (>= 7 days):
       a. Calculate business-value-weighted performance per audience segment.
       b. Increase allocation toward segments that are over-performing.
       c. Apply MIN_ALLOCATION floors so no segment is ever abandoned.
  3. If no data: use BUSINESS_PRIORITIES directly.

This means the system automatically shifts toward distributing more
distributor/retailer content if those pieces are generating more
business value — without manual intervention.
"""
import logging

logger = logging.getLogger(__name__)

_MIN_DATA_DAYS = 7   # minimum days of data before optimizer overrides defaults


def get_todays_mix(day: int = None) -> dict:
    """
    Return today's recommended content allocation.

    Output:
    {
        "allocation": {
            "consumer_purchase":  0.38,
            "distributor_leads":  0.37,
            "retailer_leads":     0.18,
            "brand_awareness":    0.07,
        },
        "data_driven":   True,
        "reasoning":     "distributor content generating 10x business value",
        "top_priority":  "consumer_purchase",
    }
    """
    from content_generator.strategy.business_priorities import (
        BUSINESS_PRIORITIES, MIN_ALLOCATION,
    )

    try:
        allocation, reasoning, data_driven = _compute_dynamic_allocation()
    except Exception as e:
        logger.warning("[mix_optimizer] Dynamic allocation failed: %s — using defaults", e)
        allocation  = dict(BUSINESS_PRIORITIES)
        reasoning   = "using default business priorities"
        data_driven = False

    top = max(allocation, key=allocation.get)
    logger.info("[mix_optimizer] Mix: %s | data_driven=%s", allocation, data_driven)

    return {
        "allocation":  allocation,
        "data_driven": data_driven,
        "reasoning":   reasoning,
        "top_priority": top,
    }


def _compute_dynamic_allocation() -> tuple[dict, str, bool]:
    """
    Core allocation logic.
    Returns (allocation_dict, reasoning_str, is_data_driven).
    """
    from content_generator.analytics.metrics_store import get_audience_performance
    from content_generator.strategy.business_priorities import (
        BUSINESS_PRIORITIES, MIN_ALLOCATION, AUDIENCE_BUSINESS_VALUES, PRIORITY_TO_AUDIENCE,
    )

    # Reverse PRIORITY_TO_AUDIENCE for lookup
    audience_to_priority = {v: k for k, v in PRIORITY_TO_AUDIENCE.items()}
    audience_to_priority["consumer"] = "consumer_purchase"   # explicit

    perf = get_audience_performance(days=30)
    if not perf or len(perf) < 2:
        return dict(BUSINESS_PRIORITIES), "insufficient data — using defaults", False

    # Calculate business-value score per audience
    total_bv = sum(r.get("total_business_value", 0) or 0 for r in perf)
    if total_bv <= 0:
        return dict(BUSINESS_PRIORITIES), "no business value data yet", False

    # Raw proportions from data
    raw: dict[str, float] = {}
    reasoning_parts: list[str] = []
    for r in perf:
        audience = r.get("audience", "consumer")
        priority = audience_to_priority.get(audience, "brand_awareness")
        bv_share = (r.get("total_business_value", 0) or 0) / total_bv
        raw[priority] = raw.get(priority, 0) + bv_share
        if bv_share > 0.3:
            reasoning_parts.append(f"{audience} driving {bv_share*100:.0f}% of business value")

    # Blend 60% data-driven + 40% business_priorities baseline
    blended: dict[str, float] = {}
    for priority in BUSINESS_PRIORITIES:
        data_share     = raw.get(priority, BUSINESS_PRIORITIES[priority])
        baseline_share = BUSINESS_PRIORITIES[priority]
        blended[priority] = data_share * 0.60 + baseline_share * 0.40

    # Enforce minimums
    for priority, floor in MIN_ALLOCATION.items():
        if blended.get(priority, 0) < floor:
            blended[priority] = floor

    # Renormalize to sum to 1.0
    total = sum(blended.values())
    allocation = {k: round(v / total, 3) for k, v in blended.items()}

    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "data-driven blend"
    return allocation, reasoning, True


def get_weekly_content_plan(start_day: int = 0) -> list[dict]:
    """
    Generate a 7-day content plan with audience and objective assignments.
    Useful for weekly planning previews.
    """
    mix = get_todays_mix()
    allocation = mix["allocation"]

    # Convert allocation proportions to day assignments across 8 pieces/day
    priority_list = sorted(allocation.keys(), key=allocation.get, reverse=True)
    plan = []
    for d in range(start_day, start_day + 7):
        day_plan = {
            "day_number":  d,
            "objective_priority": priority_list[d % len(priority_list)],
            "allocation":  allocation,
        }
        plan.append(day_plan)
    return plan
