"""
CTA optimizer — selects the highest-converting call-to-action for a given
objective and audience segment.

Sources ranked by priority:
  1. Measured click-through + conversion rate from cta_performance table
  2. Business-priority-weighted defaults
  3. Static fallback copy

Feed real data:
    from content_generator.analytics.metrics_store import record_cta_click
    record_cta_click("Buy at p3online.in", objective="Consumer Purchase",
                     audience="consumer", converted=True, revenue=450)
"""
import logging

logger = logging.getLogger(__name__)

# Default CTA copy per (objective, audience) — used until live data accumulates
_DEFAULT_CTAS: dict[tuple[str, str], list[str]] = {
    ("Consumer Purchase",       "consumer"):     [
        "Buy at p3online.in — Rs 18 per cup, free delivery",
        "Order now at p3online.in",
        "Try Purity Beans → p3online.in",
    ],
    ("Consumer Purchase",       "retailer"):     [
        "Stock Purity Beans — WhatsApp for wholesale pricing",
        "Retail enquiries: WhatsApp us now",
    ],
    ("Distributor Acquisition", "distributor"):  [
        "DM for distribution partnership in your region",
        "Become a Purity Beans distributor — DM now",
        "Distribution enquiry: call or WhatsApp us",
    ],
    ("Retailer Lead Gen",       "retailer"):     [
        "Get Purity Beans on your shelf — WhatsApp for pricing",
        "Retail partnership enquiry → WhatsApp us",
    ],
    ("Website Traffic",         "consumer"):     [
        "Read the full story at p3online.in",
        "More at p3online.in/blog",
    ],
    ("Brand Awareness",         "consumer"):     [
        "Follow for daily coffee truth",
        "Share with a coffee lover",
        "Tag someone who drinks fake coffee",
    ],
    ("Engagement Growth",       "consumer"):     [
        "Share this — someone you know is drinking chicory right now",
        "Tag a coffee lover who needs to see this",
        "Save this for the next time someone argues about coffee",
    ],
}

_FALLBACK_CTA = "Follow Purity Beans for daily coffee truth"


def get_best_cta(
    objective: str,
    audience: str  = "consumer",
    day: int       = 0,
) -> str:
    """
    Return the best CTA for given objective + audience.

    Uses measured conversion rate when available (>= 5 clicks).
    Falls back to priority-ordered defaults otherwise.
    """
    # Try data-driven selection first
    data_cta = _get_data_driven_cta(objective, audience)
    if data_cta:
        return data_cta

    # Fallback to defaults with day-based rotation
    key     = (objective, audience)
    options = _DEFAULT_CTAS.get(key) or _DEFAULT_CTAS.get((objective, "consumer"), [_FALLBACK_CTA])
    return options[day % len(options)]


def _get_data_driven_cta(objective: str, audience: str) -> str:
    """Return the highest-converting measured CTA, or empty string if none."""
    try:
        from content_generator.analytics.metrics_store import get_cta_performance
        rows = get_cta_performance(min_clicks=5)
        # Filter by objective + audience
        relevant = [
            r for r in rows
            if r.get("objective") == objective and r.get("audience") == audience
        ]
        if relevant:
            # Already sorted by conv_rate DESC in get_cta_performance
            return relevant[0]["cta_text"]
    except Exception as _e:
        logger.debug("[cta_optimizer] optional step failed: %s", _e)
    return ""


def get_all_ctas_for_objective(objective: str, audience: str = "consumer") -> list[str]:
    """Return all CTA options for an objective — useful for A/B testing."""
    key = (objective, audience)
    return list(_DEFAULT_CTAS.get(key, [_FALLBACK_CTA]))
