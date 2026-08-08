# ADR-002 — Scroller Psychology Layer: Scope

**Status:** Proposed (not started)
**Date:** 2026-08-08
**Blocks on:** measurement working (see Phase 0)

## The proposal

Add a layer that decides *why someone stops scrolling*, distinct from the
existing coffee-psychology layer that decides *why someone cares, shares or
buys*. Two registries, never merged:

```
Scroller Psychology  →  "Why would someone stop?"
        ↓
Coffee Psychology    →  "Why would someone share/save/follow/buy?"
        ↓
Verified facts       →  "What are we allowed to say?"
        ↓
Creative execution
```

The direction is right. This document scopes it against what the engine
already has, because roughly half of the proposal is already built and
building it twice would be worse than not building it at all.

---

## Already exists — do NOT rebuild

| Proposal asks for | Already in the repo |
|---|---|
| One canonical publish gate | `editorial_engine.approved_assets()` |
| Daily content decision / planner | `intelligence/decision_layer.plan_today()` + `attach_asset_metadata()` |
| Do not create a second reward function | `core/reward.py` is already the single definition; `viral_scorer` delegates to it |
| Verified fact boundary | `core/claim_verifier.py` + the stat/competitor scrubbers |
| Product as proof, ≤20% promotion | `core/content_balance.py` |
| Hook quality scoring, banned openers | `analytics/hook_selector.py` |
| Share/save-worthiness gate | `content_contract.shareability()` (north star) |
| Per-run self-audit block | `analytics/self_audit.py` |
| Psychology governance by risk level | `editorial_engine.resolve_psychology_governance()` (fails closed) |
| Recency-weighted learning, no outlier dominance | `learning_engine` 30-day half-life + objective gating |

**Cut from scope entirely.** Extending these is in scope; duplicating them is not.

---

## Genuinely missing — the actual work

1. **Scroller state selection.** Nothing currently decides *which* attention
   mechanism an asset should use. `hook_selector` scores a hook after the fact;
   it never chooses a strategy beforehand. This is the real gap.
2. **Payoff enforcement.** A strong hook with no payoff passes every gate today.
   "Curiosity gap without payoff" is the single most common way content feels
   like bait, and nothing rejects it.
3. **Hook decomposition for video.** `hook_text_overlay` is currently set from
   the same string as the spoken hook, so visual / on-screen / spoken are
   identical. Cheap to fix, disproportionate quality gain.
4. **Decision dimensions in the learning record.** `record_performance` stores
   hook/topic/format. It cannot answer "which mechanism worked" because the
   mechanism was never stored.

---

## The data constraint — the binding one

The proposal's learning section wants outcomes per:

```
platform × format × scroller_state × scroller_mechanism × coffee_frame × topic
```

With the proposed 12 mechanisms, 7 states, 7 frames and 4 formats, that is
**thousands of cells**. At 2 posts/day, and needing ~5 samples per cell before
a comparison means anything:

| Learn across | Cells | Posts to fill @5 each | Time @2/day |
|---|---|---|---|
| mechanism only | 12 | 60 | ~1 month |
| mechanism × frame | 84 | 420 | ~7 months |
| mechanism × frame × format | 336 | 1,680 | ~2.3 years |
| the full cross-tab | 2,000+ | 10,000+ | decades |

**Therefore: learn one dimension at a time, sequentially.** Mechanism first.
Only add a second dimension once the first has a stable answer. The engine must
refuse to report a comparison it lacks the samples for — the same rule already
applied to `viral_score` and `expected_follows`, which return `None` with a
stated basis rather than a confident-looking guess.

The registries can hold 12 mechanisms. The *learning* must start at 1 dimension.

---

## Phases

### Phase 0 — Measurement (BLOCKING, not part of this work)
Zero measured posts exist. Every phase below produces data that is only worth
collecting if insights land. **Do not start Phase 4+ until `[insights] Done —
N recorded` shows N > 0.** Phases 1–3 are safe to build regardless because they
improve content quality independent of learning.

### Phase 1 — Decision record *(small; highest leverage)*
Capture the dimensions on every asset. **No behaviour change.**
- `scroller_state`, `scroller_mechanism`, `hook_strategy`, `payoff_type`,
  `verified_fact_refs` added to asset metadata and to `record_performance`.
- Extend `decision_layer.attach_asset_metadata()`; do not write a new planner.
- Why first: it starts accumulating the data every later phase needs, and it
  is reversible. Building Phase 4 first means its first 3 months are unlearnable.

### Phase 2 — Payoff gate *(small; independent of data)*
- `payoff_strength(piece)` — does the viewer actually receive knowledge, a test,
  a comparison, a decision framework or a verified discovery?
- Reject strong-hook/no-payoff in `_apply_growth_director_gates`, alongside the
  existing north-star and 80/20 gates. One more gate in the existing chokepoint,
  not a new one.

### Phase 3 — Hook decomposition *(small; independent of data)*
- Visual hook, on-screen hook and spoken hook must be **distinct** for video.
- Schema validation rejects identical strings across the three.

### Phase 4 — Scroller registry + state selection *(medium; the actual layer)*
- `core/scroller_psychology.py`, structured like `coffee_psychology.py`
  (`id`, `name`, `attention_trigger`, `curiosity_mechanism`,
  `payoff_requirement`, `share_save_mechanism`, `best_formats`, `risk_level`,
  `prohibited_patterns`) with the same `validate_registry()` and fail-closed
  governance — no `"default"` id, ever.
- Selection driven by platform + funnel stage + objective + recent-mechanism
  fatigue. Rules first; data-driven later.
- Injected into the platform prompt builder, not appended to `generator.py`.

### Phase 5 — Mechanism learning *(only after ~100 measured posts)*
- Compare outcomes across `scroller_mechanism` alone, using the existing
  `reward.py`. No new scoring.
- Report `None` where samples are insufficient.

---

## Non-negotiables (carried from existing architecture)

- One reward function. The scroller layer supplies explanatory dimensions; it
  never scores success.
- One publish gate. New checks join `_apply_growth_director_gates`.
- No `"default"` frame or mechanism. Selection failure → no publish.
- Psychology is not a source of truth. Facts come from `claim_verifier`'s
  verified set only.
- No guaranteed-virality claims, anywhere in prompts or output.

## Explicitly rejected

- A second hook bank. `hook_selector` exists; extend it.
- A second publish gate, planner, or reward function.
- Learning the full cross-tab before the single dimension has an answer.
- Appending the whole spec to `generator.py` as one large prompt — the data flow
  must stay explicit and inspectable.

## Recommendation

Build **Phases 1–3 now** (small, data-independent, each improves quality on its
own). Hold **Phases 4–5** until measurement is confirmed working, because a
selection layer that cannot be evaluated is just a more elaborate guess.
