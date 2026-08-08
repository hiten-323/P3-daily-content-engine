1. **Fix Meta API v18.0 -> v24.0 (P0)**
   - Create `config/api_versions.py` containing API versions. (Done)
   - Replace hardcoded `"https://graph.facebook.com/v18.0"` with `META_GRAPH_BASE` in all meta-related files. (Done)
2. **Fix Shopify API Version (P0)**
   - Replace `"2024-10"` with `SHOPIFY_API_VERSION` in Shopify-related files. (Done)
3. **Fix Revenue Attribution Idempotency (P0)**
   - Update `run_revenue_attribution` and `_attribute_to_posts` in `content_generator/analytics/revenue_attribution.py`.
   - Maintain an `attributed_orders.json` ledger in `_LEARNING_DIR`. Before calculating `ig_rev`, filter out any orders that are already in the ledger, and add newly processed orders to the ledger.
   - Use `read_file` to confirm the ledger logic is correctly written in `content_generator/analytics/revenue_attribution.py`.
4. **Fix Reward Hierarchy (P0)**
   - Modify `score()` in `content_generator/core/reward.py`.
   - Instead of a single additive float, enforce a revenue floor explicitly. We will modify `score()` to compute `sum_main = float(sum(float(m.get(k, 0) or 0) * weight for k, weight in w.items() if k not in ["revenue", "orders"]))` and `revenue_score = float(m.get("revenue", 0) * w.get("revenue", 0) + m.get("orders", 0) * w.get("orders", 0))`. `score()` will return `float(sum_main + revenue_score * 10000)`. Wait, returning `float` works and effectively lexicographically sorts it. I will change `score()` to `return float(sum_main + revenue_score * 10000)`.
   - Use `read_file` to ensure `score()` in `content_generator/core/reward.py` was updated correctly.
5. **Fix Growth Reel Publishing (P0)**
   - Edit `content_generator/scheduler/slots.py`.
   - In `run_publish_slot` for the `"evening"` slot, change the reel fetching from `reel  = reels[0] if reels and isinstance(reels[0], dict) else {}` to `reel = content.get("growth_reel") or {}`.
   - Use `read_file` to verify the edit in `content_generator/scheduler/slots.py`.
6. **Stop Emergency Publishing of Unvalidated Assets (P0)**
   - In `content_generator/scheduler/daily.py`, edit `_do_publish` where `len(valid_assets) < MIN_REQUIRED_ASSETS`. The audit says "Emergency mode should be: DO NOT PUBLISH + alert founder. Missing a day is preferable to publishing unsafe content."
   - Replace the emergency fallback block that calls `_best_assets_by_score` with an early return or exception if `len(valid_assets) == 0`, and DO NOT add unvalidated assets to `valid_assets`. If `valid_assets` is empty, skip publishing.
   - Use `read_file` to verify the edit in `content_generator/scheduler/daily.py`.
7. **Fix Unknown-vs-Zero Metric Handling (P0)**
   - In `content_generator/analytics/insights_fetcher.py`:
     - Modify `fields = _graph_get(...)` so that if `fields` is None, `likes` and `comments` remain `None`, not `0`. Wait, python's `.get("like_count", None)` instead of `.get("like_count", 0) or 0`.
     - Modify `out` dictionary in `_fetch_media_insights` to `views: raw.get("views")` and `reach: raw.get("reach")` instead of fallback zeros or fallback to reach.
     - Add step to use `read_file` on `content_generator/analytics/insights_fetcher.py` to verify edits.
8. **Fix Account-Level Attribution (P0)**
   - In `content_generator/analytics/insights_fetcher.py`, in `fetch_pending_insights`, remove the lines allocating `follows_gained_total // len(due)` and `profile_views // len(due)` to post `metrics`.
   - Instead, record account metrics in a separate file (e.g. `ACCOUNT_DAILY_METRICS`) and do not attach them to `metrics` for individual posts.
   - Use `read_file` on `content_generator/analytics/insights_fetcher.py` to verify the edit.
9. **Pre commit step**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
10. **Run test suite**
    - Run `python verify_refactor.py` and specific test scripts `python tests/test_measurement_integrity.py`, `python tests/test_render_safety.py`, and `python tests/test_config_drift.py`.
