"""
Story frames must not reprint the same two hardcoded lines every day.

The live stories that looked identical except for the jar were composed by
post_story falling through to:
    "REAL COFFEE. ZERO CHICORY."
    "Reply and tell me how you take your coffee"
whenever content["stories"] was missing — which is every evergreen-fallback
day, and every day extended content is off.

Run: python tests/test_story_copy.py
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
    from content_generator.publisher.story_copy import (
        STORY_COPY_BANK, resolve_story_copy, stories_block_from_content,
    )
    from content_generator.scheduler.fallback import _from_evergreen, emergency_content_set

    banned_h = "REAL COFFEE. ZERO CHICORY."
    banned_s = "Reply and tell me how you take your coffee"

    print("\nGenerated story_1 wins:")
    copy = resolve_story_copy({
        "stories": {"story_1": {
            "headline": "THIS OR THAT",
            "subtext": "Milk or black this morning",
            "poll_question": "Milk or black?",
        }},
        "reels": [{"hook": "Turn the jar around before you buy it."}],
    }, day=237)
    check("uses generated headline", copy["headline"] == "THIS OR THAT", copy["headline"])
    check("uses generated subtext", "Milk or black" in copy["sub"], copy["sub"])
    check("source is stories", copy["source"] == "stories.story_1", copy["source"])

    print("\nEvergreen fallback (no stories key) uses today's reel overlay:")
    evergreen = {
        "reels": [{
            "hook": "Turn the jar around before you buy it.",
            "hook_text_overlay": "READ THE BACK",
            "comment_trigger": "What does the label on your jar actually say?",
        }],
        "carousel": {"hook": "Three things to check on a coffee label"},
        "_source": "emergency_fallback_evergreen",
    }
    copy = resolve_story_copy(evergreen, day=237)
    check("not the banned headline", copy["headline"].upper() != banned_h, copy["headline"])
    check("not the banned sub", copy["sub"] != banned_s, copy["sub"])
    check("uses overlay READ THE BACK", copy["headline"].upper() == "READ THE BACK", copy["headline"])
    check("uses reel comment as sub", "label" in copy["sub"].lower(), copy["sub"])

    print("\nEmpty content rotates the bank instead of a slogan:")
    a = resolve_story_copy({}, day=1)
    b = resolve_story_copy({}, day=2)
    check("bank headline on empty content", a["headline"] in {h for h, _ in STORY_COPY_BANK})
    check("two consecutive days differ", (a["headline"], a["sub"]) != (b["headline"], b["sub"]),
          f"{a} vs {b}")
    check("empty path is not banned pair",
          not (a["headline"].upper() == banned_h and a["sub"] == banned_s))

    print("\nAssembled evergreen set now carries stories:")
    content = _from_evergreen(237)
    stories = content.get("stories") or {}
    check("evergreen includes stories.story_1", isinstance(stories.get("story_1"), dict))
    if stories.get("story_1"):
        h = str(stories["story_1"].get("headline") or "")
        check("evergreen story headline is not banned slogan", h.upper() != banned_h, h)

    assembled = emergency_content_set(237)
    copy = resolve_story_copy(assembled, day=237)
    check("emergency set copy is not banned pair",
          not (copy["headline"].upper() == banned_h and copy["sub"] == banned_s),
          f"{copy['headline']} | {copy['sub']}")

    print("\nstories_block_from_content shape:")
    block = stories_block_from_content(evergreen, day=237)
    check("story_1 type is poll", block["story_1"]["type"] == "poll")
    check("headline present", bool(block["story_1"]["headline"]))

    print(f"\n{'STORY COPY REGRESSION' if failures else 'story copy ok'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


def test_main():
    rc = main()
    assert rc in (0, None), f"suite reported failures (rc={rc})"


if __name__ == "__main__":
    raise SystemExit(main())
