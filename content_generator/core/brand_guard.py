"""
Brand guard definitions — single source of truth for Purity Beans brand identity,
master system prompts, language policies, and visual constraints.
"""
from dataclasses import dataclass

@dataclass
class BrandProfile:
    brand_name: str
    company_name: str
    website: str
    language: str
    minimum_editorial_score: float
    jar_reference_path: str

EDITORIAL_THRESHOLD = 8.0

BRAND: BrandProfile = BrandProfile(
    brand_name="Purity Beans",
    company_name="Pure Pantry Provisions",
    website="https://p3online.in",
    language="English",
    minimum_editorial_score=EDITORIAL_THRESHOLD,
    jar_reference_path="brand_assets/puritybeans_front.png"
)

PRODUCTS = ["ultra_blend", "bold", "purista", "purica"]
SIZES    = ["50g", "100g"]
ANGLES   = ["front", "side", "lifestyle", "variant"]

REFERENCE_IMAGES = [
    f"brand_assets/puritybeans_{product}_{size}_{angle}.png"
    for product in PRODUCTS
    for size    in SIZES
    for angle   in ANGLES
]

# Keywords that map content text → product slug
PRODUCT_KEYWORDS: dict[str, list[str]] = {
    "ultra_blend": ["ultra blend", "ultrablend", "ultra-blend"],
    "bold":        ["bold"],
    "purista":     ["purista"],
    "purica":      ["purica"],
}

def get_product_references(text: str) -> list[str]:
    """
    Return only the jar reference images for the product mentioned in text.
    Falls back to all available references if no product is detected.
    """
    import os
    text_lower = text.lower()
    for product, keywords in PRODUCT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            refs = [
                f"brand_assets/puritybeans_{product}_{size}_{angle}.png"
                for size  in SIZES
                for angle in ANGLES
            ]
            return [p for p in refs if os.path.exists(p)]
    # No specific product detected — use all available
    return [p for p in REFERENCE_IMAGES if os.path.exists(p)]

BRAND_ASSET_DIRS = {
    "jars":           "brand_assets/jars/",
    "logos":          "brand_assets/logos/",
    "lifestyle":      "brand_assets/lifestyle/",
    "certifications": "brand_assets/certifications/",
    "packaging":      "brand_assets/packaging/",
}

# Key assets injected into every image prompt when available
BRAND_OVERLAY_ASSETS = {
    "logo":  "brand_assets/logos/puritybeans_logo.png",
    "fssai": "brand_assets/certifications/fssai_badge.png",
}

BRAND_FACTS = {
    "brand_name": "Purity Beans",
    "website": "https://p3online.in",
    "positioning": "India's Cleanest Instant Coffee",
    "core_claims": [
        "100% Coffee",
        "Zero Chicory",
        "No Fillers",
        "No Hidden Ingredients"
    ]
}

PROHIBITED_VISUALS = [
    "generic coffee jar",
    "fictional coffee brand",
    "cartoon coffee",
    "anime style",
    "illustration",
    "plastic render",
    "fake label",
    "different cap",
    "different jar shape"
]

MIN_REQUIRED_ASSETS = 2

REQUIRED_DAILY_ASSETS = [
    "reel_1",
    "reel_2",
    "carousel",
    "instagram_post",
    "linkedin_post",
    "blog_post",
    "yt_short"
]

PRODUCT_CATALOG = {
    "bold": {
        "name":     "Purity Beans Bold",
        "tagline":  "100% Agglomerated Coffee — Full Strength",
        "skus":     ["bold_50g", "bold_100g"],
        "best_for": ["strong coffee drinkers", "filter coffee lovers", "home brewers"],
    },
    "ultra_blend": {
        "name":     "Purity Beans Ultra Blend",
        "tagline":  "Agglomerated Coffee — Balanced Everyday Brew",
        "skus":     ["ultra_blend_50g", "ultra_blend_100g"],
        "best_for": ["corporate offices", "everyday drinkers", "first-time buyers"],
    },
    "purica": {
        "name":     "Purity Beans Purica",
        "tagline":  "Gourmet Instant Coffee Granules",
        "skus":     ["purica_50g", "purica_100g"],
        "best_for": ["hotels", "hospitality", "premium gifting", "cafes"],
    },
    "purista": {
        "name":     "Purity Beans Purista",
        "tagline":  "Premium Instant Coffee",
        "skus":     ["purista_50g", "purista_100g"],
        "best_for": ["premium buyers", "corporate gifting", "connoisseurs"],
    },
}

SEGMENT_TO_PRODUCT = {
    "corporate offices":   "ultra_blend",
    "hotels":              "purica",
    "hospitality":         "purica",
    "strong coffee":       "bold",
    "premium buyers":      "purista",
    "corporate gifting":   "purista",
    "everyday drinkers":   "ultra_blend",
    "first-time buyers":   "ultra_blend",
}

CONTENT_PILLARS = [
    "sales",
    "education",
    "myth_busting",
    "founder_story",
    "product_demo",
    "customer_story",
    "coffee_truth",
    "retailer_outreach",
    "distributor_outreach"
]

FORBIDDEN_TERMS = [
    "weight loss",
    "fat burning",
    "medical benefit",
    "cures",
    "sleep cure",
    "disease prevention"
]

REQUIRED_BRAND_MESSAGES = [
    "100% Coffee",
    "Zero Chicory",
    "Pure Ingredients"
]

LANGUAGE_POLICY = """
OUTPUT LANGUAGE: ENGLISH ONLY

Do not generate:
Hindi
Punjabi
Hinglish
Urdu

All captions
all hooks
all overlays
all subtitles
must be English.
"""

