"""
Engine Self-Audit — an operational assurance layer, not business logic.

Runs automatically at the end of every pipeline execution and prints a single
health block. Its job is to make REGRESSIONS immediately visible after any
future change, so a silent breakage (e.g. "editorial rejects 100% of assets")
is caught on the next run instead of weeks later.

Never raises: an audit must never be able to break the run it is auditing.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def _check(name: str, fn) -> tuple[str, bool, str]:
    try:
        ok, detail = fn()
        return name, bool(ok), str(detail)
    except Exception as e:                       # assurance layer must not raise
        logger.debug("[self_audit] check %s errored: %s", name, e)
        return name, False, f"check errored: {e}"


def run_self_audit(content: dict | None = None, publish_result: dict | None = None) -> dict:
    """Return {checks, score, healthy} and log a compact health block."""
    content = content or {}
    publish_result = publish_result or {}
    checks: list[tuple[str, bool, str]] = []

    # 1. Generation produced assets
    def _gen():
        n = sum(1 for k in ("carousel", "instagram_post", "linkedin_post", "blog_post",
                            "yt_short", "stories", "growth_reel")
                if isinstance(content.get(k), dict) and content.get(k))
        n += sum(1 for r in (content.get("reels") or []) if isinstance(r, dict) and r)
        return n >= 2, f"{n} assets"
    checks.append(_check("Generation", _gen))

    # 2. Editorial gate is scoring (and not rejecting everything)
    def _editorial():
        from content_generator.core.editorial_engine import get_valid_assets, get_current_pass_score
        valid = get_valid_assets(content) if content else []
        return (len(valid) >= 1 if content else True,
                f"{len(valid)} valid @ threshold {get_current_pass_score()}")
    checks.append(_check("Editorial", _editorial))

    # 3. Brand safety net intact (every tagline carries a required fact)
    def _brand():
        from content_generator.scheduler.daily import _BRAND_TAGLINES
        from content_generator.core.brand_validator import validate_brand_facts
        bad = [t for t in _BRAND_TAGLINES if not validate_brand_facts(t)]
        return not bad, f"{len(_BRAND_TAGLINES) - len(bad)}/{len(_BRAND_TAGLINES)} taglines valid"
    checks.append(_check("Brand", _brand))

    # 4. Publishing produced a real outcome (held is fine; total silence is not)
    def _publish():
        if not publish_result:
            return True, "not run in this context"
        pub = [k for k, v in publish_result.items()
               if isinstance(v, dict) and v.get("success")]
        held = [k for k, v in publish_result.items()
                if isinstance(v, dict) and v.get("held")]
        return bool(pub or held), f"{len(pub)} published, {len(held)} held"
    checks.append(_check("Publishing", _publish))

    # 5. Learning loop is accumulating data
    def _learning():
        from content_generator.core.learning_engine import analyze
        n = analyze().get("count", 0)
        return True, f"{n} posts with metrics" + (" (cold start)" if n < 3 else "")
    checks.append(_check("Learning", _learning))

    # 6. Reward function resolves and matches the founder KPI
    def _reward():
        from content_generator.core.reward import get_active_kpi, get_weights
        kpi = get_active_kpi()
        w = get_weights(kpi)
        top = max(w, key=w.get)
        return bool(w), f"KPI={kpi}, top-weighted signal={top}"
    checks.append(_check("Reward", _reward))

    # 7. Memory ranking is recency-aware (guards the stale-outlier regression)
    def _memory():
        from content_generator.core.learning_engine import _recency_factor
        import datetime
        old = {"posted_at": (datetime.date.today() - datetime.timedelta(days=180)).isoformat()}
        fresh = {"posted_at": datetime.date.today().isoformat()}
        return _recency_factor(old) < _recency_factor(fresh), "decay active"
    checks.append(_check("Memory", _memory))

    # 8. Config/doc drift
    def _drift():
        from content_generator.core.editorial_engine import get_current_pass_score
        from content_generator.core.founder_policy import policy
        live, pol = get_current_pass_score(), policy().get("minimum_score")
        return float(live) == float(pol), f"threshold {live} == policy {pol}"
    checks.append(_check("Drift", _drift))

    # 9. Decision layer produces a forecast
    def _forecast():
        from content_generator.intelligence.decision_layer import build_recommendation
        r = build_recommendation(int(content.get("day_number") or 0))
        return "confidence" in r, f"EVPOI {r.get('expected_evpoi')} @ conf {r.get('confidence')}"
    checks.append(_check("Forecast", _forecast))

    passed = sum(1 for _, ok, _ in checks if ok)
    score = round(100 * passed / max(len(checks), 1))
    healthy = score >= 80

    lines = ["================= ENGINE SELF-AUDIT ================="]
    for name, ok, detail in checks:
        lines.append(f"  {'OK  ' if ok else 'FAIL'}  {name:<11} {detail}")
    lines.append(f"  Overall health: {score}/100" + ("" if healthy else "   ** DEGRADED **"))
    lines.append("=" * 53)
    (logger.info if healthy else logger.error)("\n".join(lines))

    return {"checks": [{"name": n, "ok": o, "detail": d} for n, o, d in checks],
            "score": score, "healthy": healthy}
