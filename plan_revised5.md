1. **Fix Meta API v18.0 -> v24.0 (P0)** (Done)
2. **Fix Shopify API Version (P0)** (Done)
3. **Fix Revenue Attribution Idempotency (P0)**
   - Wait, `attributed` needs to actually attribute before marking the ledger.
   - Refactor `run_revenue_attribution` in `content_generator/analytics/revenue_attribution.py`: first call `_attribute_to_posts(new_ig_rev, new_ig_orders, since)`, and if it returns `> 0`, THEN add the `new_ig_orders` to the ledger using a dict `{"order_id": {"attributed_at": now.isoformat()}}` instead of a set so that the ledger can properly track attribution.
4. **Fix Reward Hierarchy (P0)**
   - The user noted that `sum_main + revenue_score * 10000` is NOT lexicographic. `score()` must be modified to return a true tuple `(revenue, main)` instead of a float. We will need to change `score()` in `content_generator/core/reward.py` to return `(float, float)`.
   - Also, `explain()` needs to handle this tuple correctly. Let's make `explain` calculate total score correctly or return the tuple.
   - Since `score` currently returns `float`, we need to check how callers use `score()`. If they just sort by it, `(float, float)` works perfectly. But let's check `_engagement_score()` in `learning_engine.py` - if it sums them or multiplies them, we might need to modify `learning_engine.py` to handle tuples.
5. **Fix Growth Reel Publishing (P0)**
   - In `content_generator/scheduler/slots.py`, `run_publish_slot` was updated to pick `growth_reel`. But we need to ensure its track is set to `"growth"`, funnel objective to `"DISCOVERY"`, and business objective to `"Audience Growth"`.
6. **Stop Emergency Publishing of Unvalidated Assets (P0) & Canonical Gate**
   - The user noticed that `slots.py` directly calls `post_content(content)` and `post_reel_video(video_url)` without calling `get_valid_assets()`.
   - We must enforce that `slots.py` ONLY publishes assets that are within `get_valid_assets(content)`.
   - For `slots.py` `"morning"`: verify that `"carousel"` or `"instagram_post"` is in `valid_assets` before publishing.
   - For `slots.py` `"evening"`: verify that `"growth_reel"` is in `valid_assets` before publishing.
   - We should delete `_best_assets_by_score` in `daily.py`.
7. **Fix Unknown-vs-Zero Metric Handling (P0)**
   - User noted that `_fetch_account_insights` still has `values[0].get("value", 0) or 0`. Modify it to use `.get("value")`.
8. **Fix Account-Level Attribution (P0)**
   - Account attribution was fixed, but we need to persist `follows_gained` in `account_metrics.json`.
9. **Pre commit step**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
10. **Run test suite**
    - Run `python verify_refactor.py` and the specific tests mentioned. Wait, the tests weren't failing initially, but my changes broke `python verify_refactor.py` (which actually passed 25/25 initially before I ran it, but when I ran it, it said `No module named 'requests'`). Oh, I need to ensure requirements are installed properly. I already ran `pip install -r requirements.txt`.
