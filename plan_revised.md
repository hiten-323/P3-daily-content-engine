1. **Fix Meta API v18.0 -> v24.0 (P0)**
   - Create `config/api_versions.py` containing API versions.
   - Replace hardcoded `"https://graph.facebook.com/v18.0"` with `META_GRAPH_BASE` in all meta-related files.
2. **Fix Shopify API Version (P0)**
   - Replace `"2024-10"` with `SHOPIFY_API_VERSION` in Shopify-related files.
3. **Fix Revenue Attribution Idempotency (P0)**
   - Update `run_revenue_attribution` in `content_generator/analytics/revenue_attribution.py`.
   - Maintain an `attributed_orders.json` ledger.
   - Filter out orders that have already been attributed before calculating `ig_rev` and passing to `_attribute_to_posts`.
4. **Fix Reward Hierarchy (P0)**
   - Modify `score()` in `content_generator/core/reward.py` to use a hierarchical scoring mechanism (e.g., returning a tuple `(revenue, followers, engagement)` or a weighted float where revenue strictly dominates followers). Wait, returning a tuple works for sorting. But `score()` might be expected to return a `float`. We could return a lexicographic float by scaling: `revenue * 1000000 + followers * 1000 + engagement`. Let's look closer at `reward.py` to see how it's used. We can also just return a tuple if Python's `sort()` handles it.
5. **Fix Growth Reel Publishing (P0)**
   - Change `content_generator/scheduler/daily.py` (or `slots.py`) to publish `growth_reel` in the evening instead of `reel_1`.
6. **Stop Emergency Publishing of Unvalidated Assets (P0)**
   - Check where `_best_assets_by_score` is used (probably in `dispatcher.py` or `daily.py` or `fallback.py`) and enforce that `brand_approved` or similar validation flags are `True`.
7. **Fix Unknown-vs-Zero Metric Handling (P0)**
   - Modify `insights_fetcher.py` and remove the `.get(..., 0)` defaults where appropriate, leaving missing metrics as `None` or absent from the dictionary. Do not map reach to views.
8. **Fix Account-Level Attribution (P0)**
   - Find where `follows_gained` etc. are divided by `len(due)` and given to posts. Stop doing that. Only attribute post-level metrics to posts. Keep account-level metrics separate.
9. **Pre commit step**
   - Run `pre_commit_instructions` and follow testing verifications and reflection.
