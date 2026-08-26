"""
Emergency fallback — the engine never misses a day.

When all three LLM providers fail (Gemini + Groq + OpenRouter), the
pipeline would normally crash and produce nothing. This module catches
that scenario and generates a reduced but valid content set from:

  1. Yesterday's strategy (same objective, proven hooks)
  2. Last week's best-performing content (remixed, not copied)
  3. Pre-baked evergreen templates (guaranteed safe fallback)

The founder receives a WhatsApp alert so they know the AI didn't run
at full capacity — but the social queue never goes dark.

Priority cascade:
  yesterday's snapshot → last week's best → evergreen templates

Usage (called automatically by daily.py):
    from content_generator.scheduler.fallback import emergency_content_set
    content = emergency_content_set(day_number=42)
"""
from __future__ import annotations
import datetime
import logging
import random

logger = logging.getLogger(__name__)


# ── Evergreen templates — always available, never stale ──────────────────────
# These are proven Purity Beans content patterns that work any day of the year.

# EVERY live truthfulness incident traced back to this file.
#
# The previous templates hardcoded, verbatim:
#   "Most people don't know their daily coffee has 40% chicory filler."
#       -> the fabricated statistic that published to the grid
#   "Try your first cup free. Link in bio."
#       -> an offer that has never existed
#   "Slide 1: It tastes bitter after 2 minutes"
#       -> the scaffolding leak that rendered into carousel images
#   "India spends Rs 6,000 crore...", "grew 34% YoY", "India's first"
#       -> unsourced market statistics and an unsubstantiated superlative
#
# None of it came from the LLM. The engine falls back here whenever generation
# fails, so the scrubbers, claim verifier and gates built downstream were all
# catching a defect that shipped with the fallback itself. Fallback content is
# published unattended on the worst days — it must be the SAFEST content in the
# repo, not the least reviewed.
#
# Rules for anything added here:
#   - only facts verifiable from our own label (see claim_verifier.VERIFIED_FACTS)
#   - no claims about what any other brand contains
#   - no market statistics, no superlatives, no offers
#   - no "Slide N:" / "Frame N:" scaffolding in viewer-facing copy
#   - must satisfy the schema, or the publish gate silently drops it
# tests/test_fallback_safety.py enforces all of the above.