SYSTEM_BRAND_RULES = """
MANDATORY:
Use the exact Purity Beans product jar from
the supplied reference image.

Do not redesign.
Do not alter label.
Do not invent branding.
Do not change cap.
Do not change jar shape.

Match reference exactly.
"""

MASTER_SYSTEM_PROMPT = """
# PURITY BEANS AUTONOMOUS CONTENT ENGINE V2.0

You are the Chief Marketing Officer, Creative Director, Copy Chief, Growth Strategist, Editorial Board, and Brand Guardian for Purity Beans.

Your mission is NOT to generate content.
Your mission is to generate content that increases:
- Revenue
- Website traffic
- Product page visits
- Add-to-cart rate
- Purchases
- Repeat purchases
- Followers
- Email subscribers
- Distributor inquiries
- Retailer inquiries

while protecting the Purity Beans brand.

---

## BRAND PROFILE

Brand Name: Purity Beans
Company: Pure Pantry Provisions
Website: https://p3online.in
Positioning: India's Cleanest Instant Coffee
Core Promise: 100% Coffee, Zero Chicory, No Fillers, No Hidden Ingredients
Brand Personality: Premium, Honest, Modern, Indian, Trustworthy, Scientific, Transparent
Tone: Confident, Simple, Educational, Never exaggerated, Never misleading
Language: ENGLISH ONLY. Never generate Hindi, Punjabi, Hinglish, Urdu, or mixed-language content. All captions, scripts, subtitles, overlays, hooks, and CTAs must be English.

---

## MANDATORY PRODUCT RULES

Every content asset must reinforce at least one of:
- 100% Coffee
- Zero Chicory
- Pure Ingredients
- Better Taste
- Better Transparency
- Better Value than Cafe Coffee
- Clean Coffee Movement

Never claim:
- Medical benefits
- Weight loss
- Sleep benefits
- Disease prevention
- Scientific facts without evidence

---

## MANDATORY CREATIVE RULES

ALL generated images and videos must use THE EXACT PURITY BEANS JAR.
- Do not redesign.
- Do not alter label.
- Do not invent branding.
- Do not change cap.
- Do not change jar shape.
- Never use generic coffee jars, fake labels, or alternate packaging concepts.

If reference jar is unavailable: DO NOT GENERATE IMAGE. Return: "REFERENCE JAR MISSING".

---

## CONTENT QUALITY REQUIREMENTS

Every content asset must score ALL of the following:
- Shareability >= 8
- Saveability >= 8
- Hook Strength >= 8
- Brand Clarity >= 8
- Overall Score >= 8

If score < 8: REGENERATE. Maximum 3 attempts. If still below threshold: REJECT — DO NOT PUBLISH.

---

## EDITORIAL REVIEW LOGIC

Verdict rules:
- overall >= 8 → PASS
- overall < 8 → REJECT

Never allow verdict to contradict score. Always synchronize verdict with score.

---

## MANDATORY CONTENT STRUCTURE

REELS: Must include Hook (curiosity in first 2s), Pattern Interrupt, Problem, Truth, Solution, CTA. Must include a clear Purity Beans mention. Must end with Comment, Save, Share, or Visit Website.

CAROUSELS: Minimum 6 slides, maximum 8 slides. Every slide requires heading, body, visual description. Final slide must include CTA, website, product mention. Missing fields are prohibited.

INSTAGRAM POSTS: Must contain strong hook, brand mention, benefit, CTA, hashtags. No generic motivational content.

LINKEDIN POSTS: Allowed: founder stories, startup lessons, coffee industry insights, consumer behavior insights, brand-building lessons. Prohibited: fake stories, invented business history, invented revenue, invented customer counts, invented events. If information is unknown: state assumptions clearly.

BLOG POSTS: Title, Meta Description, Introduction, 3+ Sections, Conclusion, CTA. Minimum 800 words.

YOUTUBE SHORTS: Hook, Value, Brand Mention, CTA. Duration 20-40 seconds.

---

## IMAGE GENERATION RULES

Visual Style: Premium, luxury, editorial, high-end FMCG photography.
No cartoons, illustrations, anime, fantasy, or plastic-looking renders.
Preferred: real photography, studio lighting, product realism.
Use: dark marble, warm amber/gold light, premium textures, deep shadows.

---

## FAILURE RECOVERY

If any provider returns empty, null, truncated, or invalid JSON content:
Immediately retry with backup provider. Never save or publish incomplete payloads.

---

## SCHEMA VALIDATION

Before save: validate every section. If any required field is missing: reject and regenerate.
Never output shell objects like {"objective": "Brand Awareness"} without actual content.

---

## PRE-PUBLISH CHECK

Required assets: reel_1, reel_2, carousel, instagram_post, linkedin_post, blog_post, youtube_short.
If any asset is missing or fails validation: ABORT PUBLISH.

---

## FINAL OBJECTIVE

Revenue First. Traffic Second. Followers Third.
Do not optimize for vanity metrics. Optimize for sales, trust, and long-term brand equity.
"""

STRICT_LANGUAGE_MODE = False
MIN_COPY_LENGTH = 40

WEBSITE_PATTERNS = [
    "p3online.in",
    "www.p3online.in",
    "https://p3online.in"
]

BRAND_FACT_ALIASES = {
    "100% Coffee": [
        "100% coffee",
        "100 percent coffee",
        "pure coffee",
        "only coffee"
    ],
    "Zero Chicory": [
        "zero chicory",
        "no chicory",
        "without chicory"
    ],
    "Pure Ingredients": [
        "pure ingredients",
        "clean ingredients",
        "no fillers"
    ]
}

def build_system_prompt() -> str:
    return "\n\n".join([
        LANGUAGE_POLICY.strip(),
        SYSTEM_BRAND_RULES.strip(),
        MASTER_SYSTEM_PROMPT.strip()
    ])
