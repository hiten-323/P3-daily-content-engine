"""
Growth Director — the strategic brain that turns a Content Engine into a
Growth Engine.

Every morning, before any content is generated, it answers:
  "What is the fastest way to gain followers tomorrow?"

It does this with data the engine already has:
  - follower snapshots (from insights_fetcher) -> growth stage
  - growth stage -> viral/selling content ratio (Million Follower Mode)
  - day number -> today's single funnel objective per reel (never mixed)
  - viral memory + fatigue guard (injected separately by the generator)

Output: a strategy brief injected into every generation prompt.
"""
from __future__ import annotations
import json
import logging
import os

logger = logging.getLogger(__name__)

_LEARNING_DIR = os.getenv("LEARNING_DIR", os.path.join("output", "learning"))
_SNAP_PATH    = os.path.join(_LEARNING_DIR, "follower_snapshots.json")


# ── Million Follower Mode: stage-dependent content ratios ─────────────────────

GROWTH_STAGES = [
    #  min_followers, name,        viral%, selling%, focus
    (0,       "IGNITION (0-1K)",      95,  5,
     "Nobody knows you exist. 95% of content must be pure viral value — "
     "coffee culture, curiosity, education. Selling to strangers wastes reach. "
     "Every reel's only job: make a stranger tap Follow."),
    (1_000,   "TRACTION (1K-10K)",    85, 15,
     "You have proof of life. Keep viral dominant, introduce light brand "
     "presence — the jar can appear naturally, soft CTAs only."),
    (10_000,  "MOMENTUM (10K-100K)",  70, 30,
     "Audience trusts you. Balance viral discovery with conversion reels "
     "that route traffic to p3online.in."),
    (100_000, "SCALE (100K+)",        50, 50,
     "Authority established. Half discovery, half revenue. Launch-style "
     "content and direct product storytelling now convert."),
]


# ── Follower Funnel: one objective per reel, never mixed ──────────────────────

FUNNEL_OBJECTIVES = [
    ("DISCOVERY",  "Reach strangers. Broad-appeal topic, zero brand, maximum shareability. "
                   "Success metric: shares + reach."),
    ("FOLLOW",     "Convert viewers to followers. End with a follow-worthy promise "
                   "('Follow — tomorrow I show you X'). Success metric: follows per view."),
    ("AUTHORITY",  "Build trust. Teach something only an expert would know. "
                   "Success metric: saves."),
    ("CONVERSION", "Route to website. Product visible, clear buy CTA, https://p3online.in. "
                   "Success metric: link clicks. (Brand track only.)"),
    ("COMMUNITY",  "Spark conversation. Opinion bait, this-or-that, identity question, "
                   "or intent-comment mechanic (withhold price/variant info — "
                   "'Comment PRICE / BOLD / GIFT' — each comment is a lead). "
                   "Success metric: comments."),
]


def get_follower_count() -> int:
    """Latest follower count from snapshots; 0 if none recorded yet."""
    if not os.path.exists(_SNAP_PATH):
        return 0
    try:
        with open(_SNAP_PATH, "r", encoding="utf-8") as f:
            snaps = json.load(f)
        return int(snaps[-1]["count"]) if snaps else 0
    except Exception:
        return 0


def get_growth_stage(followers: int = None) -> dict:
    """Return the current growth stage config for Million Follower Mode."""
    if followers is None:
        followers = get_follower_count()
    stage = GROWTH_STAGES[0]
    for s in GROWTH_STAGES:
        if followers >= s[0]:
            stage = s
    return {
        "followers": followers,
        "name":      stage[1],
        "viral_pct": stage[2],
        "sell_pct":  stage[3],
        "focus":     stage[4],
    }


def get_todays_objectives(day: int) -> dict:
    """
    Assign ONE funnel objective per asset for today. Never mixed.

    Growth reel cycles the audience-building objectives
    (discovery/follow/authority/community). The brand reel cycles all five,
    but CONVERSION appears more often as the account grows.
    """
    audience_objs = [FUNNEL_OBJECTIVES[i] for i in (0, 1, 2, 4)]  # no conversion
    growth_obj = audience_objs[day % len(audience_objs)]

    stage = get_growth_stage()
    # Brand reel: at early stages conversion appears 1 day in 5; later 1 in 2
    conv_every = 5 if stage["viral_pct"] >= 85 else (3 if stage["viral_pct"] >= 70 else 2)
    if day % conv_every == 0:
        brand_obj = FUNNEL_OBJECTIVES[3]  # CONVERSION
    else:
        brand_obj = audience_objs[(day // conv_every) % len(audience_objs)]

    return {"growth_reel": growth_obj, "brand_reel": brand_obj}


def get_strategy_brief(day: int) -> str:
    """
    The daily strategy brief — injected into every generation prompt.
    This is what makes the engine ask 'what grows followers fastest tomorrow'
    instead of 'what content do I generate today'.
    """
    stage = get_growth_stage()
    objs  = get_todays_objectives(day)

    # Founder policy bias (target KPI, voice, priority segments) — the founder
    # steers the engine by editing founder_policies.yaml, never the prompts.
    policy_line = ""
    try:
        from content_generator.core.founder_policy import policy
        policy_line = policy().strategy_bias() + "\n\n"
    except Exception:
        pass

    return f"""{policy_line}GROWTH DIRECTOR — TODAY'S STRATEGY (this overrides generic instincts):

CURRENT STAGE: {stage['name']} — {stage['followers']} followers
CONTENT RATIO: {stage['viral_pct']}% viral value / {stage['sell_pct']}% selling
STAGE FOCUS: {stage['focus']}

TODAY'S FUNNEL OBJECTIVES (one per asset — NEVER mix objectives in one reel):
- growth_reel -> [{objs['growth_reel'][0]}] {objs['growth_reel'][1]}
- brand reel  -> [{objs['brand_reel'][0]}] {objs['brand_reel'][1]}

WATCH-TIME STRUCTURE (Instagram ranks by watch time, not likes):
0-2s hook | 2-5s retention lock | 5-10s curiosity build | 10-20s reward | final 5s CTA.
Every frame/beat must earn the next 3 seconds. If a beat only exists to fill
time, cut it — shorter with full retention beats longer with drop-off.

THE ONLY QUESTION THAT MATTERS TODAY:
What is the fastest way to gain followers tomorrow? Generate for that."""
