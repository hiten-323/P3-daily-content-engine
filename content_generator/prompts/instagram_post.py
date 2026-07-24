"""Instagram single-image post prompt — full publish-ready asset."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import COMMERCIAL_EMOTIONS, WEBSITE_URL

HASHTAG_25 = (
    "#Coffee #CoffeeLover #InstantCoffee #MorningCoffee #CoffeeTime "
    "#PremiumCoffee #FreezeDriedCoffee #GourmetCoffee #PureCoffee #CoffeeCommunity "
    "#IndianCoffee #CoffeeIndia #MadeInIndia #IndianBrands #SupportIndianBrands "
    "#CoffeeAddict #CoffeeDaily #CoffeeGram #CoffeeCulture #CoffeeLife "
    "#PurityBeans #PurityBeansCoffee #PurityBeansExperience #BrewPure #PureCoffeeExperience"
)


def build(day: int, avoid: str) -> str:
    emotion = COMMERCIAL_EMOTIONS[day % len(COMMERCIAL_EMOTIONS)]

    return f"""{brand_block()}

Generate ONE complete publish-ready Instagram feed post (single image) for Purity Beans. Return a single JSON object.

{avoid}

EMOTION TO EVOKE: {emotion[0]} — {emotion[1]}

ABSOLUTE RULES:
- NEVER invent statistics or percentages
- NEVER make medical claims
- Caption MUST be 150-250 words
- 'Purity Beans' MUST appear in caption
- '{WEBSITE_URL}' MUST appear in caption and CTA
- comment_trigger, save_trigger, share_trigger, hashtags are MANDATORY

{{
  "caption": "HOOK LINE that stops the scroll (max 12 words, no emoji).\\n\\nShort story or insight coffee lovers relate to. Introduce Purity Beans naturally. Explain why real coffee drinkers should care. Mention: No preservatives. No artificial aroma. 100% coffee. Freeze-dried and agglomerated variants available.\\n\\nShop now: {WEBSITE_URL}\\n\\nThis caption must be 150-250 words. Paste-ready. Emotional storytelling with brand facts woven in naturally.",
  "cta": "Direct action with {WEBSITE_URL}",
  "comment_trigger": "Comment COFFEE if you are a real coffee lover who refuses to drink chicory.",
  "save_trigger": "Save this post before your next grocery run.",
  "share_trigger": "Share with someone who starts every morning with coffee.",
  "image_prompt": "Detailed AI image prompt — Purity Beans jar, dark marble surface, warm amber studio light, premium editorial FMCG photography, 1080x1080. No text in image. No generic jars.",
  "image_alt": "Purity Beans premium instant coffee jar — no preservatives, no artificial aroma, 100% coffee",
  "post_type": "one of: product-truth / founder-moment / customer-story / cultural-hook / myth-busting",
  "hook_line": "The first line of the caption repeated here — must stop scroll before the More button cuts it",
  "seo_keywords": ["premium instant coffee", "gourmet instant coffee", "freeze dried coffee", "coffee without preservatives", "pure instant coffee india", "best instant coffee brand india"],
  "hashtags": "{HASHTAG_25}"
}}"""


# Instagram-native V2 rules (shared growth/creative contract)
from content_generator.prompts.instagram_native import INSTAGRAM_NATIVE_RULES
