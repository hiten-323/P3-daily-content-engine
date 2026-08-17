"""Regression tests for learning evidence and commercial objective ordering."""
from __future__ import annotations

import pytest

from content_generator.core.learning_engine import _MIN_LEARNING_SAMPLES, is_teachable
from content_generator.core.reward import score


def test_learning_requires_minimum_sample_count() -> None:
    assert _MIN_LEARNING_SAMPLES >= 5


@pytest.mark.xfail(
    strict=True,
    reason=(
        "UNRESOLVED BUSINESS RULE — not a code defect.\n"
        "This test and test_reward_objective_integrity."
        "test_followers_stage_prioritises_compounding_audience demand opposite "
        "things and cannot both hold:\n"
        "  this one:  Rs 1 + 10 follows  >  10,000 follows\n"
        "  that one:  100 follows        >  Rs 1\n"
        "Solving for the revenue prefix P (follows weight 40): the first needs "
        "P > 425,590, the second needs P < 3,999. No value satisfies both.\n"
        "Resolved for now in favour of the founder documents: GOAL_HIERARCHY.md "
        "blocks naive revenue-over-audience at this stage by name, and the "
        "Growth Director spec ranks follows KPI #1, revenue #9. Attributed "
        "revenue is also a day-level split — a post can be credited Rs 0.33 — "
        "so it should not outrank real audience growth on a rounding artefact. "
        "A completed ORDER still outranks any engagement (ORDER_HIERARCHY).\n"
        "To flip it: set REVENUE_HIERARCHY high in core/reward.py, remove this "
        "marker, and expect test_reward_objective_integrity to fail instead."
    ),
)
def test_revenue_beats_engagement_when_revenue_is_real() -> None:
    engagement = {
        "views": 200_000,
        "follows_gained": 10_000,
        "shares": 2_000,
    }
    commercial = {
        "views": 1_000,
        "follows_gained": 10,
        "revenue": 1,
    }
    assert score(commercial, "followers") > score(engagement, "followers")


def test_orders_beat_noncommercial_engagement() -> None:
    engagement = {"views": 200_000, "follows_gained": 10_000}
    order = {"views": 1_000, "orders": 1}
    assert score(order, "followers") > score(engagement, "followers")


def test_unmeasured_entry_is_not_teachable() -> None:
    assert not is_teachable({"metrics": {}})
    assert not is_teachable({"metrics": {"reach": 100}})
