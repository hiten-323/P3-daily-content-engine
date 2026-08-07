"""
Growth Director spec compliance.

Asserts the founder's operating spec is actually enforced in code, not just
documented. Run: python tests/test_growth_director_spec.py
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
    from content_generator.analytics.hook_selector import score_hook, hook_violations
    from content_generator.core.content_contract import shareability, build_contract
    from content_generator.core.content_balance import classify_asset, MAX_PRODUCT_SHARE
    from content_generator.analytics.viral_scorer import compute_viral_score
    from content_generator.core.reward import get_weights, UNAVAILABLE_KPIS

    # 1. Banned openers must lose to the spec's own example hooks.
    print("\nHook rules:")
    banned = ["Did you know most instant coffee has chicory?",
              "5 tips for better instant coffee",
              "Here's why chicory is added to coffee",
              "7 ways to brew better"]
    approved = ["Your coffee isn't the problem.",
                "This Rs 20 mistake ruins most instant coffee",
                "You're making coffee wrong."]
    worst_ok = min(score_hook(h) for h in approved)
    best_bad = max(score_hook(h) for h in banned)
    for h in banned:
        check(f"penalised: {h[:44]!r}", score_hook(h) < 50, f"{score_hook(h)}")
        check(f"violation named: {h[:30]!r}", bool(hook_violations(h)))
    check("every approved hook beats every banned one", worst_ok > best_bad,
          f"worst approved {worst_ok} vs best banned {best_bad}")

    # 2. North star: generic filler must not publish.
    print("\nNorth-star shareability gate:")
    generic = {"hook": "Start your day with premium quality coffee",
               "caption": "Perfect cup for coffee lovers. Rich aroma. Shop now."}
    teaching = {"hook": "Your coffee turns bitter in 2 minutes. Check the label for chicory.",
                "caption": "Most instant coffee is cut with chicory. Read the ingredient list."}
    check("generic content rejected", not shareability(generic)["passes"],
          str(shareability(generic)["score"]))
    check("specific/teaching content passes", shareability(teaching)["passes"],
          str(shareability(teaching)["score"]))
    check("rejection states a reason", bool(shareability(generic)["reasons"]))

    # 3. 80/20 — product promotion capped.
    print("\n80/20 value-vs-product:")
    check("cap is 20%", abs(MAX_PRODUCT_SHARE - 0.20) < 1e-9, str(MAX_PRODUCT_SHARE))
    check("promo copy classified product", classify_asset(generic) == "product")
    check("teaching copy classified value", classify_asset(teaching) == "value")

    # 4. KPI coverage — the spec's primary KPIs must carry weight, and likes
    #    must not. "Success is NOT measured by likes."
    print("\nReward weights match the spec KPIs:")
    w = get_weights("followers")
    for kpi in ("follows_gained", "shares", "saves", "profile_visits",
                "website_clicks", "avg_view_duration_s", "revenue"):
        check(f"{kpi} carries weight", w.get(kpi, 0) > 0, str(w.get(kpi)))
    check("follows_gained is top-weighted signal",
          max(w, key=w.get) in ("follows_gained", "orders"), max(w, key=w.get))
    check("likes near-zero vs follows", w["likes"] < w["follows_gained"] / 20,
          f"likes={w['likes']} follows={w['follows_gained']}")
    check("unavailable KPIs are documented, not faked",
          "returning_viewers" in UNAVAILABLE_KPIS and "repeat_engagement" in UNAVAILABLE_KPIS)

    # 5. Honesty: no invented predictions before there is data to predict from.
    print("\nPredictions are null until data exists:")
    contract = build_contract(teaching, "test_asset", 1)
    baseline_exists = compute_viral_score(views=100, shares=2) is not None
    if not baseline_exists:
        check("viral_score is None without a baseline", contract["viral_score"] is None)
        check("confidence is 0.0", contract["confidence"] == 0.0, str(contract["confidence"]))
        for f in ("expected_follows", "expected_shares", "expected_saves"):
            check(f"{f} is None", contract[f] is None, str(contract[f]))
        check("basis explains the absence", "invented" in contract["prediction_basis"]
              or "no account baseline" in contract["prediction_basis"],
              contract["prediction_basis"])
    else:
        check("confidence stays below 1.0 with a thin baseline",
              0 < contract["confidence"] < 1.0, str(contract["confidence"]))

    # 6. The 14-field output contract is complete.
    print("\nOutput contract:")
    for field in ("viral_score", "confidence", "expected_follows", "expected_shares",
                  "expected_saves", "why_this_works", "risks", "suggested_thumbnail",
                  "suggested_hook", "caption", "cta", "seo_keywords", "hashtags",
                  "best_posting_time"):
        check(f"field present: {field}", field in contract)

    print(f"\n{'SPEC NOT ENFORCED' if failures else 'growth director spec enforced'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
