"""
Business priority configuration for Purity Beans.

These weights drive EVERY optimisation decision in the strategy engine.
They encode that building an FMCG brand requires more than consumer sales —
distribution and retail shelf placement are equal or higher value.

Modify these weights as the business evolves:
  • Early stage (now):     distributor and retailer acquisition equally important
  • Growth stage:          shift weight toward consumer_purchase once distribution secured
  • Scale stage:           brand_awareness to defend market share

BUSINESS_PRIORITIES controls content MIX.
AUDIENCE_BUSINESS_VALUES controls how much each LEAD is worth in the optimizer.
"""

# Proportion of weekly content targeted at each business goal.
# Must sum to 1.0.
BUSINESS_PRIORITIES: dict[str, float] = {
    "consumer_purchase":  0.35,   # drive direct sales at p3online.in
    "distributor_leads":  0.35,   # FMCG distribution partnerships
    "retailer_leads":     0.20,   # shelf placement in kirana / modern trade
    "brand_awareness":    0.10,   # top-of-funnel reach
}

# Monetary value multiplier per audience segment.
# A distributor lead is worth 10x a single consumer purchase.
AUDIENCE_BUSINESS_VALUES: dict[str, float] = {
    "distributor":  10.0,    # one deal = thousands of units/month
    "modern_trade":  8.0,    # chain listing = high-volume recurring
    "retailer":      5.0,    # shelf = steady local revenue
    "consumer":      1.0,    # baseline — individual purchase
}

# Maps FMCG business goal → audience segment
PRIORITY_TO_AUDIENCE: dict[str, str] = {
    "consumer_purchase": "consumer",
    "distributor_leads": "distributor",
    "retailer_leads":    "retailer",
    "brand_awareness":   "consumer",   # awareness reaches everyone
}

# Platform where each audience segment is most reachable
AUDIENCE_BEST_PLATFORMS: dict[str, list[str]] = {
    "distributor":  ["linkedin", "whatsapp"],
    "modern_trade": ["linkedin", "email"],
    "retailer":     ["whatsapp", "instagram"],
    "consumer":     ["instagram", "youtube", "facebook"],
}

# Minimum content allocations — ensures no segment is ever fully ignored
MIN_ALLOCATION: dict[str, float] = {
    "consumer_purchase": 0.20,
    "distributor_leads": 0.20,
    "retailer_leads":    0.10,
    "brand_awareness":   0.05,
}


def get_business_value(audience: str, revenue: float = 0.0) -> float:
    """
    Return the business-adjusted value of an audience action.

    For a distributor: even with Rs 0 direct revenue, the lead value is 10x.
    For a consumer:    value = revenue earned.
    """
    multiplier = AUDIENCE_BUSINESS_VALUES.get(audience, 1.0)
    if audience == "consumer":
        return revenue
    # Non-consumer leads — assign notional value per lead
    _lead_values = {
        "distributor":  50_000,   # Rs 50k notional value per qualified lead
        "modern_trade": 40_000,
        "retailer":     10_000,
    }
    return _lead_values.get(audience, 5_000) * multiplier / multiplier   # returns lead value
