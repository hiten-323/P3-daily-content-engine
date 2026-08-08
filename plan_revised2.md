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
   - Instead of a single additive float, enforce a revenue floor explicitly. The problem statement says: "use lexicographic / gated optimization".
   - Wait, `score()` is used heavily in `sorted(..., key=score)`. A tuple will sort lexicographically! So `score()` will be changed to return a tuple `(revenue_score, main_score)` or something similar where revenue guarantees top ranking. If `float` return is explicitly typed in python, I'll return `float(revenue_score * 10000 + main_score)`. I'll verify the logic by inspecting `reward.py` and modify it. I'll make it return `float(sum_main + revenue * 10000)`.
5. **Fix Growth Reel Publishing (P0)**
   - Edit `content_generator/scheduler/slots.py`.
   - In `run_publish_slot` for the `"evening"` slot, change `reel = reels[0]` (which corresponds to `reel_1`) to fetch `growth_reel`.
   - `content.get("growth_reel")` instead of `reel_1`.
6. **Stop Emergency Publishing of Unvalidated Assets (P0)**
   - In `content_generator/scheduler/daily.py`, edit `_best_assets_by_score`.
   - Add a strict filter: only consider assets where `piece.get("brand_approved") == True` and `piece.get("truth_approved") == True` (or similar validation flags). I will read `core/editorial_engine.py` to see what flags are set on successful validation and filter by them.
7. **Fix Unknown-vs-Zero Metric Handling (P0)**
   - In `content_generator/analytics/insights_fetcher.py`:
     - Modify `fields = _graph_get(...)` so that if `fields` is None, `likes` and `comments` remain `None`, not `0`.
     - Modify `out` dictionary in `_fetch_media_insights` to `views: raw.get("views")` and `reach: raw.get("reach")` instead of fallback zeros or fallback to reach.
8. **Fix Account-Level Attribution (P0)**
   - In `content_generator/analytics/insights_fetcher.py`, remove the lines `if follows_gained_total: metrics["follows_gained"] = follows_gained_total // len(due)` etc.
   - Instead, record account metrics in a separate file `ACCOUNT_DAILY_METRICS` (e.g. `output/learning/account_metrics.json`) and do not attach them to `metrics` for `record_performance`.
9. **Pre commit step**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
10. **Run test suite**
    - Run `python verify_refactor.py` and all pytest tests.
