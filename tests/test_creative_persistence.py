"""
Creative output must survive between slots.

Each slot is a separate workflow run on a separate GitHub runner. Images written
by the 00:30 generate run do not exist on the 04:30 publish runner unless Git
carries them, so the commit step has to stage output/creative/.

0d20beb added that line when timed slots landed, for exactly this reason.
c345418 ("make workflow persistence atomic and Git-authoritative") removed it in
favour of keeping large media out of Git — and every Instagram image post since
has failed with no_images, while Facebook, which posts text, kept succeeding:

    [instagram] Images discovered: []
    [instagram] No images found — skipping Instagram post
    INSTAGRAM  FAIL no_images

The prune line was left behind, which is the tell: you only prune what you keep.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"


def _commit_step() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index("git config user.name")
    return text[start:start + 2500]


def test_commit_step_stages_creative_output() -> None:
    step = _commit_step()
    assert re.search(r"git add -f output/creative/?", step), (
        "the commit step does not stage output/creative/. Publish slots run on a "
        "different runner than the generate slot, so uncommitted images are gone "
        "by the time Instagram is posted — the failure is 'no_images'."
    )


def test_pruning_creative_implies_keeping_it() -> None:
    """A prune with no matching add is the exact shape of the c345418 regression."""
    step = _commit_step()
    prunes = "output/creative" in step and "-delete" in step
    if prunes:
        assert "git add -f output/creative" in step, (
            "output/creative is pruned but never staged. Pruning only makes sense "
            "for files that persist; this combination means images are being "
            "deleted from a runner that was never going to keep them anyway."
        )


def test_content_json_is_still_staged() -> None:
    """The sibling guarantee — content and its images must persist together."""
    step = _commit_step()
    assert "output/content_" in step and "git add" in step, (
        "the day's content JSON must be committed, or publish slots hold with "
        "no_content_for_today"
    )


def test_prune_is_not_mtime_based() -> None:
    """
    Every run starts with a fresh checkout, which stamps every file's mtime as
    "now". `find output/creative -mtime +7` therefore matched nothing on the
    runner: growth was bounded in theory and unbounded in fact — July media was
    still in the tree weeks later. The prune must key off the date embedded in
    the filename instead.
    """
    step = _commit_step()
    assert not re.search(r"find\s+output/creative.*-mtime", step), (
        "creative is pruned by mtime, which is always 'now' after checkout — "
        "the prune is a no-op and the repo grows without bound"
    )


def test_prune_still_exists_in_some_form() -> None:
    """Committing creative without any prune is the other failure mode."""
    step = _commit_step()
    assert "output/creative" in step and ("os.remove" in step or "-delete" in step), (
        "output/creative is committed but never pruned — ~1MB/day, forever"
    )
