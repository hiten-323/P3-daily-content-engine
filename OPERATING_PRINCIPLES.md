# Operating Principles

These govern every change to this system. They change only through an ADR.

## 1. Prefer evidence over elegance
The simplest solution that measurably improves the business wins. A hardcoded
heuristic that ships today beats an ML pipeline that ships next month.
Example in practice: hook A/B scoring is a deterministic heuristic, not an LLM
call — zero cost, zero latency, good enough to separate strong hooks from weak.

## 2. Learn from money first, engagement second
Revenue dominates the learning score (₹1 = 1 point, order = 25 points,
follow = 10). A post that sells outranks a post that only entertains.
Engagement metrics are leading indicators; orders are the truth.

## 3. Never miss a day
Every pipeline step degrades gracefully: LLM providers cascade
(Groq → Cerebras → Gemini → DeepSeek → OpenRouter), image generation falls back
to Pillow placeholders, publish falls back to best-assets-by-score. A partial
day beats a missed day — consistency is the compounding asset.

## 4. Honesty is enforced, not aspirational
No fabricated statistics (scrubbed before editorial), no invented business
history, no guaranteed-virality claims. The system maximizes probability,
never promises outcomes.

## 5. One objective per asset, never mixed
Every reel serves exactly one funnel goal: DISCOVERY, FOLLOW, AUTHORITY,
CONVERSION, or COMMUNITY. Mixed objectives dilute all of them.

## 6. Stage-appropriate content (Million Follower Mode)
At 105 followers, 95% viral value / 5% selling. Ratios shift automatically as
follower snapshots grow. Selling to strangers wastes reach.

## 7. Brand shows fully or not at all
Growth-track content never shows the product. Brand-track content always shows
the exact jar + buy CTA + https://p3online.in. No middle ground.

## 8. Realism or nothing
Every generated visual must pass as real — skin pores, correct shadows,
lived-in imperfections. AI-looking content destroys trust faster than no
content.

## 9. Improve existing capabilities before adding new ones
80/20 allocation: most effort goes to making the existing loop learn better,
not to new features. Governance before autonomy; resilience before optimization.

## 10. Never repeat a failed pattern
The fatigue guard blocks the last 60 days of hooks/angles. The viral memory's
bottom-20% list is a permanent avoid-list. Winners get reused; failures don't
get second chances without a new angle.
