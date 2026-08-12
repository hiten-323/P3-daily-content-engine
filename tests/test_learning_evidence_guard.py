"""Regression tests for learning evidence and commercial objective ordering."""
from __future__ import annotations

from content_generator.core.learning_engine import _MIN_LEARNING_SAMPLES, is_teachable
from content_generator.core.reward import score


def test_learning_requires_minimum_sample_count() -> None:
    assert _MIN_LEARNING_SAMPLES >= 5


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
