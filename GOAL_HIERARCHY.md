# Goal Hierarchy

When goals conflict, the higher goal wins. Every automated decision in this
repo can be traced to one of these levels.

```
L0  Brand trust survives everything
    (never fabricate, never look AI-generated, never sell what isn't true)
        ↓ constrains
L1  Monthly revenue growth
    (the business exists to sell coffee)
        ↓ is driven by
L2  Audience growth  →  Followers → website visitors → orders → repeat orders → LTV
        ↓ is driven by
L3  Daily content quality
    (one funnel objective per asset, watch-time structure, realism)
        ↓ is improved by
L4  Learning loop fidelity
    (accurate metrics in → honest classification → better prompts out)
```

## Conflict resolution examples

- A hook that would get views by fabricating a statistic → **blocked** (L0 > L2).
  Enforced by `_strip_unsupported_stats` and editorial gate.
- Selling harder at 105 followers would raise short-term revenue but kill reach
  → **blocked** (L2 growth staging > naive L1). Enforced by Growth Director
  ratios: conversion content limited to 1-in-5 days at IGNITION.
- A beautiful cinematic prompt that looks AI-generated → **rejected** (L0).
  Enforced by REALISM_RULES.
- Skipping a day to wait for better content → **rejected** (L3 consistency
  compounds; emergency fallback publishes best-by-score instead).

## Ownership

| Level | Owner |
|---|---|
| L0 | Constitution (this repo's .md documents) — changes require an ADR |
| L1–L2 | Growth Director (`content_generator/core/growth_director.py`) |
| L3 | Generation pipeline + editorial gate |
| L4 | Learning engine + insights fetcher + revenue attribution |
| Everything above | The founder — the system proposes, humans can override |