_EVERGREEN: list[dict] = [
    {
        "type":      "reel",
        "hook":      "Turn the jar around before you buy it.",
        "hook_text": "Turn the jar around before you buy it.",
        "hook_spoken": "The front of the pack is marketing. The back is the recipe.",
        "hook_text_overlay": "READ THE BACK",
        "frames": [
            {"on_screen": "READ THE BACK",
             "spoken": "The front of the pack is marketing. The back is the recipe."},
            {"on_screen": "INGREDIENTS",
             "spoken": "Find the ingredient list. Read every line, not just the first."},
            {"on_screen": "WHAT'S IN OURS",
             "spoken": "Purity Beans lists one thing: coffee. Zero chicory, nothing added."},
            {"on_screen": "ONE LINE",
             "spoken": "Coffee needs one ingredient. Anything else is worth knowing about."},
            {"on_screen": "YOUR TURN",
             "spoken": "Check the jar in your kitchen tonight and see what it says."},
        ],
        "body":    "Purity Beans is 100% coffee. Zero chicory, no additives, no preservatives.",
        "caption": ("The front of a coffee pack is marketing. The back is the recipe.\n\n"
                    "Purity Beans lists one ingredient: coffee. Zero chicory, nothing added.\n\n"
                    "Check the jar in your kitchen tonight.\n\np3online.in"),
        "cta":     "Read the label, then shop at p3online.in",
        "comment_trigger": "What does the label on your jar actually say?",
        "save_trigger":    "Save this for your next grocery run.",
        "share_trigger":   "Send this to whoever buys the coffee in your house.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "audio":   "Quiet kitchen ambience, no music bed — the spoken line carries it.",
        "loop_ending": "Ends on the jar being turned around, which is where it opens — the last frame reads as the first.",
        "angle":   "EXPOSE",
        "source":  "evergreen_template",
    },
    {
        "type":  "carousel",
        "hook":  "Three things to check on a coffee label",
        "title": "Three things to check on a coffee label",
        "slides": [
            {"slide": 1, "heading": "Read the ingredient list",
             "body": "It is on the back, usually in the smallest type on the pack.",
             "visual": "Close-up of an ingredient panel, jar turned to camera"},
            {"slide": 2, "heading": "Count the ingredients",
             "body": "Coffee needs one. Anything else is there for a reason worth knowing.",
             "visual": "Finger tracing down a short ingredient list"},
            {"slide": 3, "heading": "Look for chicory by name",
             "body": "It is a root, not a bean, and it is listed when present.",
             "visual": "Ingredient panel with the word chicory in frame"},
            {"slide": 4, "heading": "Check the order",
             "body": "Ingredients are listed by weight, so the first one is the bulk of it.",
             "visual": "Ingredient panel with the first line highlighted"},
            {"slide": 5, "heading": "What ours says",
             "body": "Purity Beans lists coffee. Zero chicory, no additives.",
             "visual": "Purity Beans jar, label facing camera"},
            # The schema requires the website on the final slide — the carousel
            # is the one format where the CTA lives in the image, not the caption.
            {"slide": 6, "heading": "Do it tonight",
             "body": "Turn around the jar in your kitchen and read the list. "
                     "Purity Beans — p3online.in",
             "visual": "Hand turning a jar on a kitchen counter"},
        ],
        "caption": ("Three things worth checking on any coffee label.\n\n"
                    "Purity Beans lists one ingredient: coffee.\n\n"
                    "Zero chicory, no additives.\n\np3online.in"),
        "cta":     "Shop pure coffee at p3online.in",
        "comment_trigger": "Which of the three surprised you?",
        "save_trigger":    "Save this for your next grocery run.",
        "share_trigger":   "Share with someone who drinks instant daily.",
        "hashtags": "#PurityBeans #PureCoffee #ZeroChicory #CoffeeIndia #ReadTheLabel",
        "source":  "evergreen_template",
    },
    {
        "type":    "instagram_post",
        "hook":    "One ingredient. That is the whole list.",
        "body":    "Purity Beans is 100% coffee. Zero chicory, no additives, no preservatives.",
        "caption": ("One ingredient. That is the whole list.\n\n"
                    "Purity Beans is 100% coffee — zero chicory, no additives, "
                    "no preservatives.\n\nTurn your jar around and compare.\n\np3online.in"),
        "cta":     "Shop at p3online.in",
        "comment_trigger": "How many ingredients are on your jar?",
        "save_trigger":    "Save this for your next grocery run.",
        "share_trigger":   "Send this to a fellow coffee drinker.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeLover",
        "source":  "evergreen_template",
    },
    {
        "type": "linkedin_post",
        "hook": "We built a coffee brand around a shorter ingredient list",
        "body": (
            "Instant coffee in India is a category where the ingredient list is "
            "the most informative thing on the pack, and the least read.\n\n"
            "We built Purity Beans around a simple constraint: one ingredient. "
            "Coffee. Zero chicory, no additives, no preservatives.\n\n"
            "That constraint decides sourcing, cost and shelf positioning — it is "
            "a harder product to make and an easier one to explain.\n\n"
            "For distributors and retailers interested in stocking it, my DMs are open.\n\n"
            "p3online.in"
        ),
        "cta": "Distributor and retailer enquiries welcome in DMs",
        "hashtags": "#Coffee #FMCG #IndianBrands #Distribution #PurityBeans",
        "source": "evergreen_template",
    },
    # ── Set 2 — count the ingredients ─────────────────────────────────────────
    {
        "type": "reel",
        "hook": "Instant coffee should have a very short ingredient list.",
        "hook_text": "Instant coffee should have a very short ingredient list.",
        "hook_spoken": "Pick up any jar of instant coffee and count the lines.",
        "hook_text_overlay": "COUNT THE LINES",
        "frames": [
            {"on_screen": "COUNT THE LINES",
             "spoken": "Pick up any jar of instant coffee and count the ingredients."},
            {"on_screen": "ONE IS ENOUGH",
             "spoken": "Coffee needs one ingredient to be coffee. That is the whole list."},
            {"on_screen": "ANYTHING ELSE",
             "spoken": "Everything after the first line is there for a reason. Worth knowing which."},
            {"on_screen": "WHAT OURS SAYS",
             "spoken": "Purity Beans lists coffee. Zero chicory, no additives, no preservatives."},
            {"on_screen": "GO COUNT",
             "spoken": "Go count the lines on the jar in your kitchen right now."},
        ],
        "body": "Purity Beans is 100% coffee. Zero chicory, no additives, no preservatives.",
        "caption": "Count the ingredients on your instant coffee.\n\nCoffee needs one. Purity Beans lists one: coffee.\n\nCheck the jar in your kitchen tonight.\n\np3online.in",
        "cta": "Count yours, then shop at p3online.in",
        "comment_trigger": "How many ingredients does your jar list?",
        "save_trigger": "Save this before your next grocery run.",
        "share_trigger": "Send this to whoever buys the coffee in your house.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "audio": "Quiet kitchen ambience, no music bed - the spoken line carries it.",
        "loop_ending": "Ends on the jar being picked up, which is how it opens - the last frame reads as the first.",
        "angle": "EDUCATE",
        "source": "evergreen_template",
    },
    {
        "type": "carousel",
        "hook": "What 100% coffee actually means",
        "title": "What 100% coffee actually means",
        "slides": [
            {"slide": 1, "heading": "It is a claim about the list",
             "body": "It means the ingredient list has coffee on it and nothing else.",
             "visual": "Ingredient panel filling the frame"},
            {"slide": 2, "heading": "Not a claim about strength",
             "body": "Strength comes from how much you use and how you brew it.",
             "visual": "Spoon of coffee held over a cup"},
            {"slide": 3, "heading": "Not a claim about roast",
             "body": "Roast changes flavour. It does not change what is in the jar.",
             "visual": "Two jars side by side on a counter"},
            {"slide": 4, "heading": "Read it as a list, not a slogan",
             "body": "The front of a pack is designed. The back is declared.",
             "visual": "Jar being turned from front to back"},
            {"slide": 5, "heading": "What ours says",
             "body": "Purity Beans lists coffee. Zero chicory, no additives.",
             "visual": "Purity Beans jar, label facing camera"},
            {"slide": 6, "heading": "Check yours tonight",
             "body": "Turn the jar around and read the list. Purity Beans - p3online.in",
             "visual": "Hand turning a jar on a kitchen counter"},
        ],
        "caption": "100% coffee is a claim about the ingredient list, not about strength or roast.\n\nPurity Beans lists one ingredient: coffee.\n\nCheck the jar in your kitchen tonight.\n\np3online.in",
        "cta": "Read your label, then shop at p3online.in",
        "comment_trigger": "What does your jar list after the first line?",
        "save_trigger": "Save this for your next grocery run.",
        "share_trigger": "Send this to whoever buys the coffee in your house.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },
    {
        "type": "instagram_post",
        "hook": "Ingredients are listed by weight, so the first line is most of the jar.",
        "body": "That is why the order matters as much as the list. Purity Beans lists coffee. Zero chicory, no additives.",
        "caption": "Ingredients are listed by weight, so the first line is most of what you are buying.\n\nThe order tells you as much as the list does.\n\nPurity Beans is 100% coffee. Zero chicory.\n\np3online.in",
        "cta": "Read the label, then shop at p3online.in",
        "comment_trigger": "What is the first ingredient on your jar?",
        "save_trigger": "Save this for your next grocery run.",
        "share_trigger": "Send this to whoever buys the coffee in your house.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },

    # ── Set 3 — chicory, explained plainly ────────────────────────────────────
    {
        "type": "reel",
        "hook": "Chicory is a root, not a coffee bean.",
        "hook_text": "Chicory is a root, not a coffee bean.",
        "hook_spoken": "Chicory is a root. Roasted and ground, it looks a lot like coffee.",
        "hook_text_overlay": "ROOT, NOT BEAN",
        "frames": [
            {"on_screen": "ROOT, NOT BEAN",
             "spoken": "Chicory is a root. Roasted and ground, it looks a lot like coffee."},
            {"on_screen": "IT IS DECLARED",
             "spoken": "When it is in the jar, it is named on the ingredient list."},
            {"on_screen": "FIVE SECONDS",
             "spoken": "Which means you can find out by turning the jar around."},
            {"on_screen": "WHAT OURS SAYS",
             "spoken": "Purity Beans lists coffee and nothing else. Zero chicory."},
            {"on_screen": "CHECK YOURS",
             "spoken": "Turn your jar around tonight and look for the word."},
        ],
        "body": "Chicory is a roasted root. It is declared on the label when present. Purity Beans lists coffee only.",
        "caption": "Chicory is a root, not a bean. Roasted and ground, it looks like coffee.\n\nWhen it is in a jar it is named on the label, so you can check in seconds.\n\nPurity Beans lists coffee. Zero chicory.\n\np3online.in",
        "cta": "Check your label, then shop at p3online.in",
        "comment_trigger": "Does the word chicory appear on your jar?",
        "save_trigger": "Save this so you remember what to look for.",
        "share_trigger": "Send this to someone who has never read their coffee label.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "audio": "Quiet kitchen ambience, no music bed - the spoken line carries it.",
        "loop_ending": "Ends on the jar turning, which is how it opens - the last frame reads as the first.",
        "angle": "EDUCATE",
        "source": "evergreen_template",
    },
    {
        "type": "carousel",
        "hook": "Chicory, explained without the drama",
        "title": "Chicory, explained without the drama",
        "slides": [
            {"slide": 1, "heading": "It is a root",
             "body": "Chicory is a plant root, not a coffee bean.",
             "visual": "Chicory root beside coffee beans on a board"},
            {"slide": 2, "heading": "It is roasted and ground",
             "body": "Processed that way, it looks very similar to ground coffee.",
             "visual": "Two dark grounds side by side in bowls"},
            {"slide": 3, "heading": "It carries its own taste",
             "body": "It is more bitter and a little woody next to coffee.",
             "visual": "Two cups poured side by side"},
            {"slide": 4, "heading": "It is always declared",
             "body": "If it is in the jar, it is named on the ingredient list.",
             "visual": "Ingredient panel with a finger pointing at a line"},
            {"slide": 5, "heading": "So you can simply check",
             "body": "Turning the jar around answers the question in seconds.",
             "visual": "Hand rotating a jar to the back label"},
            {"slide": 6, "heading": "What ours says",
             "body": "Purity Beans lists coffee. Zero chicory. p3online.in",
             "visual": "Purity Beans jar, label facing camera"},
        ],
        "caption": "Chicory is a root, not a bean. Roasted and ground it looks like coffee, and it is always named on the label when present.\n\nPurity Beans lists coffee. Zero chicory.\n\nCheck the jar in your kitchen tonight.\n\np3online.in",
        "cta": "Check your label, then shop at p3online.in",
        "comment_trigger": "Does the word chicory appear on your jar?",
        "save_trigger": "Save this so you know what to look for.",
        "share_trigger": "Send this to someone who has never checked.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },
    {
        "type": "instagram_post",
        "hook": "Chicory is a root, not a coffee bean.",
        "body": "Roasted and ground it looks like coffee, and it is named on the ingredient list whenever it is in the jar. Purity Beans lists coffee. Zero chicory.",
        "caption": "Chicory is a root, not a bean.\n\nRoasted and ground it looks like coffee - and it is always named on the label when it is there.\n\nPurity Beans lists coffee. Zero chicory.\n\np3online.in",
        "cta": "Check your label, then shop at p3online.in",
        "comment_trigger": "Does the word chicory appear on your jar?",
        "save_trigger": "Save this so you remember what to look for.",
        "share_trigger": "Send this to someone who has never read their label.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },
    # ── Set 4 — how to keep it tasting like it should ─────────────────────────
    {
        "type": "reel",
        "hook": "Most instant coffee goes stale in the jar, not in the shop.",
        "hook_text": "Most instant coffee goes stale in the jar, not in the shop.",
        "hook_spoken": "The jar on your counter is doing more damage than the shelf ever did.",
        "hook_text_overlay": "SEAL IT",
        "frames": [
            {"on_screen": "SEAL IT",
             "spoken": "The jar on your counter is doing more damage than the shelf ever did."},
            {"on_screen": "AIR",
             "spoken": "Every time it stays open, moisture gets in and aroma gets out."},
            {"on_screen": "HEAT",
             "spoken": "Above the stove is the warmest shelf in the kitchen. Move it."},
            {"on_screen": "DRY SPOON",
             "spoken": "A wet spoon clumps the whole jar. Keep one spoon dry, just for coffee."},
            {"on_screen": "TONIGHT",
             "spoken": "Close it tight, move it off the stove, and taste the difference this week."},
        ],
        "body": "Purity Beans is 100% coffee. Zero chicory, no additives, no preservatives.",
        "caption": "Instant coffee usually goes stale in the jar, not in the shop.\n\nClose it tight, keep it off the stove, use a dry spoon.\n\nPurity Beans is 100% coffee. Zero chicory.\n\np3online.in",
        "cta": "Store it right, then restock at p3online.in",
        "comment_trigger": "Where does the coffee jar live in your kitchen?",
        "save_trigger": "Save this and move your jar tonight.",
        "share_trigger": "Send this to whoever leaves the lid off.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "audio": "Quiet kitchen ambience, no music bed - the spoken line carries it.",
        "loop_ending": "Ends on the lid closing, which is how it opens - the last frame reads as the first.",
        "angle": "EDUCATE",
        "source": "evergreen_template",
    },
    {
        "type": "carousel",
        "hook": "Four things that stale your coffee at home",
        "title": "Four things that stale your coffee at home",
        "slides": [
            {"slide": 1, "heading": "An open lid",
             "body": "Aroma leaves the moment the jar is open. Close it between cups.",
             "visual": "Open jar on a counter, lid beside it"},
            {"slide": 2, "heading": "A wet spoon",
             "body": "Moisture clumps what it touches and the clumps spread.",
             "visual": "Damp spoon going into a jar"},
            {"slide": 3, "heading": "The shelf above the stove",
             "body": "It is the warmest place in the kitchen. Pick a cooler one.",
             "visual": "Jar on a shelf directly above a hob"},
            {"slide": 4, "heading": "Sunlight on the counter",
             "body": "Light and warmth together age it faster than either alone.",
             "visual": "Jar in a bright window"},
            {"slide": 5, "heading": "Fix all four tonight",
             "body": "Lid closed, dry spoon, cool shelf, out of the sun.",
             "visual": "Jar being moved into a closed cupboard"},
            {"slide": 6, "heading": "What ours says",
             "body": "Purity Beans is 100% coffee. Zero chicory. p3online.in",
             "visual": "Purity Beans jar, label facing camera"},
        ],
        "caption": "Four things stale your coffee at home: an open lid, a wet spoon, the shelf above the stove, and direct sun.\n\nAll four are free to fix tonight.\n\nPurity Beans is 100% coffee. Zero chicory.\n\np3online.in",
        "cta": "Store it right, then restock at p3online.in",
        "comment_trigger": "Which of the four is happening in your kitchen?",
        "save_trigger": "Save this and fix one tonight.",
        "share_trigger": "Send this to whoever leaves the lid off.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },
    {
        "type": "instagram_post",
        "hook": "A wet spoon will clump a whole jar of instant coffee.",
        "body": "Keep one dry spoon for coffee, close the lid between cups, and keep the jar off the shelf above the stove. Purity Beans is 100% coffee. Zero chicory.",
        "caption": "A wet spoon will clump a whole jar.\n\nOne dry spoon, lid closed between cups, and keep it off the shelf above the stove.\n\nPurity Beans is 100% coffee. Zero chicory.\n\np3online.in",
        "cta": "Store it right, then restock at p3online.in",
        "comment_trigger": "Where does your coffee jar live?",
        "save_trigger": "Save this and move your jar tonight.",
        "share_trigger": "Send this to whoever leaves the lid off.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },

    # ── Set 5 — freeze dried, explained ───────────────────────────────────────
    {
        "type": "reel",
        "hook": "Freeze dried and spray dried are not the same thing.",
        "hook_text": "Freeze dried and spray dried are not the same thing.",
        "hook_spoken": "Two jars can both say instant coffee and be made completely differently.",
        "hook_text_overlay": "TWO METHODS",
        "frames": [
            {"on_screen": "TWO METHODS",
             "spoken": "Two jars can both say instant coffee and be made completely differently."},
            {"on_screen": "SPRAY DRIED",
             "spoken": "Spray drying uses hot air. It is fast, and heat costs aroma."},
            {"on_screen": "FREEZE DRIED",
             "spoken": "Freeze drying works cold, so more of the aroma survives the process."},
            {"on_screen": "LOOK AT IT",
             "spoken": "Freeze dried looks like crystals. Spray dried looks like fine powder."},
            {"on_screen": "OURS",
             "spoken": "Purity Beans is freeze dried arabica. 100% coffee, zero chicory."},
        ],
        "body": "Purity Beans is freeze dried arabica. 100% coffee, zero chicory, no additives.",
        "caption": "Freeze dried and spray dried are not the same thing.\n\nSpray drying uses hot air. Freeze drying works cold, so more aroma survives.\n\nLook at the granules: crystals or powder.\n\nPurity Beans is freeze dried arabica. 100% coffee, zero chicory.\n\np3online.in",
        "cta": "Look at your granules, then shop at p3online.in",
        "comment_trigger": "Crystals or powder in your jar?",
        "save_trigger": "Save this for your next grocery run.",
        "share_trigger": "Send this to the coffee drinker who has never looked closely.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "audio": "Quiet kitchen ambience, no music bed - the spoken line carries it.",
        "loop_ending": "Ends on the granules in close up, which is how it opens - the last frame reads as the first.",
        "angle": "EDUCATE",
        "source": "evergreen_template",
    },
    {
        "type": "carousel",
        "hook": "Crystals or powder: what your granules tell you",
        "title": "Crystals or powder: what your granules tell you",
        "slides": [
            {"slide": 1, "heading": "Tip some into your palm",
             "body": "Before the water goes in, look at what you are actually holding.",
             "visual": "Granules poured into an open palm"},
            {"slide": 2, "heading": "Crystals mean freeze dried",
             "body": "Irregular, glassy pieces that catch the light.",
             "visual": "Macro shot of coffee crystals"},
            {"slide": 3, "heading": "Fine powder means spray dried",
             "body": "Even, dusty and uniform, because hot air made it.",
             "visual": "Macro shot of fine coffee powder"},
            {"slide": 4, "heading": "Why the method matters",
             "body": "Freeze drying works cold, so more of the aroma survives.",
             "visual": "Steam rising from a fresh cup"},
            {"slide": 5, "heading": "It is on the pack",
             "body": "The method is usually printed on the label. Look for it.",
             "visual": "Label with the drying method in frame"},
            {"slide": 6, "heading": "What ours says",
             "body": "Purity Beans is freeze dried arabica. 100% coffee, zero chicory. p3online.in",
             "visual": "Purity Beans jar, label facing camera"},
        ],
        "caption": "Tip some granules into your palm before the water goes in.\n\nCrystals mean freeze dried. Fine powder means spray dried, which uses hot air.\n\nPurity Beans is freeze dried arabica. 100% coffee, zero chicory.\n\np3online.in",
        "cta": "Look at your granules, then shop at p3online.in",
        "comment_trigger": "Crystals or powder in your jar?",
        "save_trigger": "Save this and check your jar tonight.",
        "share_trigger": "Send this to someone who has never looked closely.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },
    {
        "type": "instagram_post",
        "hook": "Two jars of instant coffee can look completely different in your palm.",
        "body": "Irregular glassy crystals mean freeze dried. Even fine powder means spray dried, which uses hot air. Purity Beans is freeze dried arabica. 100% coffee, zero chicory.",
        "caption": "Tip some into your palm before the water goes in.\n\nCrystals mean freeze dried. Fine powder means spray dried, made with hot air.\n\nPurity Beans is freeze dried arabica. 100% coffee, zero chicory.\n\np3online.in",
        "cta": "Look at your granules, then shop at p3online.in",
        "comment_trigger": "Crystals or powder in your jar?",
        "save_trigger": "Save this and check your jar tonight.",
        "share_trigger": "Send this to someone who has never looked closely.",
        "hashtags": "#PurityBeans #PureCoffee #InstantCoffee #ZeroChicory #CoffeeIndia",
        "source": "evergreen_template",
    },
]

_DISTRIBUTOR_TEMPLATES: list[dict] = [
    {
        "type": "linkedin_post",
        "hook": "What our distributors ask about first",
        "body": (
            "The first question is always the ingredient list, because it is what "
            "the customer asks them about at the counter.\n\n"
            "Purity Beans is 100% coffee — zero chicory, no additives, no "
            "preservatives — which makes it a straightforward product to stand "
            "behind on a shelf full of blends.\n\n"
            "We are expanding our distributor network. If you distribute FMCG and "
            "want the details, message me.\n\np3online.in"
        ),
        "cta": "DM for the distributor pack",
        "hashtags": "#FMCG #Distribution #Coffee #IndianBrands #PurityBeans",
        "source": "evergreen_distributor",
    },
]


def emergency_content_set(day_number: int = 0) -> dict:
    """
    Generate a reduced content set when all LLM providers are unavailable.

    Returns a valid content dict with the same keys as generate_daily_content(),
    so the rest of the pipeline (save, memory, objectives) can continue normally.
    """
    logger.warning(
        "[fallback] ALL LLM PROVIDERS FAILED — using emergency content set for day %d",
        day_number,
    )

    # Try yesterday's snapshot first
    content = _from_yesterday_snapshot(day_number)
    if content:
        logger.info("[fallback] Using yesterday's snapshot as base")
        _send_fallback_alert("yesterday_snapshot", day_number)
        return _attach_stories(content, day_number)

    # Try last week's best content
    content = _from_best_historical(day_number)
    if content:
        logger.info("[fallback] Using best historical content")
        _send_fallback_alert("historical_best", day_number)
        return _attach_stories(content, day_number)

    # Final safety net: evergreen templates
    logger.warning("[fallback] Using evergreen templates (minimum viable output)")
    _send_fallback_alert("evergreen_templates", day_number)
    return _attach_stories(_from_evergreen(day_number), day_number)


def _from_yesterday_snapshot(day_number: int) -> dict | None:
    """Extract and lightly remix yesterday's content."""
    try:
        from content_generator.scheduler.snapshot import load_yesterday_snapshot
        snap = load_yesterday_snapshot()
        if not snap or "content" not in snap:
            return None

        yesterday_content = snap["content"]
        # Mark as recycled so analytics can discount it
        yesterday_content["_source"]    = "emergency_fallback_yesterday"
        yesterday_content["_recycled"]  = True
        yesterday_content["day_number"] = day_number

        # Freshen the date references in copy (basic swap)
        today_str = datetime.date.today().strftime("%B %d")
        return yesterday_content
    except Exception as e:
        logger.debug("[fallback] yesterday snapshot failed: %s", e)
        return None


def _from_best_historical(day_number: int) -> dict | None:
    """Build a content set from the highest-performing historical pieces."""
    try:
        from content_generator.analytics.metrics_store import get_recent_metrics
        rows = get_recent_metrics(days=30)
        if not rows or len(rows) < 3:
            return None

        # Top 4 by viral score
        top = sorted(rows, key=lambda x: x.get("viral_score", 0), reverse=True)[:4]

        reels = []
        for r in top[:2]:
            reels.append({
                "hook":   r.get("hook_archetype", "Pure coffee. Real taste."),
                "body":   "Purity Beans — 100% pure instant coffee. Rs 18/cup.",
                "cta":    "Link in bio.",
                "_source": f"recycled:{r.get('content_id', '')}",
            })

        return {
            "day_number":     day_number,
            "reels":          reels,
            "carousel":       _EVERGREEN[1],
            "instagram_post": _EVERGREEN[2],
            "linkedin_post":  _DISTRIBUTOR_TEMPLATES[0],
            "_source":        "emergency_fallback_historical",
            "_recycled":      True,
        }
    except Exception as e:
        logger.debug("[fallback] historical best failed: %s", e)
        return None


def _of_type(kind: str) -> list[dict]:
    return [p for p in _EVERGREEN if p.get("type") == kind]


def _pick(kind: str, day_number: int, offset: int = 0) -> dict | None:
    """Deterministic day-indexed pick, so consecutive days differ and any day is reproducible."""
    pool = _of_type(kind)
    if not pool:
        return None
    return pool[(int(day_number or 0) + offset) % len(pool)]


def _from_evergreen(day_number: int) -> dict:
    """
    Guaranteed fallback using static evergreen templates, rotated by day.

    This used to random.shuffle() the template list and take the first of each
    type. With one template per type that was a shuffle of a single-element
    list: every fallback day produced byte-identical content. Since no day has
    ever produced real generation, that is every post the account has ever made
    — the same reel, the same carousel, the same caption, for weeks.

    Rotation is now indexed by day rather than randomised, which:
      - guarantees consecutive days differ, where shuffling only made it likely
      - makes any given day reproducible, so a bad post can be traced to a
        template instead of an unrecoverable RNG draw
      - offsets reel_2 from reel_1 so the two reels in a day are never the same
    """
    reels = [r for r in (_pick("reel", day_number), _pick("reel", day_number, 1)) if r]
    while len(reels) < 2 and _of_type("reel"):
        reels.append(_of_type("reel")[0])

    payload = {
        "day_number":     day_number,
        "reels":          reels,
        "carousel":       _pick("carousel", day_number) or _EVERGREEN[1],
        "instagram_post": _pick("instagram_post", day_number) or _EVERGREEN[2],
        "linkedin_post":  _DISTRIBUTOR_TEMPLATES[
                              int(day_number or 0) % len(_DISTRIBUTOR_TEMPLATES)],
        "_source":        "emergency_fallback_evergreen",
        "_recycled":      True,
    }
    return _attach_stories(payload, day_number)


def _attach_stories(payload: dict, day_number: int) -> dict:
    """Give fallback days a stories.story_1 so post_story is not slogan-only."""
    if not isinstance(payload, dict):
        return payload
    stories = payload.get("stories") if isinstance(payload.get("stories"), dict) else {}
    s1 = stories.get("story_1") if isinstance(stories.get("story_1"), dict) else {}
    if s1.get("headline") or s1.get("poll_question"):
        return payload
    try:
        from content_generator.publisher.story_copy import stories_block_from_content
        payload["stories"] = stories_block_from_content(payload, day_number)
    except Exception as e:
        logger.debug("[fallback] stories block skipped: %s", e)
    return payload


def _send_fallback_alert(source: str, day_number: int) -> None:
    """Alert the founder that the fallback activated."""
    msg = (
        f"FALLBACK ACTIVATED — Day {day_number}\n"
        f"Source: {source}\n"
        f"All LLM providers unavailable.\n"
        f"Reduced content set generated.\n"
        f"Check API keys and provider status."
    )
    try:
        from content_generator.scheduler.watchdog import _alert
        _alert(msg)
    except Exception:
        logger.warning("[fallback] %s", msg)
