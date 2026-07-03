# Success Metrics

Data sources: Instagram Graph API insights (`output/learning/performance_log.json`),
follower snapshots (`follower_snapshots.json`), Shopify orders (`revenue_log.json`).
All collected automatically by the daily pipeline.

## North-star hierarchy

| Priority | Metric | Definition | Source |
|---|---|---|---|
| 1 | **Monthly Revenue Growth** | Shopify paid orders, month over month | revenue_log.json |
| 2 | **IG-Attributed Revenue** | Orders with instagram.com / l.instagram.com / utm_source=instagram | revenue_attribution.py |
| 3 | **Follower Growth Rate** | Day-over-day follower delta | follower_snapshots.json |
| 4 | **Follows per 1K Reach** | The true content-quality signal | insights ÷ reach |

## Engagement score (learning-engine weighting)

```
score = revenue×1.0 + orders×25 + follows×10 + shares×5 + saves×4
      + comments×3 + profile_visits×2 + likes×1 + views×0.01
```

Revenue dominates by design (Principle 2). Posts are classified against the
account's own median: top 20% = reuse structures, bottom 20% = never repeat.

## Founder-OS metrics (from the Master Working Document)

- **PPOI** (Profit Per Order Instagram): ig_revenue ÷ ig_orders — tracked daily.
- **FLR** (Follower-to-Lead Rate): follows gained ÷ reach — proxy until email
  capture exists (see UNKNOWNS.md).
- **LTV proxy**: returning_customers count in daily revenue snapshots.
- **Decision Latency**: time from insight to strategy change = 1 day by
  construction (insights fetched before generation every morning).
- **Founder Cognitive Load**: manual steps per day. Current: 1 (produce reel
  video from tool brief). Target: hold at ≤2.

## Stage gates (Million Follower Mode)

| Stage | Followers | Content ratio | Success = |
|---|---|---|---|
| IGNITION | 0–1K | 95/5 | Any reel >10K reach; +30 followers/week |
| TRACTION | 1K–10K | 85/15 | First attributed order from a reel |
| MOMENTUM | 10K–100K | 70/30 | IG revenue ≥ 20% of total revenue |
| SCALE | 100K+ | 50/50 | Repeat-order rate ≥ 25% |

## EVPOI — Enterprise Value Per Organic Impression

```
EVPOI v1 = IG-attributed revenue ÷ organic impressions × 1000
```
Attribution is **first-touch** via Shopify customer journeys
(`customerJourneySummary`), so a reel that started a journey days before a
Google-search checkout still gets credit — it never collapses to last-click.

## Brand Equity Score (0–10)

```
Brand Equity = repeat_purchase_rate×0.3 + branded_search_index×0.2
             + ugc_creation_rate×0.2 + review_sentiment×0.3
```
- Repeat purchase rate: **auto** from revenue snapshots (25% repeat = 10/10)
- Other three: weekly manual entry in `output/learning/brand_equity_inputs.json`
  until data sources exist (Search Console, tagged posts, reviews)
- Policy: if Brand Equity < 6/10, prioritize trust/education content over
  aggressive conversion content.

## Weekly Founder Brief (Mondays, auto — `analytics/founder_brief.py`)

Exactly three numbers, nothing else:
1. **EVPOI** (₹ per 1,000 impressions, 7-day)
2. **Brand Equity Score** (with components)
3. **Learning Velocity** (hooks validated / retired this week)

If a metric doesn't answer "value per impression / brand health / getting
smarter", it does not belong in the brief.
