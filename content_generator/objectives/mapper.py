"""
Business objective mapper.

Every content piece is assigned a primary business objective so the engine
optimises for REVENUE, not just vanity metrics.

Objectives rotate deterministically by day so the weekly content mix
always drives all revenue levers — not just brand awareness.

Objectives:
  Consumer Purchase     — drive direct buy at p3online.in
  Brand Awareness       — reach new audiences, grow followers
  Distributor Acquisition — attract FMCG distribution partners
  Retailer Lead Gen     — attract retail shelf placement
  Website Traffic       — drive blog / product page visits
  Engagement Growth     — shares, saves, comments for algorithmic reach
"""
from typing import Literal

ObjectiveType = Literal[
    "Consumer Purchase",
    "Brand Awareness",
    "Distributor Acquisition",
    "Retailer Lead Gen",
    "Website Traffic",
    "Engagement Growth",
]

# For each content type, objectives rotate in priority order (index = day % len)
_ROTATION: dict[str, list[ObjectiveType]] = {
    "reel_1":         ["Brand Awareness",        "Consumer Purchase",       "Engagement Growth"],
    "reel_2":         ["Consumer Purchase",       "Brand Awareness",         "Engagement Growth"],
    "instagram_post": ["Consumer Purchase",       "Website Traffic",         "Brand Awareness"],
    "carousel":       ["Consumer Purchase",       "Brand Awareness",         "Website Traffic"],
    "linkedin_post":  ["Distributor Acquisition", "Retailer Lead Gen",       "Brand Awareness"],
    "blog_post":      ["Website Traffic",         "Consumer Purchase",       "Brand Awareness"],
    "stories":        ["Consumer Purchase",       "Engagement Growth",       "Brand Awareness"],
    "yt_short":       ["Brand Awareness",         "Consumer Purchase",       "Website Traffic"],
}

# KPI targets and CTA copy per objective
_KPI: dict[str, dict] = {
    "Consumer Purchase": {
        "primary_cta":    "Buy at p3online.in — Rs 18 per cup",
        "success_metric": "link_clicks",
        "target":         500,
    },
    "Brand Awareness": {
        "primary_cta":    "Follow for daily coffee truth",
        "success_metric": "reach",
        "target":         50_000,
    },
    "Distributor Acquisition": {
        "primary_cta":    "DM us for distribution partnership",
        "success_metric": "dm_inquiries",
        "target":         10,
    },
    "Retailer Lead Gen": {
        "primary_cta":    "WhatsApp for bulk / retail pricing",
        "success_metric": "whatsapp_clicks",
        "target":         25,
    },
    "Website Traffic": {
        "primary_cta":    "Full article at p3online.in",
        "success_metric": "link_clicks",
        "target":         300,
    },
    "Engagement Growth": {
        "primary_cta":    "Tag someone who needs to see this",
        "success_metric": "shares",
        "target":         300,
    },
}


def assign_objective(content_type: str, day: int) -> dict:
    """
    Return objective metadata for one content piece.

    Returns:
        {
          "objective":      str,
          "primary_cta":    str,
          "success_metric": str,
          "target":         int,
        }
    """
    rotation   = _ROTATION.get(content_type, ["Brand Awareness"])
    objective: ObjectiveType = rotation[day % len(rotation)]
    kpis       = _KPI.get(objective, {})
    return {
        "objective":      objective,
        "primary_cta":    kpis.get("primary_cta", ""),
        "success_metric": kpis.get("success_metric", ""),
        "target":         kpis.get("target", 0),
    }


def assign_all(content: dict, day: int) -> dict:
    """
    Stamp business objectives onto every content piece in the output dict.
    Non-destructive: existing keys are preserved, objective keys are added.
    """
    out = dict(content)

    # Flat content types
    for key in ("instagram_post", "carousel", "linkedin_post", "blog_post", "stories", "yt_short"):
        if key in out and isinstance(out[key], dict):
            out[key] = {**out[key], **assign_objective(key, day)}

    # Reels array
    if "reels" in out and isinstance(out["reels"], list):
        reel_keys = ["reel_1", "reel_2"]
        out["reels"] = [
            {**reel, **assign_objective(reel_keys[i], day)}
            if i < len(reel_keys) else reel
            for i, reel in enumerate(out["reels"])
        ]

    return out
