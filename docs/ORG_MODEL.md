# Org Model — the marketing "team" mapped to real code

Your org chart is a good mental model. The key insight: **~80% of it already
exists** as modules in this engine. This doc names each role and points to the
code that IS that role — so the hierarchy is a *lens*, not a rebuild. Building
each role as a separate autonomous "agent" would be over-engineering at current
scale (ADR-001: architecture frozen; evidence over elegance).

## The hierarchy → the code

```
Founder                     you (sets founder_policies.yaml)
  │
CMO  (strategy/KPI/policy)   core/founder_policy.py + core/growth_director.py
  │                          — target KPI, stage ratios, message angle, funnel
  │                            objective, daily strategy brief
  │
  ├─ Brand Director          core/brand_guard.py + core/editorial_engine.py
  │                          — brand facts, governance, editorial score gate
  │
  ├─ Content Director        strategy/content_mix_optimizer.py +
  │                          intelligence/decision_layer.py + rotation.py
  │                          — what to make today, experiment, playbook, DNA
  │
  ├─ SMM (orchestration)     scheduler/daily.py + scheduler/slots.py +
  │   │                       publisher/dispatcher.py
  │   │                       — timing (3 slots), platform routing, invokes
  │   │                         creative + audio, holds/publishes per slot
  │   │
  │   ├─ Instagram Engine    publisher/instagram.py + prompts/reels.py,
  │   │                       carousel.py + analytics/hashtag_bank.py +
  │   │                       analytics/social_seo.py + publisher/product_tags.py
  │   ├─ Facebook Engine      publisher/facebook.py (mirrors IG)
  │   ├─ LinkedIn Engine      publisher/linkedin.py + prompts/linkedin.py
  │   ├─ YouTube Engine       publisher/youtube.py + prompts/yt_short.py
  │   ├─ X/Twitter Engine     — NOT built (no token / channel)
  │   └─ Pinterest Engine     — NOT built (no channel)
  │
  ├─ SEO Director            analytics/social_seo.py (search-question captions)
  │                          + analytics/hashtag_bank.py + publisher/shopify_blog.py
  │
  ├─ Email Marketing Dir.    nurture/email_sequences.py  (built, DORMANT — no SMTP)
  ├─ Community Director       nurture/*  + comment mechanics (replies are MANUAL)
  ├─ Analytics Director       analytics/insights_fetcher.py +
  │                           analytics/revenue_attribution.py +
  │                           analytics/founder_brief.py + analytics/metrics_store.py
  │
  └─ Creative Studio
        ├─ Copy Engine        prompts/* + providers/llm_router.py
        ├─ Image Engine        creative/real_jar_composer.py +
        │                      creative/cinematic_frame.py + creative/gemini_scene.py
        ├─ Video Engine        creative/reel_video.py
        ├─ Thumbnail Engine    creative/cinematic_frame.py (reel thumbnails)
        └─ Audio Intelligence  creative/audio_director.py

Learning / Memory (cross-cutting):
  core/learning_engine.py (viral memory, top/bottom 20%, audio/hook/topic dims)
  + intelligence/decision_layer.py + output/learning/*.json (persisted each run)
```

## Roles deliberately NOT built (premature — activate when the business has the function)

| Role | Why not yet |
|---|---|
| Influencer Director | No influencer budget/relationships to manage yet |
| PR Director | No press function/media list yet |
| Performance Marketing Director | No paid-ad spend — this engine is organic-only by design |
| X/Twitter, Pinterest Engines | Channels not set up; adding them is trivial once tokens exist |

Building these now = empty shells consuming maintenance for zero output. Each
becomes a real module the day the business actually does that thing — added via
a new ADR, not speculatively.

## My edits to your model

1. **The engine is a PIPELINE, not a bureaucracy.** Your boxes are real, but they
   run as one daily flow (CMO strategy → Content Director plan → SMM orchestrates
   → Platform/Creative engines produce → Publisher ships → Analytics/Learning/
   Memory feed back). Keeping it a pipeline (not 15 chattering agents) is what
   makes it cheap, debuggable, and reliable.

2. **"SMM owns the whole publishing workflow"** — agreed, and it already does:
   `scheduler/daily.py` + `slots.py` + `dispatcher.py` decide timing, route to
   platforms, invoke creative + audio, and hold/publish per slot.

3. **Audio as a shared capability the SMM invokes** — exactly how it's wired now:
   `audio_director.get_audio_plan()` is called by the reel Video Engine (embed)
   and attached per-asset for the manual path. It's not owned by one platform.

4. **Your simplified final hierarchy is the right one** and closely matches the
   real data flow: Policy → Strategy → Orchestration → Platform/Creative Engines
   → Publisher → Analytics → Learning → Memory. That's the system today.

## Bottom line

You don't need to build an org — you need to *recognize* the one that exists and
only add a role when the business grows a real function for it. The org chart is
now documentation (this file), not a construction plan.
