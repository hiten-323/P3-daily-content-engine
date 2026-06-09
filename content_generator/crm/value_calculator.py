"""
Lifetime Value (LTV) calculator for Purity Beans.

This module quantifies EXACTLY why a single distributor lead is worth
more than 10,000 consumer reels reaching zero distributors.

LTV benchmarks (conservative estimates for Purity Beans FMCG):

  DISTRIBUTOR
    Avg monthly GMV per active distributor:  Rs 1,50,000
    Active months expected:                  24
    Margin:                                  25%
    Expected LTV:                            Rs 9,00,000

  MODERN TRADE (chain listing — D-Mart, Big Bazaar, etc.)
    Avg monthly GMV per chain:               Rs 5,00,000
    Active months:                           36
    Margin:                                  20%
    Expected LTV:                            Rs 36,00,000

  RETAILER (kirana / local store)
    Avg monthly GMV per retailer:            Rs 15,000
    Active months:                           18
    Margin:                                  30%
    Expected LTV:                            Rs 81,000

  CONSUMER (D2C)
    Avg order value:                         Rs 450
    Orders per year:                         8
    Customer lifetime:                       2 years
    Expected LTV:                            Rs 7,200

These numbers make the business case for content allocation crystal clear:
  One distributor lead = 125× a consumer purchase
  One modern trade listing = 500× a consumer purchase
"""

# Base LTV assumptions — update as real data accumulates
_LTV_CONFIG: dict[str, dict] = {
    "distributor": {
        "avg_monthly_gmv":     150_000,
        "avg_active_months":   24,
        "margin_pct":          0.25,
        "expected_ltv":        900_000,
        "revenue_per_month":   37_500,   # gmv × margin
    },
    "modern_trade": {
        "avg_monthly_gmv":     500_000,
        "avg_active_months":   36,
        "margin_pct":          0.20,
        "expected_ltv":        3_600_000,
        "revenue_per_month":   100_000,
    },
    "retailer": {
        "avg_monthly_gmv":     15_000,
        "avg_active_months":   18,
        "margin_pct":          0.30,
        "expected_ltv":        81_000,
        "revenue_per_month":   4_500,
    },
    "consumer": {
        "avg_order_value":     450,
        "orders_per_year":     8,
        "avg_lifetime_years":  2,
        "expected_ltv":        7_200,
        "revenue_per_month":   300,
    },
}

# Probability of each stage reaching full active/reordering status
# Used to compute expected value (EV) from a lead at a given stage
_STAGE_EV_MULTIPLIERS: dict[str, dict[str, float]] = {
    "distributor": {
        "inquiry":     0.12,   # 12% of all inquiries become active (cascaded probability)
        "qualified":   0.30,
        "sample_sent": 0.50,
        "trial_order": 0.70,
        "agreement":   0.90,
        "active":      1.00,
    },
    "modern_trade": {
        "inquiry":       0.05,
        "proposal_sent": 0.12,
        "buyer_meeting": 0.30,
        "trial_listed":  0.60,
        "chain_listed":  1.00,
    },
    "retailer": {
        "inquiry":     0.30,
        "sample_sent": 0.48,
        "shelf_listed": 0.80,
        "reordering":   1.00,
    },
    "consumer": {
        "lead":             0.35,
        "first_purchase":   0.45,
        "repeat_customer":  0.60,
        "loyal":            1.00,
        "ambassador":       1.00,
    },
}


def estimate_ltv(segment: str) -> float:
    """Return expected LTV for a segment (full potential, not stage-adjusted)."""
    return float(_LTV_CONFIG.get(segment, {}).get("expected_ltv", 0))


def estimate_expected_value(segment: str, stage: str) -> float:
    """
    Return the stage-adjusted expected value (EV) of a lead.

    EV = LTV × probability_of_reaching_active_from_this_stage

    Example:
        distributor at 'inquiry' → 900,000 × 0.12 = Rs 1,08,000 EV
        distributor at 'trial_order' → 900,000 × 0.70 = Rs 6,30,000 EV
    """
    ltv      = estimate_ltv(segment)
    prob     = _STAGE_EV_MULTIPLIERS.get(segment, {}).get(stage, 0.10)
    return round(ltv * prob, 2)


def get_pipeline_value(leads: list[dict]) -> dict:
    """
    Compute total pipeline value (sum of all lead EVs).

    Returns:
    {
        "total_ev":               Rs 47,32,000,
        "by_segment": {
            "distributor":        Rs 32,40,000,
            "retailer":           Rs 4,86,000,
            "consumer":           Rs 2,52,000,
        },
        "total_leads":            52,
        "weighted_avg_ev_per_lead": Rs 90,000,
    }
    """
    total_ev:  float          = 0.0
    by_segment: dict[str, float] = {}

    for lead in leads:
        seg   = lead.get("segment", "consumer")
        stage = lead.get("stage", "inquiry")
        ev    = estimate_expected_value(seg, stage)
        total_ev                   += ev
        by_segment[seg]             = by_segment.get(seg, 0.0) + ev

    n = max(len(leads), 1)
    return {
        "total_ev":                   round(total_ev, 2),
        "by_segment":                 {k: round(v, 2) for k, v in by_segment.items()},
        "total_leads":                len(leads),
        "weighted_avg_ev_per_lead":   round(total_ev / n, 2),
    }


def get_ltv_table() -> list[dict]:
    """Return full LTV breakdown for all segments — used in dashboard."""
    rows = []
    for segment, cfg in _LTV_CONFIG.items():
        rows.append({
            "segment":      segment,
            "expected_ltv": cfg["expected_ltv"],
            "monthly_revenue": cfg.get("revenue_per_month", 0),
            "ltv_vs_consumer": round(cfg["expected_ltv"] / _LTV_CONFIG["consumer"]["expected_ltv"], 1),
        })
    return sorted(rows, key=lambda x: x["expected_ltv"], reverse=True)


def compute_content_revenue_potential(
    content_id: str,
    leads_generated: int,
    segment: str,
    stage: str = "inquiry",
) -> dict:
    """
    Compute the total revenue potential from leads generated by one content piece.

    Used to rank content by BUSINESS VALUE, not just views.
    """
    ltv   = estimate_ltv(segment)
    ev    = estimate_expected_value(segment, stage)
    total = ev * leads_generated

    return {
        "content_id":       content_id,
        "segment":          segment,
        "leads_generated":  leads_generated,
        "ltv_per_lead":     ltv,
        "ev_per_lead":      ev,
        "total_pipeline_ev": round(total, 2),
    }
