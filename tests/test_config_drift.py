"""
Config/doc drift guard — cheap checks that the running system matches what the
constitution documents and what other layers assume.

Run: python -m tests.test_config_drift   (also importable by any test runner)

These catch the class of bug that already bit us once: a threshold defined in
two places, or docs promising behavior the code no longer has.
"""
from __future__ import annotations
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} — {detail}")
        failures.append(name)


def main() -> int:
    print("Config / documentation drift checks")

    # 1. Editorial threshold has exactly ONE runtime source
    from content_generator.core.editorial_engine import get_current_pass_score
    from content_generator.core.founder_policy import policy
    live, pol = get_current_pass_score(), policy().get("minimum_score")
    check("editorial threshold == founder policy", float(live) == float(pol),
          f"live={live} policy={pol}")

    # 2. No module hardcodes its own threshold
    hits = []
    for root, _dirs, files in os.walk("content_generator"):
        for f in files:
            if not f.endswith(".py") or "editorial_engine" in f:
                continue
            path = os.path.join(root, f)
            body = open(path, encoding="utf-8", errors="ignore").read()
            if re.search(r"PASS_SCORE\s*=\s*\d", body):
                hits.append(path)
    check("no module hardcodes PASS_SCORE", not hits, str(hits))

    # 3. Every rotating brand tagline satisfies the brand-facts validator
    from content_generator.scheduler.daily import _BRAND_TAGLINES
    from content_generator.core.brand_validator import validate_brand_facts
    bad = [t for t in _BRAND_TAGLINES if not validate_brand_facts(t)]
    check("all brand taglines carry a required brand fact", not bad, str(bad))

    # 4. Versions are present and well-formed
    from content_generator.core.versions import all_versions
    vers = all_versions()
    check("version registry complete",
          all(re.match(r"^\d+\.\d+\.\d+$", v) for v in vers.values()) and len(vers) == 4,
          str(vers))

    # 5. Telemetry uses the shared publisher version (not its own copy)
    from content_generator.analytics.telemetry import PUBLISHER_VERSION
    from content_generator.core.versions import PUBLISHER_VERSION as CANON
    check("telemetry publisher_version is shared", PUBLISHER_VERSION == CANON,
          f"{PUBLISHER_VERSION} != {CANON}")

    # 6. Documented policy file keys exist in the loader defaults
    p = policy()
    for dom in ("business", "content", "brand", "marketing", "quality",
                "publishing", "experiments"):
        check(f"policy domain '{dom}' present", isinstance(p.domain(dom), dict) and bool(p.domain(dom)))

    # 7. Docs reference files that exist
    for doc in ("MISSION.md", "OPERATING_PRINCIPLES.md", "SUCCESS_METRICS.md",
                "GOAL_HIERARCHY.md", "POLICY_ENGINE.md", "ARCHITECTURE.md",
                "ASSUMPTIONS.md", "UNKNOWNS.md", "docs/ADR-001.md"):
        check(f"doc exists: {doc}", os.path.exists(doc))

    print(f"\n{'DRIFT DETECTED' if failures else 'no drift'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
