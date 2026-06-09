"""
Lead scorer — assigns a 0–100 quality score to every lead.

Scoring model (weighted sum):
  Source virality    20%  — high-viral content attracts higher-quality leads
  Engagement depth   30%  — comment/DM > like > passive view
  Segment value      30%  — distributor >> retailer >> consumer (business value)
  Contact completeness 20% — name + phone + company = higher intent

Score interpretation:
  80–100  Hot lead — act within 24 hours
  60–79   Warm lead — nurture within 3 days
  40–59   Cool lead — weekly nurture sequence
  0–39    Cold lead — automated low-touch nurture only
"""
import logging

logger = logging.getLogger(__name__)

# Segment base scores reflecting business value hierarchy
_SEGMENT_BASE: dict[str, float] = {
    "distributor":  90.0,
    "modern_trade": 85.0,
    "retailer":     65.0,
    "consumer":     40.0,
}

# Engagement type weights (how they reached out)
_ENGAGEMENT_WEIGHTS: dict[str, float] = {
    "direct_dm":        1.0,    # highest intent — they typed a message
    "whatsapp_inquiry": 1.0,
    "phone_call":       0.95,
    "email_inquiry":    0.85,
    "form_submission":  0.75,
    "comment":          0.60,
    "link_click":       0.40,
    "profile_visit":    0.20,
    "like":             0.10,
}

# Priority label thresholds
_PRIORITY_LABELS: list[tuple[float, str]] = [
    (80, "hot"),
    (60, "warm"),
    (40, "cool"),
    (0,  "cold"),
]


def score_lead(
    segment: str,
    engagement_type: str  = "form_submission",
    source_viral_score: float = 50.0,
    has_name: bool        = False,
    has_phone: bool       = False,
    has_company: bool     = False,
    stage: str            = "inquiry",
) -> float:
    """
    Compute a 0–100 lead quality score.

    Args:
        segment:             consumer | retailer | distributor | modern_trade
        engagement_type:     how the lead reached out (see _ENGAGEMENT_WEIGHTS)
        source_viral_score:  viral score of the content that generated this lead
        has_name:            whether name is captured
        has_phone:           whether phone number is captured
        has_company:         whether company name is captured (B2B signals)
        stage:               current pipeline stage (later stages score higher)
    """
    # Component 1: Source content virality (0–100 input, normalised 0–1)
    virality_score = min(source_viral_score / 100, 1.0) * 100 * 0.20

    # Component 2: Engagement depth
    engagement_w   = _ENGAGEMENT_WEIGHTS.get(engagement_type, 0.50)
    engagement_score = engagement_w * 100 * 0.30

    # Component 3: Segment business value (base score already 0–100)
    segment_score  = _SEGMENT_BASE.get(segment, 40.0) * 0.30

    # Component 4: Contact completeness
    completeness   = sum([has_name, has_phone, has_company]) / 3.0
    contact_score  = completeness * 100 * 0.20

    raw = virality_score + engagement_score + segment_score + contact_score

    # Stage bonus — leads that have progressed get a bump
    from content_generator.leads.pipeline import get_stage_index
    idx   = get_stage_index(segment, stage)
    bonus = min(idx * 3, 15)   # max +15 points for stage progression

    return round(min(raw + bonus, 100), 1)


def get_priority(score: float) -> str:
    """Return human priority label for a lead score."""
    for threshold, label in _PRIORITY_LABELS:
        if score >= threshold:
            return label
    return "cold"


def should_alert(score: float, segment: str) -> bool:
    """Return True if this lead warrants an immediate human alert."""
    return (
        score >= 80
        or segment in ("distributor", "modern_trade") and score >= 60
    )


def enrich_lead_with_score(lead: dict) -> dict:
    """
    Add score, priority, and alert flag to an existing lead dict.
    Used when displaying leads in dashboard.
    """
    score    = lead.get("score", 0.0)
    priority = get_priority(score)
    alert    = should_alert(score, lead.get("segment", "consumer"))
    return {**lead, "priority": priority, "needs_alert": alert}
