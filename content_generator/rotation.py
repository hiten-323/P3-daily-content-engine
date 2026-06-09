"""
Rotation banks and day-number helpers.
All mutable state lives here so every prompt module imports from one place.
"""
import os
import datetime

# ── Start date ────────────────────────────────────────────────────────────────
# Change this if the project restarts from day 0.
CONTENT_ENGINE_START_DATE = datetime.date(2026, 1, 1)

# ── Runtime config ────────────────────────────────────────────────────────────
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://p3online.in")

# ── Rotation banks ────────────────────────────────────────────────────────────

BLOG_TOPIC_CLUSTERS = [
    "instant coffee benefits India — antioxidants, clean energy, mental clarity science",
    "instant coffee recipe India — 2-minute preparation, flavour variations, pro tips",
    "best coffee for students India — exam focus, affordable, zero crash caffeine",
    "morning coffee routine India — productivity ritual, habit-stacking, lifestyle design",
    "pure coffee vs adulterated India — chicory exposed, zero additives explained",
    "coffee price comparison India — Rs18/cup vs Rs180 cafe, 10-year savings breakdown",
    "work from home coffee India — deep focus, Pomodoro pairing, WFH productivity guide",
    "coffee health myths India — caffeine facts debunked, what doctors actually say",
    "instant coffee brand comparison India — what ingredient labels never tell you",
    "coffee for gym fitness India — pre-workout, clean energy, no jitters guide",
    "founder story Purity Beans — bootstrapped FMCG India, zero VC, 10x growth",
    "single origin vs blended coffee India — quality, taste profile, ethical sourcing",
    "coffee gifting India — premium corporate gifts, occasion boxes, personalised sets",
    "sustainable coffee India — ethical sourcing, clean supply chain, carbon footprint",
    "caffeine and productivity science India — focus mechanisms, Indian professionals study",
    "cold brew at home India — step-by-step guide, Purity Beans method",
    "coffee culture India — from filter kaapi to specialty, the evolution story",
    "chicory in Indian coffee — the 80-year adulterant history nobody talks about",
]

HOOK_ARCHETYPES = [
    ("EXPOSE",         "Reveal what powerful brands actively hide — righteous anger drives shares"),
    ("IDENTITY CALL",  "Challenge who they believe they are — identity threat stops the scroll"),
    ("SHOCKING STAT",  "Open with a specific number that breaks their reality — precision beats vagueness"),
    ("CONTRARIAN",     "Fight the mainstream belief — controversy holds attention better than agreement"),
    ("TRANSFORMATION", "Before/after in one sentence — implies they can have the after too"),
    ("LOOP BAIT",      "End that loops to the beginning — algorithm rewards replays"),
    ("LIVE CHALLENGE", "Make them act RIGHT NOW — participation drives retention and algorithm boost"),
    ("RELATABLE FAIL", "Voice their silent daily failure — parasocial bond, mass relatability"),
    ("SOCIAL PROOF",   "Mass adoption framed as movement — nobody wants to be the last to know"),
    ("FEAR URGENCY",   "Something bad is happening right now — urgency overrides decision fatigue"),
    ("MYTH BUST",      "Call out a belief they hold as fact — cognitive dissonance halts the thumb"),
    ("INSIDER ACCESS", "You know something the industry hides — forbidden knowledge appeal"),
    ("CURIOSITY GAP",  "Start the answer but force them to watch to complete it — incomplete loops itch"),
    ("SOCIAL SHAME",   "Everyone else knows this but you — FOMO plus status anxiety in one punch"),
    ("PATTERN BREAK",  "Shatter the expected visually or verbally — novelty triggers the dopamine hit"),
]

SAVE_MECHANICS = [
    ("MYTH-BUSTING LIST",  "List of false beliefs they hold — save to share and correct others"),
    ("COMPARISON TABLE",   "Side-by-side data they will reference later — save as cheat sheet"),
    ("STEP-BY-STEP GUIDE", "Process they want to execute later — save equals bookmark for action"),
    ("CHECKLIST",          "Diagnostic tool they reuse — save for repeated reference"),
    ("NUMBERED FACTS",     "Dense value stack — save to reread when they have time"),
    ("EXPOSE SLIDES",      "Damning evidence broken into slides — save and share to expose wrongdoing"),
    ("RECIPE HOW-TO",      "Instruction they want to execute in 24 hrs — save equals purchase intent"),
    ("DATA STORY",         "Before/after numbers with narrative — save for motivation"),
    ("RANKING TIER LIST",  "Ranked options with criteria — save as decision-making reference"),
    ("INSIDER GLOSSARY",   "Terms the industry uses — save to sound smart in conversations"),
]

LINKEDIN_ANGLES = [
    ("FOUNDER CONFESSION",  "Raw honest failure/insight building premium FMCG in India without VC"),
    ("INDUSTRY EXPOSE",     "What the Rs4000Cr Indian instant coffee industry hides from buyers"),
    ("CONTRARIAN BUSINESS", "Why competing on price destroys FMCG brands — compete on purity instead"),
    ("PERSONAL EXPERIMENT", "I replaced morning chai with pure coffee for 60 days — here is the data"),
    ("CONSUMER PSYCHOLOGY", "Why Indians accept chicory in coffee but revolt over adulterated milk"),
    ("STARTUP LESSON",      "The hardest thing about building a food brand Indians actually trust"),
    ("MARKET INSIGHT",      "The Rs4000Cr instant coffee opportunity and who is actually winning it"),
    ("HEALTH SCIENCE",      "What pure caffeine does vs adulterated coffee — with peer-reviewed sources"),
    ("DISTRIBUTION TRUTH",  "Why the best product in India never wins without cracking distribution"),
    ("PRICING PSYCHOLOGY",  "Why Rs18/cup feels risky to Indians but Rs180 at a cafe feels normal"),
]

COMMERCIAL_EMOTIONS = [
    ("RELIEF",    "the exhale moment — finally getting real coffee after years of filler"),
    ("PRIDE",     "choosing quality when everyone around you settles for cheap garbage"),
    ("AMBITION",  "fuelling your grind at 5am when the city is still asleep"),
    ("NOSTALGIA", "the real coffee taste your grandmother made before brands added chicory"),
    ("REBELLION", "refusing to be fooled by fake ingredients disguised as premium packaging"),
    ("JOY",       "the small daily luxury that costs less than a tapri chai"),
    ("FOCUS",     "clean energy that builds without the crash — real caffeine, real work"),
]

PRODUCTS = [
    "Ultra Blend",
    "Bold",
    "Purista Gourmet",
    "Purica Gourmet",
    "Prima Premium",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_day_number() -> int:
    return (datetime.date.today() - CONTENT_ENGINE_START_DATE).days


def get_todays_blog_topic(day: int) -> str:
    return BLOG_TOPIC_CLUSTERS[day % len(BLOG_TOPIC_CLUSTERS)]


def pick(bank: list, day: int, offset: int = 0):
    """Return the bank item for this day, with optional offset for diversity."""
    return bank[(day + offset) % len(bank)]
