# Policy Engine

The rules the system enforces automatically, and where each lives in code.
These are running policies, not aspirations — each row is executable today.

## Content policies

| Policy | Enforcement point |
|---|---|
| No fabricated statistics ("9 out of 10…", "studies show…") | `daily._strip_unsupported_stats` — sentence removed before editorial |
| No medical/weight-loss claims | `FORBIDDEN_TERMS` in brand_guard + editorial review |
| No competitor names in copy or image prompts | `brand_guardrails.validate_copy` / `validate_image_prompt` (auto-replaced) |
| English only | `LANGUAGE_POLICY` in every system prompt |
| Editorial threshold: score < 6.5 → reject, regenerate (max 1) | `editorial_engine.enforce_editorial_gate`, `PASS_SCORE` |
| Verdict never contradicts score | `normalize_editorial_result` — score is authoritative |

## Brand policies

| Policy | Enforcement point |
|---|---|
| Product shown ⇒ exact jar + buy CTA + p3online.in (all three) | System prompt PRODUCT VISIBILITY RULE + `_inject_brand_into_piece` safety net |
| Growth-track content: zero brand presence | growth_reel prompt hard rules; bypasses brand injection by design |
| Jar images: only real files from brand_assets/, product-matched | `get_product_references` — returns [] rather than inventing |
| Every visual engineered for realism; AI-tell words banned | REALISM_RULES + `enforce_brand_prompt` suffix |

## Publishing policies

| Policy | Enforcement point |
|---|---|
| Publish at algorithm-optimal windows (08:00 / 20:00 IST for IG) | `scheduler/slots.py` + 3 cron triggers |
| Never publish twice in one slot | Per-slot `RunLock`, locks committed across CI runs |
| Never miss a day: < 2 valid assets → publish top-2 by score | `_best_assets_by_score` emergency fallback |
| Hashtags: adaptive 25 from scored bank, never trimmed by caption limit | `hashtag_bank.select_hashtags` + `_assemble_caption` |
| Only the highest-scoring hook publishes | `hook_selector.run_hook_ab` before editorial |

## Learning policies

| Policy | Enforcement point |
|---|---|
| Metrics auto-recorded ≥20h after posting; never double-recorded | `insights_fetcher.fetch_pending_insights` (idempotent) |
| Optimizer needs ≥12 samples before trusting history | `optimizer._MIN_DATA_SAMPLES` |
| Bottom-20% structures never repeated | viral memory block in every prompt |
| No hook/angle reuse within 60 days | `hook_selector.get_fatigue_block` |
| Learning state survives CI runs | workflow persist step commits `output/learning/` |

## Change control

Constitutional documents (MISSION, OPERATING_PRINCIPLES, SUCCESS_METRICS,
GOAL_HIERARCHY, this file, ARCHITECTURE) change only through a new ADR in
`docs/`. Operational parameters (thresholds, banks, rotations) change through
normal commits.
