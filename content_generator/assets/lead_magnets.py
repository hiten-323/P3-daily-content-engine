"""
Lead magnets — the REAL resources a value-unlock reel gives away.

The value-unlock mechanic ("comment GUIDE and I'll send it") only works if the
thing actually exists and is worth having. These are ready-to-send resources
the founder pastes into a DM/comment reply when someone comments the keyword.

Each has: a keyword (what people comment), a promise (what the reel offers),
and the deliverable (what you send back). Keep the deliverable genuinely
useful — that is what converts a follow into trust.

Delivery is MANUAL by the founder (Policy #001: no mass auto-DM tools). At low
follower counts a personal reply converts far better than automation anyway.
"""

LEAD_MAGNETS = [
    {
        "keyword": "CHICORY",
        "promise": "the 30-second test to check if YOUR coffee has chicory",
        "deliverable": (
            "The Chicory Test (works on any instant coffee):\n"
            "1. Add a spoon of your coffee to a glass of COLD water. Do not stir.\n"
            "2. Pure coffee floats and dissolves slowly, staining the water evenly.\n"
            "3. Chicory sinks fast and sends brown streaks straight down.\n"
            "The faster and heavier it sinks, the more chicory it has.\n"
            "Purity Beans is 100% coffee — it floats. See for yourself: p3online.in"
        ),
    },
    {
        "keyword": "GUIDE",
        "promise": "the Pure Coffee Buyer's Guide — read any label like an expert",
        "deliverable": (
            "Pure Coffee Buyer's Guide (India):\n"
            "- 'Coffee-chicory mix' = it has chicory, however small the print.\n"
            "- 'Instant coffee' with no % usually means a blend.\n"
            "- Look for '100% coffee' stated plainly — if it's not there, assume filler.\n"
            "- Freeze-dried = gentler process, keeps aroma. Agglomerated = spray-dried "
            "then clumped, still pure if labelled 100% coffee.\n"
            "- Price is not proof of purity. The label is.\n"
            "Purity Beans prints exactly what's inside: p3online.in"
        ),
    },
    {
        "keyword": "BREW",
        "promise": "the barista method for cafe-quality coffee at home in 2 minutes",
        "deliverable": (
            "2-Minute Barista Method (no machine):\n"
            "1. 1 heaped tsp Purity Beans in a cup.\n"
            "2. Add 2 tsp hot (not boiling) water + 1 tsp sugar if you like it sweet.\n"
            "3. Whisk/spoon-beat 40 seconds until pale and creamy.\n"
            "4. Add hot milk or water. The beaten paste floats up as a foam layer.\n"
            "Cafe texture, Rs 18 a cup. Get the coffee: p3online.in"
        ),
    },
    {
        "keyword": "GIFT",
        "promise": "the corporate gifting rate card + which variant suits which client",
        "deliverable": (
            "Purity Beans Corporate Gifting:\n"
            "- Purista / Purica gourmet jars = premium client & festival gifting.\n"
            "- Ultra Blend = bulk office pantry, everyday crowd-pleaser.\n"
            "- Bold = for the serious-coffee clients who notice quality.\n"
            "Custom hampers and bulk rates available. Reply here or visit p3online.in "
            "and mention 'corporate gifting'."
        ),
    },
]


def get_todays_lead_magnet(day: int) -> dict:
    return LEAD_MAGNETS[day % len(LEAD_MAGNETS)]
