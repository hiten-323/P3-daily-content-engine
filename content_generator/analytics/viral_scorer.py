"""
Viral score — 0-100, normalized against THIS account, not a global benchmark.

Why this was rewritten:
  The original ceilings were Indian-FMCG benchmarks — 100,000 views, 1,000
  shares, 2,000 saves. On an account with ~105 followers every post scores
  ~0.3/100, so the number carries no ranking information at all: a genuinely
  strong post and a dud are indistinguishable. A score is only useful if it
  discriminates within the range the account actually operates in.

  So the ceilings now come from the account's own recent history (p90 of the
  last N measured posts). A post in your own top decile scores near 100 —
  whatever your absolute numbers are — and the scale re-tunes itself as the
  account grows.

Two rules this module holds to:
  1. WEIGHTS ARE NOT DEFINED HERE. They come from core/reward.py, the single
     definition of success. Two competing weight tables is how an engine ends
     up optimizing two different things.
  2. NO BASELINE MEANS NO SCORE. With too little history the honest answer is
     None, not a fabricated number. Callers must handle it.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# Below this many measured posts, the p90 of the sample is noise, not a ceiling.
MIN_POSTS_FOR_BASELINE = 5
# How much history the baseline is drawn from.
BASELINE_WINDOW = 30

# Metrics the score is computed over, in the order they're reported.
_SIGNALS = ("follows_gained", "shares", "saves", "profile_visits",
            "comments", "views", "retention")

# Floors so a single freak post can't set an unreachable ceiling and flatten
# every subsequent score to near-zero.
_CEILING_FLOOR = {
    "follows_gained": 1.0, "shares": 1.0, "saves": 1.0, "profile_visits": 1.0,
    "comments": 1.0, "views": 10.0, "retention": 10.0,
}


def _p90(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return float(s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))])


def get_account_baseline(window: int = BASELINE_WINDOW) -> dict | None:
    """
    Per-signal ceilings from the account's own measured posts.
    Returns None when there isn't enough history to normalize against.
    """
    try:
        from content_generator.core.learning_engine import _load_log
        rows = [e for e in _load_log()
                if ((e.get("metrics") or {}).get("reach", 0)
                    or (e.get("metrics") or {}).get("views", 0))]
    except Exception as e:
        logger.debug("[viral] learning log unavailable: %s", e)
        return None

    if len(rows) < MIN_POSTS_FOR_BASELINE:
        return None

    rows = rows[-window:]
    ceilings = {}
    for sig in _SIGNALS:
        vals = [float((r.get("metrics") or {}).get(sig, 0) or 0) for r in rows]
        ceilings[sig] = max(_p90(vals), _CEILING_FLOOR[sig])
    return ceilings


def compute_viral_score(views: int = 0, retention: float = 0.0, shares: int = 0,
                        saves: int = 0, comments: int = 0,
                        follows_gained: int = 0, profile_visits: int = 0
                        ) -> float | None:
    """
    0-100 relative to this account's own recent performance, weighted by the
    active KPI profile in core/reward.py.

    Returns None when the account has fewer than MIN_POSTS_FOR_BASELINE measured
    posts — there is nothing to normalize against and any number would be made up.
    """
    baseline = get_account_baseline()
    if baseline is None:
        return None

    from content_generator.core.reward import get_weights
    weights = get_weights()

    raw = {"views": views, "retention": retention, "shares": shares,
           "saves": saves, "comments": comments,
           "follows_gained": follows_gained, "profile_visits": profile_visits}

    # Weight each signal by its share of the active reward profile, so this
    # score and the reward function always agree on what "good" means.
    active = {s: float(weights.get(s, 0.0)) for s in _SIGNALS if weights.get(s, 0.0) > 0}
    # `retention` is not a reward signal but is the strongest watch-time proxy;
    # give it the same standing as shares so watch time is represented.
    active.setdefault("retention", float(weights.get("shares", 1.0)))
    total_w = sum(active.values()) or 1.0

    total = 0.0
    for sig, w in active.items():
        ceiling = baseline.get(sig) or _CEILING_FLOOR[sig]
        total += min(max(float(raw.get(sig, 0) or 0), 0.0) / ceiling, 1.0) * (w / total_w)
    return round(total * 100, 1)


def explain_score(metrics: dict) -> dict:
    """Score plus the baseline it was measured against — so it is auditable."""
    baseline = get_account_baseline()
    if baseline is None:
        try:
            from content_generator.core.learning_engine import _load_log
            have = len(_load_log())
        except Exception:
            have = 0
        return {"viral_score": None, "basis": "insufficient_history",
                "measured_posts": have, "needed": MIN_POSTS_FOR_BASELINE,
                "note": "no account baseline yet — a score here would be invented"}
    m = metrics or {}
    return {
        "viral_score": compute_viral_score(
            views=m.get("views", 0), retention=m.get("retention", 0.0),
            shares=m.get("shares", 0), saves=m.get("saves", 0),
            comments=m.get("comments", 0),
            follows_gained=m.get("follows_gained", 0),
            profile_visits=m.get("profile_visits", 0)),
        "basis": "account_relative_p90",
        "baseline": {k: round(v, 1) for k, v in baseline.items()},
    }


def score_batch(metrics_list: list[dict]) -> list[dict]:
    """Add viral_score to each metrics dict and return sorted descending."""
    for m in metrics_list:
        m["viral_score"] = compute_viral_score(
            views=m.get("views", 0), retention=m.get("retention", 0.0),
            shares=m.get("shares", 0), saves=m.get("saves", 0),
            comments=m.get("comments", 0),
            follows_gained=m.get("follows_gained", 0),
            profile_visits=m.get("profile_visits", 0),
        )
    # None sorts last — unscored posts must not outrank measured ones.
    return sorted(metrics_list,
                  key=lambda x: (x["viral_score"] is not None, x["viral_score"] or 0),
                  reverse=True)
