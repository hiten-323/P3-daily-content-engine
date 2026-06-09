"""7-slide Instagram Carousel prompt."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL


def build(mech: tuple, avoid: str) -> str:
    from config.brand_config import HASHTAG_SETS
    hs = HASHTAG_SETS["carousel"]

    return f"""{brand_block()}

Generate ONE 7-slide Instagram Carousel for Purity Beans. Return a single JSON object.

{avoid}

SAVE MECHANIC: [{mech[0]}] — {mech[1]}
Every slide must make the viewer think: I need to save this for later.
HASHTAGS (8-12 max): {hs}

{{
  "id": "carousel_1",
  "save_mechanic": "{mech[0]}",
  "title": "7 WORDS MAX — curiosity + utility combined",
  "slides": [
    {{"slide": 1, "heading": "COVER HOOK — 6 WORDS MAX", "body": "Stat or promise that forces the swipe. Max 12 words.", "visual": "Dark marble, product hero, single gold beam"}},
    {{"slide": 2, "heading": "Point 1", "body": "One precise Indian market fact. Max 20 words.", "visual": "Dark bg, white text, one visual accent"}},
    {{"slide": 3, "heading": "Point 2", "body": "More specific than slide 2. Makes them nod. Max 20 words.", "visual": "Ingredient or product detail"}},
    {{"slide": 4, "heading": "THE REVELATION", "body": "The I-did-not-know-this moment. Industry data or hidden ingredient truth. Max 25 words.", "visual": "Before/after or label close-up"}},
    {{"slide": 5, "heading": "Make It Personal", "body": "Specific Indian scenario — student 1am / office 2pm / parent pre-commute. Max 25 words.", "visual": "Indian person + coffee, natural light"}},
    {{"slide": 6, "heading": "The Solution", "body": "Purity Beans. Zero chicory. Rs18/cup. Earned, not pitched. Max 20 words.", "visual": "Product hero — full jar, cinematic, gold accent"}},
    {{"slide": 7, "heading": "Share This", "body": "Tag the friend who [specific relatable behaviour]. {WEBSITE_URL}", "visual": "Brand CTA — dark bg, logo, minimal gold"}}
  ],
  "caption": "Paste-ready. Hook (12 words) + what they'll learn + save/tag CTA + {WEBSITE_URL} + hashtags. Under 150 words."
}}"""
