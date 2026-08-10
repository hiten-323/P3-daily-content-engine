"""
The publish result contract — what a run must prove before it may report success.

WHY THIS EXISTS

The workflow's check was "did we publish to at least one platform", read from a
`published_platforms` list. Two things were wrong with it:

  1. run_publish_slot() never returned that key. It returns the publisher's own
     dict, so on the morning and evening slots — the runs that actually post to
     Instagram — the key was always absent and the check exited 0 with a
     warning. Those slots have never been verified.

  2. "Something published" is not the same as "what was supposed to publish did".
     Instagram succeeding while Facebook silently failed reads as success.

So a run now declares what it EXPECTED to publish and what actually happened,
per platform, and the workflow compares the two. A missing contract is a hard
failure: a run that cannot say what it did has not demonstrated that it did
anything.

DELIBERATELY DISTINCT STATES

    skipped   an explicit, reasoned decision not to publish  -> green
    held      content existed but failed a gate              -> green, reported
    published everything expected succeeded                  -> green
    partial   some expected platform failed                  -> RED
    missing   no contract at all                             -> RED

"Skipped" and "broken" are different, and the previous check collapsed them.
"""
from __future__ import annotations
import datetime
import logging
import os

logger = logging.getLogger(__name__)

CONTRACT_VERSION = "1.0.0"

# What each slot is responsible for. Instagram and Facebook are held during
# generate and published in their own windows (see scheduler/slots.py).
SLOT_EXPECTATIONS: dict[str, list[str]] = {
    "generate": ["linkedin"],
    "morning":  ["instagram", "facebook"],
    "evening":  ["instagram", "facebook"],
}


def expected_platforms(slot: str) -> list[str]:
    return list(SLOT_EXPECTATIONS.get(slot, []))


def build(slot: str, day: int, expected: dict, results: dict,
          generation_id: str = "", status: str = "", reason: str = "") -> dict:
    """
    Assemble the contract a run reports back.

    expected: {"instagram": ["carousel"], "facebook": ["carousel"]}
    results:  {"instagram": {"status": "published", "asset_id": ..., "remote_id": ...}}
    """
    contract = {
        "contract_version": CONTRACT_VERSION,
        "run_id":        os.getenv("GITHUB_RUN_ID", "") or datetime.datetime.now()
                         .strftime("local_%Y%m%d_%H%M%S"),
        "generation_id": generation_id,
        "slot":          slot,
        "day":           day,
        "expected":      expected or {},
        "results":       results or {},
        "reason":        reason,
    }
    contract["status"] = status or evaluate(contract)["status"]
    # Retained so older readers of the result keep working; the contract above
    # is what the workflow actually checks.
    contract["published_platforms"] = [
        p for p, r in (results or {}).items()
        if str((r or {}).get("status")) == "published"
    ]
    return contract


def evaluate(contract: dict) -> dict:
    """
    Compare expected against actual.
    Returns {"status": ..., "ok": bool, "missing": [...], "detail": str}
    """
    if not isinstance(contract, dict) or "expected" not in contract:
        return {"status": "missing", "ok": False, "missing": [],
                "detail": "no publish contract in the run result"}

    if contract.get("status") in ("skipped", "held"):
        return {"status": contract["status"], "ok": True, "missing": [],
                "detail": contract.get("reason") or contract["status"]}

    expected = contract.get("expected") or {}
    results  = contract.get("results") or {}
    missing  = []
    for platform in expected:
        r = results.get(platform) or {}
        if str(r.get("status")) != "published":
            missing.append(f"{platform} ({r.get('status') or 'no result'}"
                           + (f": {r.get('error')}" if r.get("error") else "") + ")")

    if not expected:
        return {"status": "nothing_expected", "ok": True, "missing": [],
                "detail": "this slot publishes nothing"}
    if missing:
        return {"status": "partial", "ok": False, "missing": missing,
                "detail": "expected but not published: " + "; ".join(missing)}
    return {"status": "published", "ok": True, "missing": [],
            "detail": f"all {len(expected)} expected platform(s) published"}


def format_report(contract: dict) -> str:
    """Human-readable per-platform outcome for the CI log."""
    ev = evaluate(contract)
    lines = [f"slot={contract.get('slot')} day={contract.get('day')} "
             f"run_id={contract.get('run_id')} -> {ev['status'].upper()}"]
    expected = contract.get("expected") or {}
    results  = contract.get("results") or {}
    for platform in sorted(set(expected) | set(results)):
        if platform not in expected:
            lines.append(f"  {platform.upper():<10} — not expected this slot")
            continue
        r = results.get(platform) or {}
        mark = "OK  " if str(r.get("status")) == "published" else "FAIL"
        detail = r.get("remote_id") or r.get("error") or r.get("status") or "no result"
        lines.append(f"  {platform.upper():<10} {mark} {detail}")
    return "\n".join(lines)
