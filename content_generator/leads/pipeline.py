"""
Pipeline stage definitions for every audience segment.

Purity Beans has four distinct sales motions:

  DISTRIBUTOR  — longest cycle, highest value, relationship-driven
  MODERN TRADE — enterprise chain stores, procurement-driven
  RETAILER     — kirana / local shops, fast cycle
  CONSUMER     — D2C, shortest cycle, volume-driven

Stage velocity benchmarks tell the system when a lead is stalling
so the nurture engine can intervene automatically.
"""

# Stage definitions per segment — ORDER MATTERS (earlier = lower stage index)
PIPELINE_STAGES: dict[str, list[str]] = {
    "distributor": [
        "inquiry",       # initial DM / call / form fill
        "qualified",     # confirmed territory, intent verified
        "sample_sent",   # product samples dispatched
        "trial_order",   # first paid (small) order placed
        "agreement",     # distribution agreement signed
        "active",        # regular monthly orders flowing
        "churned",       # stopped ordering
    ],
    "modern_trade": [
        "inquiry",
        "proposal_sent",   # formal business proposal submitted
        "buyer_meeting",   # meeting with purchase manager / buyer
        "trial_listed",    # small trial listing approved
        "chain_listed",    # full chain rollout
        "churned",
    ],
    "retailer": [
        "inquiry",
        "sample_sent",
        "shelf_listed",    # product physically on the shelf
        "reordering",      # active reorders
        "churned",
    ],
    "consumer": [
        "lead",            # opted in / DM'd / form submitted
        "first_purchase",  # placed first order
        "repeat_customer", # 2–4 purchases
        "loyal",           # 5+ purchases
        "ambassador",      # referring others / UGC creator
    ],
}

# Max days in a stage before the lead is considered stalling
# → triggers automatic nurture nudge
STAGE_MAX_DAYS: dict[str, dict[str, int]] = {
    "distributor": {
        "inquiry":     3,
        "qualified":   7,
        "sample_sent": 14,
        "trial_order": 30,
        "agreement":   45,
    },
    "modern_trade": {
        "inquiry":       5,
        "proposal_sent": 14,
        "buyer_meeting": 30,
        "trial_listed":  60,
    },
    "retailer": {
        "inquiry":     2,
        "sample_sent": 7,
        "shelf_listed": 30,
    },
    "consumer": {
        "lead":            7,
        "first_purchase": 30,
        "repeat_customer": 60,
    },
}

# Probability of advancing to the next stage from each current stage
# Used for pipeline revenue forecasting
STAGE_CONVERSION_RATES: dict[str, dict[str, float]] = {
    "distributor": {
        "inquiry":     0.40,   # 40% of inquiries qualify
        "qualified":   0.60,   # 60% of qualified get samples
        "sample_sent": 0.50,   # 50% place a trial order
        "trial_order": 0.70,   # 70% of trial orders → agreement
        "agreement":   0.90,   # 90% of agreements become active
    },
    "modern_trade": {
        "inquiry":       0.20,
        "proposal_sent": 0.30,
        "buyer_meeting": 0.40,
        "trial_listed":  0.60,
    },
    "retailer": {
        "inquiry":     0.50,
        "sample_sent": 0.60,
        "shelf_listed": 0.80,
    },
    "consumer": {
        "lead":             0.35,
        "first_purchase":   0.45,
        "repeat_customer":  0.60,
        "loyal":            0.40,
    },
}


def get_stage_index(segment: str, stage: str) -> int:
    """Return the 0-based position of a stage in the segment pipeline."""
    stages = PIPELINE_STAGES.get(segment, [])
    try:
        return stages.index(stage)
    except ValueError:
        return -1


def get_next_stage(segment: str, current_stage: str) -> str | None:
    """Return the next stage name, or None if already at terminal stage."""
    stages = PIPELINE_STAGES.get(segment, [])
    idx    = get_stage_index(segment, current_stage)
    if idx < 0 or idx >= len(stages) - 1:
        return None
    next_s = stages[idx + 1]
    return next_s if next_s != "churned" else None


def is_stalling(segment: str, stage: str, days_in_stage: int) -> bool:
    """Return True if a lead has been in a stage longer than the max benchmark."""
    max_days = STAGE_MAX_DAYS.get(segment, {}).get(stage)
    if max_days is None:
        return False
    return days_in_stage > max_days


def get_conversion_probability(segment: str, stage: str) -> float:
    """Return the probability of this lead advancing to the next stage."""
    return STAGE_CONVERSION_RATES.get(segment, {}).get(stage, 0.3)


def cumulative_conversion_to_active(segment: str, from_stage: str) -> float:
    """
    Return the probability of reaching 'active'/'reordering'/'loyal'
    from the given stage — product of all intermediate conversion rates.
    """
    stages = PIPELINE_STAGES.get(segment, [])
    terminal_map = {
        "distributor":  "active",
        "modern_trade": "chain_listed",
        "retailer":     "reordering",
        "consumer":     "loyal",
    }
    terminal = terminal_map.get(segment, stages[-1] if stages else "")

    idx_start   = get_stage_index(segment, from_stage)
    idx_terminal = get_stage_index(segment, terminal)

    if idx_start < 0 or idx_terminal < 0 or idx_start >= idx_terminal:
        return 0.0

    prob = 1.0
    rates = STAGE_CONVERSION_RATES.get(segment, {})
    for stage in stages[idx_start:idx_terminal]:
        prob *= rates.get(stage, 0.3)
    return round(prob, 4)
