"""Blog post prompt."""
from content_generator.prompts.brand import brand_block
from content_generator.rotation import WEBSITE_URL


def build(topic: str) -> str:
    return f"""{brand_block()}

Generate ONE blog post for Purity Beans. Return a single JSON object.

TOPIC: {topic}
AUDIENCE: Indians searching Google for coffee information.

{{
  "title": "50-60 chars — include instant coffee India or pure coffee. Must earn the click over 9 competitors.",
  "slug": "lowercase-hyphens-max-6-words",
  "meta_description": "150-160 chars — lead with the benefit or surprising fact. Include Purity Beans and India.",
  "focus_keyword": "Primary keyword used 3-5x naturally in body",
  "intro": "2-3 sentences — fact, scenario, or question that makes the reader feel understood. Indian voice. Never say In today's world.",
  "body_html": "Full HTML. 600-800 words. 5-7 h2 sections, p tags, ul/li lists. Arc: hook scenario → chicory problem history India → caffeine science → pure vs adulterated comparison → Purity Beans solution → brew tips → CTA. Two natural links to {WEBSITE_URL}. Indian voice throughout.",
  "tags": ["instant coffee", "pure coffee", "coffee benefits", "chicory free", "purity beans", "india coffee"],
  "image_alt": "Product + keyword + India context — under 125 chars"
}}"""
