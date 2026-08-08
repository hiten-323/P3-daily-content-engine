1. **Fix Meta API v18.0 -> v24.0 (P0)**
   - Created `config/api_versions.py` and replaced all hardcoded `"https://graph.facebook.com/v18.0"` with `META_GRAPH_BASE` in the following files:
     - `content_generator/nurture/whatsapp.py`
     - `content_generator/publisher/instagram.py`
     - `content_generator/publisher/product_tags.py`
     - `content_generator/publisher/facebook.py`
     - `content_generator/analytics/insights_fetcher.py`
     - `content_generator/analytics/brand_signals.py`
2. **Fix Shopify API Version (P0)**
   - Replaced `"2024-10"` with `SHOPIFY_API_VERSION` from `config/api_versions.py` in `content_generator/analytics/revenue_attribution.py` and `content_generator/publisher/shopify_blog.py`.
3. **Fix Revenue Attribution Idempotency (P0)**
   - Modify `run_revenue_attribution` and `_attribute_to_posts` in `content_generator/analytics/revenue_attribution.py`.
   - Pass a list of `ig_orders` with their `id`s to `_attribute_to_posts`.
   - Create a global `attributed_orders` ledger (e.g. `output/learning/attributed_orders.json`) or check inside `learning_engine.py`'s log to avoid double counting the same order. Since attribution is split across posts, we need to mark an order as "attributed" so it is not processed on day 2.
4. **Fix Reward Hierarchy (P0)**
   - Modify `content_generator/core/reward.py` to enforce lexicographic/gated optimization instead of additive weights.
   - A post that has revenue/orders should strictly rank higher than a post with no revenue/orders (if revenue floor is required), or at least we enforce rules that `followers` doesn't purely outscore `orders` mathematically when not intended. Actually, we should follow the logic: `rank by revenue first, then followers as tie-breaker` if revenue signal is available. Wait, the user specifically mentioned: `L1 Revenue floor -> compare qualifying assets, L2 Audience growth -> optimize within qualifying assets`. We can implement a lexicographic scoring system in `score()` or `explain()`.
5. **Fix Growth Reel Publishing (P0)**
   - Check `content_generator/scheduler/daily.py` or wherever publishing slots are defined.
   - Replace the evening `reel_1` with `growth_reel`.
6. **Stop Emergency Publishing of Unvalidated Assets (P0)**
   - Check fallback or dispatcher logic where `_best_assets_by_score` is used.
   - Ensure it strictly filters for validated assets, or skips the slot instead of publishing an invalid asset.
7. **Fix Unknown-vs-Zero Metric Handling (P0)**
   - Check `content_generator/analytics/insights_fetcher.py` and any other insight fetching code.
   - Set missing metrics to `None` instead of `0`.
   - Avoid substituting `views = raw.get("views", raw.get("reach", 0))`.
8. **Fix Account-Level Attribution (P0)**
   - Remove account-level follower gains from per-post `followers` attribution. Keep them separate.
   - Pre-commit step.
