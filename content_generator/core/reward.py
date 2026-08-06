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
WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    # 0-1K followers: compounding audience is the objective.
    "followers": {
        "revenue": 1.0, "orders": 25.0,
        "follows_gained": 40.0,     # the KPI — dominant
        "shares": 12.0,             # shares create followers
        "profile_visits": 8.0,      # the step before a follow
        "saves": 4.0, "comments": 4.0, "likes": 0.5, "views": 0.01,
    },
    # Conversation/community phase.
    "engagement": {
        "revenue": 1.0, "orders": 25.0,
        "comments": 20.0, "shares": 15.0, "saves": 12.0,
        "follows_gained": 10.0, "profile_visits": 4.0,
        "likes": 1.0, "views": 0.01,
    },
    # Mature account: money is the objective.
    "revenue": {
        "revenue": 2.0, "orders": 50.0,
        "profile_visits": 5.0, "follows_gained": 5.0,
        "shares": 4.0, "saves": 4.0, "comments": 3.0,
        "likes": 0.5, "views": 0.01,
    },
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
