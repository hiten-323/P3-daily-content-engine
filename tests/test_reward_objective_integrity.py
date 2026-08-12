"""Regression tests for the canonical reward/objective contract."""

from content_generator.core.reward import explain, score


def test_reward_is_explicitly_kpi_aware():
    metrics = {"follows_gained": 100, "revenue": 1000, "orders": 1}
    assert score(metrics, "followers") != score(metrics, "revenue")
    assert explain(metrics, "followers")["kpi"] == "followers"
    assert explain(metrics, "revenue")["kpi"] == "revenue"


def test_followers_stage_prioritises_compounding_audience():
    audience = {"follows_gained": 100, "revenue": 0, "orders": 0}
    tiny_sale = {"follows_gained": 0, "revenue": 1, "orders": 0}
    assert score(audience, "followers") > score(tiny_sale, "followers")


def test_revenue_stage_prioritises_orders_and_revenue():
    sale = {"revenue": 1000, "orders": 1, "follows_gained": 0}
    audience = {"revenue": 0, "orders": 0, "follows_gained": 100}
    assert score(sale, "revenue") > score(audience, "revenue")


def test_revenue_and_orders_have_nonzero_floor_in_every_profile():
    for kpi in ("followers", "engagement", "revenue"):
        explanation = explain({"revenue": 1, "orders": 1}, kpi)
        assert explanation["contributions"]["revenue"] > 0
        assert explanation["contributions"]["orders"] > 0
