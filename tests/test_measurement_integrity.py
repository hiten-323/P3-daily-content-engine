"""
Measurement integrity — the learning loop is only as honest as its inputs.

Every check here exists because the failure it guards silently emptied the
learning log for 50 consecutive posts. Run: python tests/test_measurement_integrity.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

failures = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main():
    from content_generator.analytics import insights_fetcher as ins
    from content_generator.scheduler.slots import _track, _first

    original = ins._graph_get

    # 1. A failed insights call must record NOTHING. Returning zeros here is what
    #    wrote "reached nobody" onto 50 posts that were never actually measured.
    print("\nFailed fetch is never recorded as zero:")
    try:
        ins._graph_get = lambda path, params: (
            {"like_count": 3, "comments_count": 1, "media_product_type": "FEED"}
            if "insights" not in path else None)
        check("insights failure -> None", ins._fetch_media_insights("m1") is None)

        # 2. ...but a genuine zero, reported by the API, must be preserved.
        def _genuine_zero(path, params):
            if "insights" not in path:
                return {"like_count": 0, "comments_count": 0, "media_product_type": "FEED"}
            return {"data": [{"name": "reach", "values": [{"value": 0}]},
                             {"name": "saved", "values": [{"value": 0}]}]}
        ins._graph_get = _genuine_zero
        m = ins._fetch_media_insights("m2")
        check("measured zero -> recorded", m is not None and m.get("reach") == 0, str(m))

        # 3. Real numbers survive intact.
        def _real(path, params):
            if "insights" not in path:
                return {"like_count": 12, "comments_count": 4, "media_product_type": "FEED"}
            return {"data": [{"name": "reach", "values": [{"value": 840}]},
                             {"name": "saved", "values": [{"value": 19}]},
                             {"name": "shares", "values": [{"value": 7}]}]}
        ins._graph_get = _real
        m = ins._fetch_media_insights("m3")
        check("real metrics preserved",
              m and m["reach"] == 840 and m["saves"] == 19 and m["shares"] == 7 and m["likes"] == 12,
              str(m))
    finally:
        ins._graph_get = original

    # 4. The tracked hook must come off the real schema field. `hook_text` and
    #    `title` exist on neither carousels nor reels — reading them is what made
    #    every record's hook an empty string.
    print("\nHook and format are read from the real schema:")
    carousel = {"type": "carousel", "hook": "3 signs your coffee is not pure",
                "objective": "DISCOVERY", "slides": [], "caption": "..."}
    reel = {"type": "reel", "hook": "Read the label before you buy",
            "angle": "contrarian", "caption": "..."}
    check("carousel hook found", _first(carousel, "hook", "hook_text", "headline", "title")
          == "3 signs your coffee is not pure")
    check("reel hook found", _first(reel, "hook", "hook_text", "headline", "title")
          == "Read the label before you buy")
    check("carousel format is 'carousel'", (_first(carousel, "type") or "morning") == "carousel")
    check("reel format is 'reel'", (_first(reel, "type") or "evening") == "reel")
    check("empty piece falls back to slot", (_first({}, "type") or "morning") == "morning")

    captured = {}

    def _fake_track(**kw):
        captured.update(kw)

    sys.modules["content_generator.analytics.insights_fetcher"].track_published_post = _fake_track
    _track({"success": True, "media_id": "abc"}, {"day_number": 7}, "morning", carousel)
    check("_track passes real hook", captured.get("hook") == "3 signs your coffee is not pure",
          str(captured.get("hook")))
    check("_track passes real format", captured.get("format_used") == "carousel",
          str(captured.get("format_used")))

    # 5. The live log must hold only real measurements. A row with no reach and
    #    no hook teaches nothing and drags the median it is measured against.
    print("\nLive performance log holds only real measurements:")
    path = os.path.join("output", "learning", "performance_log.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        empty = [r for r in rows
                 if not ((r.get("metrics") or {}).get("reach", 0)
                         or (r.get("metrics") or {}).get("views", 0))]
        check("no unmeasured rows in learning log", not empty,
              f"{len(empty)} of {len(rows)} rows have no reach/views")
        hookless = [r for r in rows if not str(r.get("hook", "")).strip()]
        check("no hookless rows in learning log", not hookless,
              f"{len(hookless)} of {len(rows)} rows have no hook")

    print(f"\n{'MEASUREMENT INTEGRITY BROKEN' if failures else 'measurement integrity OK'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
