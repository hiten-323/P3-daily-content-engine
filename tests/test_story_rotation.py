"""
Fallback story copy must rotate.

Original defect: post_story hardcoded a slogan, so every story read
"REAL COFFEE. ZERO CHICORY. / Reply and tell me how you take your coffee",
day after day, with only the jar changing.

First fix resolved copy from today's content instead. But evergreen fallback
content is IDENTICAL every day — same reel, same overlay, same comment trigger —
so deriving from it reprinted one line forever, and the day-rotated bank became
unreachable on exactly the days it exists for. Measured before the second fix:
nine consecutive fallback days produced ONE distinct story line. The bug had
moved a tier, not gone.

Recycled days now take the bank. Genuinely generated days keep their own copy,
which is the whole point of the tier order.
"""
from __future__ import annotations

from content_generator.publisher.story_copy import (
    STORY_COPY_BANK,
    resolve_story_copy,
)

_BANNED = ("REAL COFFEE. ZERO CHICORY.", "ZERO CHICORY")


def _fallback(day: int) -> dict:
    """The shape emergency_content_set produces: constant copy, marked recycled."""
    return {
        "day_number": day,
        "_source": "emergency_fallback_evergreen",
        "_recycled": True,
        "reels": [{
            "hook": "Turn the jar around before you buy it.",
            "hook_text_overlay": "READ THE BACK",
            "comment_trigger": "What does the label on your jar actually say?",
        }],
        "carousel": {"hook": "Three things to check on a coffee label"},
    }


def test_fallback_days_do_not_repeat_one_line() -> None:
    span = len(STORY_COPY_BANK)
    seen = {
        (o["headline"], o["sub"])
        for o in (resolve_story_copy(_fallback(d), d) for d in range(200, 200 + span))
    }
    assert len(seen) == span, (
        f"{len(seen)} distinct story lines across {span} fallback days — recycled "
        "content is constant, so anything derived from it repeats forever"
    )


def test_fallback_never_prints_the_slogan() -> None:
    for day in range(200, 240):
        o = resolve_story_copy(_fallback(day), day)
        joined = f"{o['headline']} {o['sub']}".upper()
        for banned in _BANNED:
            assert banned not in joined, f"day {day} reprinted the slogan: {o}"


def test_generated_days_still_use_their_own_copy() -> None:
    """
    Rotation applies ONLY to recycled days. A real generated day must keep its
    own hook, or this fix would discard the content the engine exists to make.
    """
    generated = {
        "day_number": 300,
        "_source": "llm",
        "reels": [{
            "hook": "The cheapest jar costs the most per cup.",
            "hook_text_overlay": "COST PER CUP",
            "comment_trigger": "How much are you actually paying per cup?",
        }],
    }
    out = resolve_story_copy(generated, 300)
    assert out["headline"] == "COST PER CUP"
    assert out["source"].endswith(".overlay")
    assert out["source"] != "story_bank.recycled"


def test_generated_story_1_still_wins() -> None:
    """An LLM-written story is the highest tier and must not be overridden."""
    content = {
        "day_number": 301,
        "_source": "llm",
        "stories": {"story_1": {"headline": "SIX RUPEES", "subtext": "That is the gap per cup."}},
    }
    out = resolve_story_copy(content, 301)
    assert out["headline"] == "SIX RUPEES"
    assert out["source"] == "stories.story_1"


def test_bank_carries_no_verifiable_claims() -> None:
    """
    This copy ships unreviewed on every fallback day. The engine's history is
    fabricated statistics reaching live posts, so the bank goes through the
    same verifier as generated copy.
    """
    from content_generator.core.claim_verifier import verify_claims

    for headline, sub in STORY_COPY_BANK:
        flagged = verify_claims(f"{headline}. {sub}")
        assert not flagged, f"story bank line carries an unverifiable claim: {headline} / {sub} -> {flagged}"
