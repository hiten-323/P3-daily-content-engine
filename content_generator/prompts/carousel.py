"""Instagram Carousel prompt — full publish-ready asset."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL, get_todays_viral_idea

HASHTAG_25 = (
    "#Coffee #CoffeeLover #InstantCoffee #MorningCoffee #CoffeeTime "
    "#PremiumCoffee #FreezeDriedCoffee #GourmetCoffee #PureCoffee #CoffeeCommunity "
    "#IndianCoffee #CoffeeIndia #MadeInIndia #IndianBrands #SupportIndianBrands "
    "#CoffeeAddict #CoffeeDaily #CoffeeGram #CoffeeCulture #CoffeeLife "
    "#PurityBeans #PurityBeansCoffee #PurityBeansExperience #BrewPure #PureCoffeeExperience"
)


def build(mech: tuple, avoid: str, day: int = 0) -> str:
    viral_idea = get_todays_viral_idea(day)

    return f"""{brand_block()}

Generate ONE complete publish-ready Instagram Carousel for Purity Beans. Return a single JSON object.

{avoid}

SAVE MECHANIC: [{mech[0]}] — {mech[1]}
TODAY'S VIRAL CONTENT ANGLE: {viral_idea}
Every slide must make the viewer think: I need to save this for later.
PURPOSE: Maximize saves and shares through comparison, myth-busting, coffee tips, education, or buying guide.

ABSOLUTE RULES:
- NEVER invent statistics or percentages
- NEVER make medical claims
- Minimum 6 slides, maximum 8 slides
- Final slide MUST include CTA + {WEBSITE_URL} + mention of Purity Beans
- caption MUST be 200-300 words
- comment_trigger, save_trigger, share_trigger, hashtags are MANDATORY

{{
  "id": "carousel_1",
  "save_mechanic": "{mech[0]}",
  "title": "7 WORDS MAX — curiosity + utility that forces the save",
  "slides": [
    {{"slide": 1, "heading": "COVER HOOK — 6 WORDS MAX", "body": "Pattern interrupt. Promise that forces the swipe. What they will learn.", "visual": "Dark marble, Purity Beans jar hero, single gold beam"}},
    {{"slide": 2, "heading": "The Problem", "body": "What most people do not know about their daily coffee. Specific, relatable, not statistical.", "visual": "Dark bg, white text, one visual accent"}},
    {{"slide": 3, "heading": "Myth Busted", "body": "The assumption everyone holds that is actually wrong. Contrarian and surprising.", "visual": "Ingredient or product detail close-up"}},
    {{"slide": 4, "heading": "The Revelation", "body": "The I-did-not-know-this moment. Specific truth about coffee purity vs adulterants.", "visual": "Before/after or label close-up"}},
    {{"slide": 5, "heading": "Why It Matters", "body": "Specific Indian scenario — what this means for a real coffee lover in India.", "visual": "Indian person + coffee, natural light"}},
    {{"slide": 6, "heading": "Purity Beans Difference", "body": "No preservatives. No artificial aroma. 100% coffee. Zero chicory. Available freeze-dried and agglomerated. Shop {WEBSITE_URL}", "visual": "Product hero — full Purity Beans jar, cinematic, gold accent"}},
    {{"slide": 7, "heading": "Share This", "body": "Tag the friend who deserves real coffee. Visit {WEBSITE_URL}", "visual": "Brand CTA — dark bg, Purity Beans logo, minimal gold"}}
  ],
  "caption": "HOOK LINE that stops the scroll.\\n\\nWhat you will learn in this carousel (preview the value). Tell the story of why this matters to a real coffee lover. Mention Purity Beans naturally. Include: No preservatives. No artificial aroma. 100% coffee. Freeze-dried and agglomerated variants.\\n\\nThis is a 200-300 word paste-ready caption with emotional storytelling and brand facts.\\n\\nShop now: {WEBSITE_URL}",
  "cta": "Direct action with {WEBSITE_URL}",
  "comment_trigger": "Comment SAVE if you are switching to real coffee this week.",
  "save_trigger": "Save this carousel — it will change how you buy coffee forever.",
  "share_trigger": "Share with someone who deserves to know what is really in their coffee.",
  "seo_keywords": ["premium instant coffee", "gourmet instant coffee", "freeze dried coffee", "agglomerated coffee", "coffee without preservatives", "pure instant coffee india", "best instant coffee brand india"],
  "hashtags": "{HASHTAG_25}"
}}"""
