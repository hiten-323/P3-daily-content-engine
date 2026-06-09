"""Static single-image Instagram feed post prompt."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import COMMERCIAL_EMOTIONS, WEBSITE_URL


def build(day: int, avoid: str) -> str:
    from config.brand_config import HASHTAG_SETS
    hs      = HASHTAG_SETS.get("carousel", "")
    emotion = COMMERCIAL_EMOTIONS[day % len(COMMERCIAL_EMOTIONS)]

    return f"""{brand_block()}

Generate ONE static Instagram feed post (single image) for Purity Beans. Return a single JSON object.

{avoid}

EMOTION TO EVOKE: {emotion[0]} — {emotion[1]}
HASHTAGS (8-12 max): {hs}

This is a single image post — not a reel, not a carousel.
The caption must stand alone and drive engagement without video or swipes.

{{
  "caption": "Paste-ready. Line 1: scroll-stopping statement (max 12 words, no emoji). Line 2-3: the insight or story (Indian voice, specific detail). Line 4: CTA — comment, share, or {WEBSITE_URL}. Line 5: hashtags. Total under 120 words.",
  "image_prompt": "Detailed AI image generation prompt — subject, lighting, composition, colour grade, mood. Usable in Midjourney or Firefly. 1080x1080 square. No text in image.",
  "image_alt": "Instagram alt text for accessibility and SEO — under 100 chars",
  "post_type": "one of: product-truth / founder-moment / customer-story / cultural-hook",
  "hook_line": "The first line of the caption repeated here — must stop the More button from cutting off the key message"
}}"""
