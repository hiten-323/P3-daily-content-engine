"""LinkedIn post prompt — full publish-ready asset."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL

HASHTAG_15 = (
    "#PurityBeans #D2CBrand #FoodBusiness #IndianStartup #PureCoffee "
    "#CPGIndia #FMCGIndia #BrandBuilding #Entrepreneurship #InstantCoffee "
    "#CoffeeIndia #IndianBrands #SupportIndianBrands #PremiumCoffee #CoffeeCommunity"
)


def build(angle: tuple, avoid: str) -> str:
    return f"""{brand_block()}

Generate ONE complete publish-ready LinkedIn post for Purity Beans. Return a single JSON object.

{avoid}

ANGLE: [{angle[0]}] — {angle[1]}

ALLOWED CONTENT: founder stories, startup lessons, coffee industry insights, consumer behavior, brand-building lessons.
PROHIBITED: fake stories, invented revenue, invented customer counts, invented events, fabricated statistics.
If any information is unknown: state assumptions clearly and explicitly.

ABSOLUTE RULES:
- 'Purity Beans' MUST appear in the post
- '{WEBSITE_URL}' MUST appear in cta
- Body MUST be 300+ words
- hashtags are MANDATORY

{{
  "angle": "{angle[0]}",
  "hook": "Max 12 words. No emoji. Controversial, confessional, or contrarian. Makes a professional stop scrolling.",
  "body": "3-5 short paragraphs. First-person. One specific real detail — a place, a conversation, a decision. Indian professional voice. No corporate speak. No invented numbers. If sharing data, cite it as observation not fact. 300+ words total.",
  "brand_bridge": "One sentence linking the insight to Purity Beans — specific, never 'that is why we built it'",
  "closing_question": "Question professionals actually want to debate — polarising or personally relevant",
  "cta": "Visit {WEBSITE_URL} with a specific reason to click, OR a comment prompt with real stakes",
  "hashtags": "{HASHTAG_15}",
  "image_prompt": "Purity Beans jar on dark wood desk, laptop soft-blurred behind, single warm lamp, professional but human, 1200x628. No generic coffee imagery."
}}"""
