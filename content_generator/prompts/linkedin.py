"""LinkedIn post prompt."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL


def build(angle: tuple, avoid: str) -> str:
    from config.brand_config import HASHTAG_SETS
    hs = HASHTAG_SETS["linkedin"]

    return f"""{brand_block()}

Generate ONE LinkedIn post for Purity Beans. Return a single JSON object.

{avoid}

ANGLE: [{angle[0]}] — {angle[1]}
Write a [{angle[0]}] post. Coffee is the proof, not the subject.
HASHTAGS: {hs}

{{
  "angle": "{angle[0]}",
  "hook": "Max 12 words. No emoji. Controversial, confessional, or contrarian. Makes a professional stop scrolling.",
  "body": "3-5 short paragraphs. First-person. One real number, one specific place, one lived moment. Numbered insights if sharing data. Indian professional voice. No corporate speak.",
  "brand_bridge": "1 sentence linking the insight to Purity Beans — not that is why we built it",
  "closing_question": "Question professionals actually want to debate or answer — polarising or personally relevant",
  "cta": "{WEBSITE_URL} with a specific reason, OR a comment prompt with stakes",
  "hashtags": "{hs}",
  "image_prompt": "Purity Beans jar on dark wood desk, laptop soft-blurred behind, single warm lamp, professional but human, 1200x628"
}}"""
