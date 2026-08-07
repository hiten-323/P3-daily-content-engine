"""
THE reward function — the single definition of "success" for this engine.

Everything that learns (hook selection, hashtags, lead magnets, audio, viral
memory) ranks by this one score. If these weights are wrong, the engine
optimizes the wrong thing — so they live here, alone, documented and testable.

Two properties that were previously missing and caused real risk:

1. STAGE / KPI AWARENESS. The founder policy sets target_kpi. At IGNITION
   (target_kpi: followers) a revenue-dominant reward would teach the engine to
   chase the few rupees a post earns instead of the followers that compound.
   Weights now switch with the KPI.

2. GOAL-HIERARCHY SAFETY (GOAL_HIERARCHY.md). Lower goals must never override
   higher ones. Revenue and orders keep a floor weight in EVERY profile, so a
   follower-optimizing engine can never learn to prefer a post that earns
   nothing over one that sells — it only changes how much *extra* credit the
   softer signals get.

Weights are "points per unit". Revenue is per rupee.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# Per-KPI weight profiles. Revenue/orders keep meaningful weight everywhere
# (goal-hierarchy floor); what changes is the emphasis on the softer signals.
# Signal ordering follows the founder's Growth Director spec:
#   PRIMARY   follows, shares, saves, watch time, profile visits, website CTR,
#             returning viewers, repeat engagement, revenue
#   SECONDARY comments, reach, impressions
# `likes` is deliberately near-zero everywhere — "success is NOT measured by likes".
WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    # 0-1K followers: compounding audience is the objective.
    "followers": {
        "revenue": 1.0, "orders": 25.0,
        "follows_gained": 40.0,     # the KPI — dominant
        "shares": 12.0,             # shares create followers
        "profile_visits": 8.0,      # the step before a follow
        "website_clicks": 6.0,      # intent — the step before a sale
        "saves": 4.0, "comments": 4.0,
        "avg_view_duration_s": 0.8,  # watch time: seconds held per viewer
        "reach": 0.02, "likes": 0.5, "views": 0.01,
    },
    # Conversation/community phase.
    "engagement": {
        "revenue": 1.0, "orders": 25.0,
        "comments": 20.0, "shares": 15.0, "saves": 12.0,
        "follows_gained": 10.0, "profile_visits": 4.0,
        "website_clicks": 4.0,
        "avg_view_duration_s": 1.0,
        "reach": 0.02, "likes": 1.0, "views": 0.01,
    },
    # Mature account: money is the objective.
    "revenue": {
        "revenue": 2.0, "orders": 50.0,
        "website_clicks": 8.0,
        "profile_visits": 5.0, "follows_gained": 5.0,
        "shares": 4.0, "saves": 4.0, "comments": 3.0,
        "avg_view_duration_s": 0.5,
        "reach": 0.01, "likes": 0.5, "views": 0.01,
    },
}

# Spec KPIs the Instagram Graph API does not expose per post, and the honest
# reason why. Documented here so nobody "adds" them later with invented numbers:
#
#   returning_viewers / repeat_engagement — Instagram exposes no per-viewer
#     identity on media insights. There is no supported way to tell a repeat
#     viewer from a new one. The closest real proxies are account-level
#     `accounts_engaged` over time, and repeat commenters (derivable from the
#     comments API). Neither is per-post.
#
#   website_ctr — link clicks are reported at ACCOUNT level (`website_clicks`),
#     not per post. `website_clicks` above is therefore attributed across the
#     day's posts, exactly as follows_gained already is. Per-post CTR requires
#     per-post UTM links, which Instagram's single bio link cannot provide
#     without a link-in-bio router.
UNAVAILABLE_KPIS = {
    "returning_viewers": "no per-viewer identity in the Graph API",
    "repeat_engagement": "no per-viewer identity in the Graph API",
    "website_ctr_per_post": "link clicks are account-level, not per-media",
}
DEFAULT_KPI = "followers"


def get_active_kpi() -> str:
    """The founder-set KPI (founder_policies.yaml -> business.target_kpi)."""
    try:
        from content_generator.core.founder_policy import policy
        kpi = str(policy().get("target_kpi") or DEFAULT_KPI).lower()
        return kpi if kpi in WEIGHT_PROFILES else DEFAULT_KPI
    except Exception as e:
        logger.debug("[reward] policy KPI unavailable (%s) — default", e)
        return DEFAULT_KPI


def get_weights(kpi: str | None = None) -> dict[str, float]:
    return WEIGHT_PROFILES.get(kpi or get_active_kpi(), WEIGHT_PROFILES[DEFAULT_KPI])


def score(metrics: dict, kpi: str | None = None) -> float:
    """Reward for one post's metrics under the active KPI profile."""
    w = get_weights(kpi)
    m = metrics or {}
    return float(sum(float(m.get(k, 0) or 0) * weight for k, weight in w.items()))


def explain(metrics: dict, kpi: str | None = None) -> dict:
    """Score plus the per-signal contribution — so ranking is auditable."""
    kpi = kpi or get_active_kpi()
    w = get_weights(kpi)
    m = metrics or {}
    parts = {k: round(float(m.get(k, 0) or 0) * weight, 2)
             for k, weight in w.items() if m.get(k)}
    total = round(sum(parts.values()), 2)
    top = sorted(parts.items(), key=lambda x: x[1], reverse=True)[:3]
    return {"kpi": kpi, "score": total, "contributions": parts,
            "top_drivers": [k for k, _ in top]}
