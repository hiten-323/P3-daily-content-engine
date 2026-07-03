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

## Weekly Founder Brief (auto-derivable from stored data)

PPOI trend · follower trend · top-3 winning structures (viral memory) ·
top-3 risks (fatigue/quota/token expiry) · one actionable recommendation.
