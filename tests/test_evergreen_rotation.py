"""
Fallback content must rotate, and must be reproducible.

_from_evergreen used to random.shuffle(_EVERGREEN) and take the first of each
type. _EVERGREEN held exactly one template per type, so that was a shuffle of a
single-element list: every fallback day produced byte-identical content.

Because no day has ever produced real generation, that was every post the
account has made — the same reel, the same carousel, the same caption, for
weeks. It is the largest single reason the feed reads as boring.

Selection is now indexed by day rather than randomised, which guarantees
consecutive days differ (shuffling only made it likely) and makes any given day
reproducible, so a bad post can be traced to a template rather than to an
unrecoverable RNG draw.
"""
from __future__ import annotations

from content_generator.scheduler.fallback import (
    _EVERGREEN,
    _from_evergreen,
    _of_type,
)


def _days(n: int, start: int = 500) -> list[dict]:
    return [_from_evergreen(d) for d in range(start, start + n)]


def test_every_type_has_more_than_one_template() -> None:
    """A single template per type makes any selection strategy a no-op."""
    for kind in ("reel", "carousel", "instagram_post"):
        assert len(_of_type(kind)) > 1, (
            f"only {len(_of_type(kind))} {kind} template(s) — rotation cannot "
            "produce variety from a pool of one, which is how every post became identical"
        )


def test_consecutive_days_differ() -> None:
    a, b = _from_evergreen(500), _from_evergreen(501)
    assert a["reels"][0]["hook"] != b["reels"][0]["hook"]
    assert a["carousel"]["hook"] != b["carousel"]["hook"]
    assert a["instagram_post"]["hook"] != b["instagram_post"]["hook"]


def test_a_full_cycle_uses_every_template() -> None:
    """Rotation should exhaust the pool, not favour a subset."""
    for kind, key in (("reel", "reels"), ("carousel", "carousel"),
                      ("instagram_post", "instagram_post")):
        span = len(_of_type(kind))
        got = set()
        for c in _days(span):
            piece = c[key][0] if key == "reels" else c[key]
            got.add(piece["hook"])
        assert len(got) == span, f"{kind}: {len(got)} distinct across a {span}-day cycle"


def test_the_two_reels_in_a_day_are_never_the_same() -> None:
    for c in _days(12):
        assert c["reels"][0]["hook"] != c["reels"][1]["hook"], (
            "reel_1 and reel_2 are the same piece — the day publishes one idea twice"
        )


def test_selection_is_reproducible() -> None:
    """
    Determinism is the point: with random.shuffle, a day that shipped bad
    content could not be reconstructed. Same day in, same content out.
    """
    for day in (500, 733, 1042):
        first, second = _from_evergreen(day), _from_evergreen(day)
        assert first["reels"][0]["hook"] == second["reels"][0]["hook"]
        assert first["carousel"]["hook"] == second["carousel"]["hook"]
        assert first["instagram_post"]["hook"] == second["instagram_post"]["hook"]


def test_every_template_is_reachable() -> None:
    """A template the rotation never selects is dead weight that still ships risk."""
    span = max(len(_of_type(k)) for k in ("reel", "carousel", "instagram_post"))
    reached = set()
    for c in _days(span * 2):
        reached.add(c["reels"][0]["hook"])
        reached.add(c["reels"][1]["hook"])
        reached.add(c["carousel"]["hook"])
        reached.add(c["instagram_post"]["hook"])
    for t in _EVERGREEN:
        if t["type"] in ("reel", "carousel", "instagram_post"):
            assert t["hook"] in reached, f"template never selected: {t['type']} / {t['hook'][:50]}"
