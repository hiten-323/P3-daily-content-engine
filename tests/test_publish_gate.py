"""
Publish gate safety.

Every check here is a route by which unvalidated content reached the API.
Run: python tests/test_publish_gate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

failures = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main():
    from content_generator.core import editorial_engine as ee
    from content_generator.core.reward import score

    # 1. THE BUG: an invalid growth_reel must never publish just because reel_1
    #    is valid. The old guard was `growth_reel not in valid AND reel_1 not in
    #    valid` followed by an unconditional content["growth_reel"].
    print("\nInvalid growth_reel never publishes:")
    content = {
        "growth_reel": {"type": "reel", "hook": "Start your day with premium quality coffee"},
        "reels": [{"type": "reel", "hook": "Check the label: chicory turns coffee bitter in 2 minutes"}],
    }
    real_valid = ee.get_valid_assets
    try:
        ee.get_valid_assets = lambda c: ["reel_1"]          # growth_reel REJECTED
        approved = ee.approved_assets(content)
        check("growth_reel absent from approved set", "growth_reel" not in approved,
              str(sorted(approved)))
        chosen = approved.get("growth_reel") or approved.get("reel_1")
        check("selection falls to the validated reel_1",
              chosen is not None and "chicory" in str(chosen.get("hook", "")),
              str(chosen))

        # 2. Nothing valid -> nothing publishable.
        ee.get_valid_assets = lambda c: []
        approved = ee.approved_assets(content)
        check("no valid assets -> empty approved set", approved == {}, str(approved))

        # 3. The gate returns OBJECTS, so selection cannot disagree with
        #    validation by looking the asset up a second time.
        ee.get_valid_assets = lambda c: ["growth_reel"]
        approved = ee.approved_assets(content)
        check("approved set contains the object, not just the name",
              isinstance(approved.get("growth_reel"), dict))
    finally:
        ee.get_valid_assets = real_valid

    # 4. GOAL_HIERARCHY: "Selling harder at 105 followers would raise short-term
    #    revenue but kill reach -> blocked (L2 growth staging > naive L1)."
    #    A lexicographic (revenue, engagement) tuple inverted this.
    print("\nReward respects GOAL_HIERARCHY (L2 > naive L1):")
    tiny_revenue = score({"revenue": 1.0, "orders": 0, "follows_gained": 0})
    big_audience = score({"revenue": 0, "orders": 0, "follows_gained": 10000})
    check("10k followers outrank Rs 1 of revenue", big_audience > tiny_revenue,
          f"{big_audience} vs {tiny_revenue}")
    check("score is a scalar, not a tuple", isinstance(tiny_revenue, float),
          type(tiny_revenue).__name__)

    # ...but the revenue floor still holds: same audience + revenue must win.
    without = score({"follows_gained": 10, "shares": 2})
    with_rev = score({"follows_gained": 10, "shares": 2, "revenue": 500, "orders": 1})
    check("revenue floor intact (same audience + revenue ranks higher)",
          with_rev > without, f"{with_rev} vs {without}")

    # 5. Unknown must never be recorded as a measured zero.
    print("\nUnknown vs zero, account insights:")
    from content_generator.analytics import insights_fetcher as ins
    real_get = ins._graph_get
    try:
        os.environ.setdefault("INSTAGRAM_ACCOUNT_ID", "test_account")
        # Metric present but with no value -> must be absent, not 0.
        ins._graph_get = lambda p, q: {"data": [{"name": "profile_views", "values": [{}]}]}
        out = ins._fetch_account_insights()
        check("missing value is omitted, not zeroed", "profile_views" not in out, str(out))
        # A genuine measured zero must survive.
        ins._graph_get = lambda p, q: {"data": [{"name": "profile_views",
                                                 "values": [{"value": 0}]}]}
        out = ins._fetch_account_insights()
        check("measured zero is preserved", out.get("profile_views") == 0, str(out))
    finally:
        ins._graph_get = real_get

    # 6. Revenue attribution reports order ids, not a post tally.
    print("\nRevenue attribution semantics:")
    import datetime
    from content_generator.analytics.revenue_attribution import _attribute_to_posts
    res = _attribute_to_posts([{"id": "1", "total_price": "500"}],
                              datetime.datetime.now() + datetime.timedelta(days=1))
    for key in ("attributed_order_ids", "unattributed_order_ids",
                "attributed_revenue", "posts_updated"):
        check(f"result has {key}", key in res)
    check("no posts in window -> order stays pending",
          res["attributed_order_ids"] == [] and res["unattributed_order_ids"] == ["1"],
          str(res))

    print(f"\n{'PUBLISH GATE UNSAFE' if failures else 'publish gate safe'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
