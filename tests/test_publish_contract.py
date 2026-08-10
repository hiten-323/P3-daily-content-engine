"""
Publish result contract.

A green CI run must mean the expected platforms actually published. Every check
here guards a way a run could report success while publishing nothing.
Run: python tests/test_publish_contract.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LEARNING_DIR"] = tempfile.mkdtemp(prefix="pb_test_learning_")

failures = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main():
    from content_generator.core.publish_contract import (
        build, evaluate, format_report, expected_platforms, SLOT_EXPECTATIONS,
    )

    # 1. A missing contract must FAIL. It previously warned and exited 0, which
    #    contradicted the check's own purpose.
    print("\nA missing contract is a failure, not a warning:")
    for bad in ({}, {"success": True}, {"slot": "morning", "success": True}):
        v = evaluate(bad)
        check(f"no contract -> failure: {bad}", v["status"] == "missing" and not v["ok"])

    # 2. Partial publishing must FAIL. "Something published" is not "what was
    #    supposed to publish did".
    print("\nPartial publishing fails:")
    partial = build("morning", 1,
                    expected={"instagram": ["carousel"], "facebook": ["carousel"]},
                    results={"instagram": {"status": "published", "remote_id": "ig1"},
                             "facebook":  {"status": "failed", "error": "token expired"}})
    v = evaluate(partial)
    check("instagram ok + facebook failed -> not ok", not v["ok"], v["status"])
    check("the failing platform is named",
          any("facebook" in m for m in v["missing"]), str(v["missing"]))
    check("the reason is carried through", "token expired" in v["detail"], v["detail"])
    check("published_platforms still lists only real successes",
          partial["published_platforms"] == ["instagram"],
          str(partial["published_platforms"]))

    # 3. Everything expected publishing -> pass.
    print("\nFull publishing passes:")
    full = build("morning", 1,
                 expected={"instagram": ["carousel"], "facebook": ["carousel"]},
                 results={"instagram": {"status": "published", "remote_id": "ig1"},
                          "facebook":  {"status": "published", "remote_id": "fb1"}})
    check("all expected published -> ok", evaluate(full)["ok"])

    # 4. Held and skipped are distinct from broken, and stay green.
    print("\nDeliberate non-publishing is distinguished from breakage:")
    held = build("evening", 1, expected={}, results={},
                 status="held", reason="canonical_validation_failed")
    v = evaluate(held)
    check("held is ok", v["ok"] and v["status"] == "held")
    check("held carries its reason", "canonical" in v["detail"], v["detail"])
    check("held is NOT reported as published",
          held["published_platforms"] == [], str(held["published_platforms"]))

    # 5. Correlation ids so a publish can be traced back to its generation.
    print("\nRuns are traceable:")
    c = build("morning", 7, {"instagram": ["carousel"]},
              {"instagram": {"status": "published", "remote_id": "x"}},
              generation_id="gen_2026-08-09_abc123")
    for f in ("run_id", "generation_id", "slot", "day", "contract_version"):
        check(f"contract carries {f}", bool(c.get(f) is not None and c.get(f) != ""))
    check("generation_id preserved", c["generation_id"] == "gen_2026-08-09_abc123")

    # 6. Each slot declares what it is responsible for.
    print("\nSlot expectations are declared:")
    check("morning expects instagram + facebook",
          set(expected_platforms("morning")) == {"instagram", "facebook"})
    check("evening expects instagram + facebook",
          set(expected_platforms("evening")) == {"instagram", "facebook"})
    check("generate does not expect instagram",
          "instagram" not in expected_platforms("generate"))

    # 7. The report names every platform, including ones not expected — so a
    #    reader can tell "not due this slot" from "failed".
    print("\nReport distinguishes not-expected from failed:")
    rep = format_report(partial)
    check("report marks the failure", "FAIL" in rep, rep)
    check("report marks the success", "OK" in rep, rep)
    rep2 = format_report(build("generate", 1, {"linkedin": ["post"]},
                               {"linkedin": {"status": "published"},
                                "instagram": {"status": "skipped"}}))
    check("unexpected platform marked not-expected",
          "not expected this slot" in rep2, rep2)

    # 8. The real slot functions must return a contract, not a bare dict. This
    #    is the defect itself: run_publish_slot returned the publisher's dict.
    print("\nThe scheduler emits the contract:")
    from content_generator.scheduler import slots as sl
    import inspect
    src = inspect.getsource(sl)
    check("no bare '{\"slot\": slot, **result}' returns remain",
          '{"slot": slot, **result}' not in src)
    check("_held exists for deliberate holds", hasattr(sl, "_held"))
    check("_contract exists for publishes", hasattr(sl, "_contract"))
    check("facebook mirror returns its result",
          "-> dict" in inspect.getsource(sl._mirror_to_facebook))

    print(f"\n{'PUBLISH CONTRACT BROKEN' if failures else 'publish contract enforced'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
