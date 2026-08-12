"""
Continuous Learning Engine — closes the loop between published content
and future generation.

Historical performance is always scored under the KPI stamped when the asset
was created. A later founder-policy change may discount old evidence, but must
never silently rewrite the yardstick under which an experiment originally ran.
"""
import datetime
import json
import logging
import os

logger = logging.getLogger(__name__)
_LEARNING_DIR = os.getenv("LEARNING_DIR", os.path.join("output", "learning"))
_LOG_PATH = os.path.join(_LEARNING_DIR, "performance_log.json")

METRIC_FIELDS = [
    "views", "reach", "impressions", "watch_time_s", "avg_view_duration_s",
    "completion_rate", "shares", "saves", "comments", "profile_visits",
    "follows_gained", "website_clicks", "likes", "revenue", "orders",
]


def _load_log() -> list[dict]:
    if not os.path.exists(_LOG_PATH):
        return []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("[learning] Could not read log: %s", e)
        return []


def _save_log(entries: list[dict]) -> None:
    os.makedirs(_LEARNING_DIR, exist_ok=True)
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def record_performance(
    asset_id: str, track: str, hook: str = "", topic: str = "",
    format_used: str = "", posted_at: str = "", metrics: dict = None,
    notes: str = "", audio_category: str = "", kpi_at_creation: str = "",
    policy_version: str = "", attention_mechanism: str = "",
    scroller_state: str = "", psychology_frame: str = "",
    hook_strategy: str = "", payoff_type: str = "", decision_version: str = "",
) -> dict:
    """Record performance and preserve the objective used at creation time."""
    entries = _load_log()
    entry = {
        "asset_id": asset_id, "track": track, "kpi": kpi_at_creation,
        "policy_version": policy_version, "hook": hook, "topic": topic,
        "format": format_used, "attention_mechanism": attention_mechanism or None,
        "scroller_state": scroller_state or None, "psychology_frame": psychology_frame or None,
        "hook_strategy": hook_strategy or None, "payoff_type": payoff_type or None,
        "decision_version": decision_version or None, "audio_category": audio_category,
        "posted_at": posted_at or datetime.date.today().isoformat(),
        "recorded_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "metrics": {k: v for k, v in (metrics or {}).items() if k in METRIC_FIELDS},
        "notes": notes,
    }
    entries.append(entry)
    _save_log(entries)
    logger.info("[learning] Recorded performance for %s (%s)", asset_id, track)
    return entry


_HALF_LIFE_DAYS = 30.0
_CROSS_OBJECTIVE_DISCOUNT = 0.4


def _entry_kpi(entry: dict) -> str | None:
    """Return the KPI recorded when the asset was created; None means legacy."""
    stamped = str(entry.get("kpi") or "").strip().lower()
    return stamped or None


def _engagement_score(m: dict, kpi: str | None = None) -> float:
    """Score metrics under the creation-time KPI (or active KPI for legacy)."""
    from content_generator.core.reward import score as _reward
    return _reward(m, kpi)


def _recency_factor(entry: dict) -> float:
    ts = str(entry.get("posted_at") or entry.get("recorded_at") or "")[:10]
    if not ts:
        return 1.0
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat(ts)).days
    except Exception:
        return 1.0
    return float(0.5 ** (max(age, 0) / _HALF_LIFE_DAYS))


def _objective_factor(entry: dict) -> float:
    """Discount different-objective evidence without re-scoring its metrics."""
    stamped = _entry_kpi(entry)
    if not stamped:
        return 1.0
    try:
        from content_generator.core.reward import get_active_kpi
        return 1.0 if stamped == get_active_kpi() else _CROSS_OBJECTIVE_DISCOUNT
    except Exception as e:
        logger.debug("[learning] objective compare unavailable: %s", e)
        return 1.0


def is_teachable(entry: dict) -> bool:
    """Exclude entries whose hook contains claims rejected by the verifier."""
    hook = str(entry.get("hook") or "")
    if not hook:
        return True
    try:
        from content_generator.core.claim_verifier import verify_claims
        findings = verify_claims(hook)
    except Exception as e:
        logger.debug("[learning] claim check unavailable: %s", e)
        return True
    if findings:
        logger.debug("[learning] %s excluded from learning — hook carries %s",
                     entry.get("asset_id"), [f["type"] for f in findings])
        return False
    return True


def _weighted_score(entry: dict) -> float:
    # Score using creation KPI first, then apply today's compatibility discount.
    return (
        _engagement_score(entry.get("metrics", {}), _entry_kpi(entry))
        * _recency_factor(entry)
        * _objective_factor(entry)
    )


def analyze() -> dict:
    entries = _load_log()
    scored = [(e, _weighted_score(e)) for e in entries if e.get("metrics")]
    if not scored:
        return {"winners": [], "failed": [], "median_score": 0.0, "count": 0}
    scores = sorted(s for _, s in scored)
    median = scores[len(scores) // 2]
    winners = [e for e, s in scored if s >= median and s > 0 and is_teachable(e)]
    failed = [e for e, s in scored
              if s <= median * 0.5 and _objective_factor(e) == 1.0]
    return {"winners": winners, "failed": failed, "median_score": median, "count": len(scored)}


def _infer_reason(entry: dict) -> str:
    m = entry.get("metrics", {})
    if m.get("revenue", 0) > 0:
        return f"generated Rs {m['revenue']:.0f} in attributed sales — conversion structure"
    views = m.get("views", 0) or m.get("reach", 0)
    if not views:
        return ""
    save_rate = m.get("saves", 0) / views
    share_rate = m.get("shares", 0) / views
    comment_rate = m.get("comments", 0) / views
    best = max(save_rate, share_rate, comment_rate)
    if best == 0:
        return "reached people but nothing made them act"
    if best == save_rate:
        return "high save rate — reference/utility value"
    if best == share_rate:
        return "high share rate — identity/social value"
    return "high comment rate — opinion/conversation trigger"


def get_learning_block(max_items: int = 5) -> str:
    """Return recency- and objective-aware patterns for future generation."""
    entries = _load_log()
    scored = sorted(
        ((e, _weighted_score(e)) for e in entries if e.get("metrics")),
        key=lambda x: x[1], reverse=True,
    )
    seen, unique = set(), []
    for entry, score in scored:
        key = (str(entry.get("hook", "")).strip().lower(),
               str(entry.get("topic", "")).strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append((entry, score))
    scored = [(e, s) for e, s in unique if is_teachable(e)]
    if len(scored) < 3:
        return ""

    n_top = max(1, len(scored) // 5)
    top = scored[:n_top]
    same_obj = [(e, s) for e, s in scored if _objective_factor(e) == 1.0]
    bottom = same_obj[-n_top:] if same_obj else []

    lines = [
        "VIRAL MEMORY (this account's actual results — compounds over months):",
        "Use ONLY hook/topic structures similar to the TOP 20%. AVOID the bottom 20%.",
        "TOP 20% — reuse these structures:",
    ]
    for e, _ in top[:max_items]:
        desc = " | ".join(filter(None, [e.get("hook"), e.get("topic"), e.get("format")]))
        reason = _infer_reason(e)
        if desc:
            lines.append(f"  + {desc}" + (f"  [why: {reason}]" if reason else ""))
    lines.append("BOTTOM 20% — never repeat these structures:")
    for e, _ in bottom[:max_items]:
        desc = " | ".join(filter(None, [e.get("hook"), e.get("topic"), e.get("format")]))
        if desc:
            lines.append(f"  - {desc}")
    return "\n".join(lines)
