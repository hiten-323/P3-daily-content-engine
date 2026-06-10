"""
Purity Beans — brand configuration.

Single source of truth for brand identity, positioning, hashtags, and
content guardrails used across all content generation prompts.

Import from anywhere in the engine:
    from config.brand_config import BRAND, POSITIONING, HASHTAG_SETS
"""

# ── Core brand identity ───────────────────────────────────────────────────────

BRAND = {
    "name":        "Purity Beans",
    "tagline":     "100% Pure. Zero Chicory.",
    "category":    "Premium Instant Coffee",
    "origin":      "India",
    "website":     "https://p3online.in",
    "instagram":   "@puritybeans",
    "tone":        "premium but human, honest not corporate, Indian in DNA",
    "colors": {
        "background": "#0D0905",   # espresso dark
        "gold":       "#C8962E",   # signature gold
        "cream":      "#F5EED8",   # warm cream text
    },
}

# ── Market positioning ────────────────────────────────────────────────────────

POSITIONING = {
    "usp":              "100% pure coffee — zero chicory, zero compromise",
    "price_per_cup":    18,            # Rs
    "cafe_price":       180,           # Rs (average cafe latte)
    "price_ratio":      "10x cheaper than cafes",
    "purity_claim":     "No chicory. No fillers. Just coffee.",
    "target_segments": {
        "consumer":     "urban Indians 25-45 who care about what they drink",
        "distributor":  "FMCG distributors in Tier-1 and Tier-2 cities",
        "modern_trade": "supermarket buyers and category managers",
        "retailer":     "kirana stores and specialty food retailers",
    },
    "competitors_to_avoid_naming": ["Nescafé", "Bru", "Davidoff", "Continental"],
    "key_pain_points": [
        "Most instant coffee is 70-80% chicory, not coffee",
        "Consumers are unknowingly drinking chicory filler",
        "Premium cafe quality is unaffordable daily",
        "No transparency about coffee purity on labels",
    ],
    "proof_points": [
        "100% Arabica / Robusta blend — zero adulterants",
        "Rs 18 per cup vs Rs 180 at cafes",
        "Ships from roaster to door — freshest possible",
        "Lab-tested purity certificate on every batch",
    ],
}

# ── Hashtag sets by content type ──────────────────────────────────────────────

HASHTAG_SETS = {
    "reels": (
        "#PurityBeans #PureCoffee #InstantCoffee #NoCicory #CoffeeLover "
        "#IndianCoffee #CoffeeIndia #PremiumCoffee #CoffeeReels "
        "#CoffeeOfTheDay #MorningCoffee"
    ),
    "viral_reel": (
        "#PurityBeans #NoCicory #CoffeeTruth #InstantCoffee #CoffeeLover "
        "#PureCoffee #IndianCoffee #CoffeeShorts #CoffeeReels #FoodFacts"
    ),
    "educational_reel": (
        "#PurityBeans #CoffeeFacts #InstantCoffee #PureCoffee #NoCicory "
        "#CoffeeEducation #IndianCoffee #CoffeeLover #KnowYourCoffee"
    ),
    "carousel": (
        "#PurityBeans #PureCoffee #InstantCoffee #NoCicory #CoffeeLover "
        "#IndianCoffee #PremiumCoffee #CoffeeCarousel #SaveThis #LearnWithCoffee"
    ),
    "linkedin": (
        "#PurityBeans #D2CBrand #FoodBusiness #IndianStartup #PureCoffee "
        "#CPGIndia #FMCGIndia #BrandBuilding #Entrepreneurship"
    ),
    "instagram": (
        "#PurityBeans #PureCoffee #InstantCoffee #NoCicory #CoffeeLover "
        "#IndianCoffee #CoffeeIndia #MorningBrew #CoffeeDaily"
    ),
    "story": (
        "#PurityBeans #PureCoffee #InstantCoffee #NoCicory #CoffeeLover"
    ),
    "blog": (
        "purity beans, pure instant coffee, no chicory coffee, "
        "best instant coffee india, 100% arabica instant coffee"
    ),
    "b2b": (
        "#PurityBeans #DistributorOpportunity #FMCGIndia #CPGIndia "
        "#InstantCoffee #B2BCoffee #IndianBrand"
    ),
}

# ── Content guardrails ────────────────────────────────────────────────────────

BANNED_PHRASES = [
    "transform your mornings",
    "elevate your experience",
    "perfect cup",
    "fuel your day",
    "game changer",
    "level up",
    "discover the difference",
    "premium quality",
    "best coffee",
    "world class",
    "unmatched quality",
    "superior taste",
    "crafted with care",
    "passion for coffee",
    "artisanal",
    "small batch",         # only if untrue
    "sustainable",         # only if unverified
]

REQUIRED_ELEMENTS = {
    "every_post":   ["brand name mention", "zero chicory claim OR price mention"],
    "reel":         ["hook in first 3 seconds", "CTA at end"],
    "carousel":     ["save-worthy information", "slide 1 stops the scroll"],
    "linkedin":     ["business angle", "distributor/retailer relevance"],
    "blog":         ["keyword in title", "purity claim", "shop CTA"],
}

# ── Business targets ──────────────────────────────────────────────────────────

BUSINESS_TARGETS = {
    "monthly_revenue_inr":    500_000,    # Rs 5L/month target
    "daily_orders_target":    50,
    "avg_order_value_inr":    350,
    "distributor_target":     5,          # active distributors
    "retailer_target":        50,         # retail outlets
    "content_pieces_per_day": 6,          # reels + carousel + linkedin + blog + stories + yt
}
