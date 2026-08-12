"""Account-level Instagram funnel analytics.

Instagram exposes profile views, website clicks and follower count at account
level. This module deliberately keeps those signals account-level instead of
pretending they are attributable to individual posts.
"""
from __future__ import annotations


def delta(current: int | float | None, previous: int | float | None) -> int | float | None:
    if current is None or previous is None:
        return None
    return max(0, current - previous)


def build_funnel(current: dict, previous: dict | None = None) -> dict:
    """Build Reach -> Profile Views -> Website Clicks -> Follows at account level."""
    previous = previous or {}
    reach = current.get("reach")
    profile_views = current.get("profile_views")
    website_clicks = current.get("website_clicks")
    followers = current.get("follower_count")

    profile_delta = delta(profile_views, previous.get("profile_views"))
    click_delta = delta(website_clicks, previous.get("website_clicks"))
    follow_delta = delta(followers, previous.get("follower_count"))

    return {
        "reach": reach,
        "profile_views": profile_delta,
        "website_clicks": click_delta,
        "follows_gained": follow_delta,
        "profile_view_rate": (
            profile_delta / reach if profile_delta is not None and reach else None
        ),
        "website_click_rate": (
            click_delta / profile_delta if click_delta is not None and profile_delta else None
        ),
        "follow_rate_from_profile": (
            follow_delta / profile_delta if follow_delta is not None and profile_delta else None
        ),
        "attribution_scope": "account-level; not post-level",
    }
