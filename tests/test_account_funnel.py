"""Tests for truthful account-level funnel analytics."""
from content_generator.analytics.account_funnel import build_funnel


def test_funnel_uses_deltas_and_preserves_scope() -> None:
    result = build_funnel(
        {"reach": 1000, "profile_views": 100, "website_clicks": 20, "follower_count": 130},
        {"profile_views": 60, "website_clicks": 10, "follower_count": 120},
    )
    assert result["profile_views"] == 40
    assert result["website_clicks"] == 10
    assert result["follows_gained"] == 10
    assert result["attribution_scope"] == "account-level; not post-level"


def test_missing_previous_data_is_unknown_not_zero() -> None:
    result = build_funnel({"reach": 1000, "profile_views": 100})
    assert result["profile_views"] is None
    assert result["website_clicks"] is None
    assert result["follows_gained"] is None
