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
    "Purista",
    "Purica",
]

# ── 30 Viral content ideas rotating bank ─────────────────────────────────────

VIRAL_CONTENT_IDEAS = [
    "What is actually inside your instant coffee jar? (Ingredient label truth)",
    "I switched to pure coffee for 30 days. Here is what changed.",
    "Why most Indians are unknowingly drinking chicory every morning",
    "The Rs 18 vs Rs 180 coffee experiment — same caffeine, same quality?",
    "Real coffee vs adulterated coffee: a side-by-side taste test story",
    "Why freeze-dried coffee is different from regular instant coffee",
    "Agglomerated vs freeze-dried: which one should you buy?",
    "The ingredient your coffee brand never mentions on the label",
    "How to read a coffee label like an expert in 60 seconds",
    "Why premium instant coffee is not an oxymoron",
    "The Indian coffee adulterant problem that nobody is talking about",
    "3 signs your coffee has fillers (and how to check)",
    "What happens when you remove chicory from your morning coffee",
    "The real reason cafe coffee tastes different from home coffee",
    "How Purity Beans is built different: no preservatives, no artificial aroma",
    "Coffee gifting guide for people who actually care about quality",
    "Morning routine with pure coffee: a real Indian working professional story",
    "Why the best coffee in India costs Rs 18, not Rs 180",
    "Cold brew with instant coffee: does it actually work?",
    "The 80-year history of chicory in Indian coffee (and why it is still here)",
    "Corporate gifting: why premium coffee beats generic gifts every time",
    "What freeze-dried means and why it matters for your morning cup",
    "The coffee brand that prints what it does NOT add on the label",
    "Student life + real coffee: why Purity Beans makes sense at Rs 18",
    "Hotel and hospitality buyers: why gourmet instant coffee is the upgrade guests notice",
    "The difference between coffee you drink and coffee you experience",
    "Why Indian consumers are finally reading ingredient labels on coffee",
    "Distributor opportunity: the only pure instant coffee brand in your city",
    "How to make barista-quality coffee at home without any equipment",
    "The Purity Beans blind taste test: what real coffee lovers say",
]

# ── Scroll-stopping hooks bank ────────────────────────────────────────────────

VIRAL_HOOKS = [
    "You have been drinking chicory your entire life.",
    "What is actually inside your coffee jar?",
    "Real coffee lovers will understand this.",
    "Expensive cafe coffee is not the solution.",
    "That first sip that just does not taste right.",
    "Most instant coffee is not coffee at all.",
    "Your coffee brand is lying to you.",
    "I stopped buying branded coffee. Here is why.",
    "Rs 18 per cup. No chicory. No preservatives. No compromise.",
    "The ingredient on every label that nobody reads.",
    "If you care about what you drink, read this.",
    "Coffee without the filler finally exists in India.",
    "Everyone in your office is drinking adulterated coffee.",
    "The real reason your coffee does not taste like coffee.",
    "Indian brand. Nothing hidden. Everything on the label.",
    # Reverse-qualifier hooks — exclusion triggers curiosity + pre-qualifies
    "If you already drink single-origin coffee, skip this reel.",
    "This is not for people who enjoy chicory.",
    "Don't watch this if you're happy with your instant coffee.",
    "Real coffee is not for everyone. Scroll if that's you.",
    "If you've never read a coffee label, this will hurt.",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_day_number() -> int:
    return (datetime.date.today() - CONTENT_ENGINE_START_DATE).days


def get_todays_blog_topic(day: int) -> str:
    return BLOG_TOPIC_CLUSTERS[day % len(BLOG_TOPIC_CLUSTERS)]

def get_todays_viral_idea(day: int) -> str:
    return VIRAL_CONTENT_IDEAS[day % len(VIRAL_CONTENT_IDEAS)]

def get_todays_hook(day: int) -> str:
    return VIRAL_HOOKS[day % len(VIRAL_HOOKS)]


def pick(bank: list, day: int, offset: int = 0):
    """Return the bank item for this day, with optional offset for diversity."""
    return bank[(day + offset) % len(bank)]
