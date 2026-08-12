"""
THE reward function — the single definition of "success" for this engine.

Everything that learns (hook selection, hashtags, lead magnets, audio, viral
memory) ranks by this one score. If these weights are wrong, the engine
optimizes the wrong thing — so they live here, alone, documented and testable.

STAGE / KPI AWARENESS: the founder policy sets target_kpi and weights switch
with that KPI. At IGNITION (followers), audience growth is intentionally the
primary optimization target; at the revenue stage, conversion signals become
primary.

IMPORTANT HIERARCHY CONTRACT: this function is a weighted reward, not a
lexicographic business-objective hierarchy. Revenue/orders retain a non-zero
floor in every profile, but that floor does NOT guarantee that any revenue
outcome beats every audience outcome. The current KPI profile is the authority
for what the engine should optimize within a stage. Cross-stage governance
belongs in founder policy / Growth Director, not in an accidental property of
raw metric magnitudes.

Weights are "points per unit". Revenue is per rupee.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    # 0-1K followers: compounding audience is the objective.
    "followers": {
        "revenue": 1.0, "orders": 25.0,
        "follows_gained": 40.0,
        "shares": 12.0,
        "profile_visits": 8.0,
        "website_clicks": 6.0,
        "saves": 4.0, "comments": 4.0,
        "avg_view_duration_s": 0.8,
        "reach": 0.02, "likes": 0.5, "views": 0.01,
    },
    "engagement": {
        "revenue": 1.0, "orders": 25.0,
        "comments": 20.0, "shares": 15.0, "saves": 12.0,
        "follows_gained": 10.0, "profile_visits": 4.0,
        "website_clicks": 4.0,
        "avg_view_duration_s": 1.0,
        "reach": 0.02, "likes": 1.0, "views": 0.01,
    },
    "revenue": {
        "revenue": 2.0, "orders": 50.0,
        "website_clicks": 8.0,
        "profile_visits": 5.0, "follows_gained": 5.0,
        "shares": 4.0, "saves": 4.0, "comments": 3.0,
        "avg_view_duration_s": 0.5,
        "reach": 0.01, "likes": 0.5, "views": 0.01,
    },
}

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
    """
    Weighted reward under the explicitly supplied KPI profile.

    The caller can pass the KPI stamped at asset creation time. This is
    essential for historical learning: changing founder policy must not
    silently re-judge yesterday's experiment with today's objective.
    """
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
    total = score(metrics, kpi)
    top = sorted(parts.items(), key=lambda x: x[1], reverse=True)[:3]
    return {"kpi": kpi, "score": total, "contributions": parts,
            "top_drivers": [k for k, _ in top]}
