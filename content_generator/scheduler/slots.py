"""
Time-slot publishing — different content at its algorithm-optimal time.

The engine's own platform knowledge says:
  - Feed posts / carousels: 7-9 AM IST (commute + morning coffee scroll)
  - Reels: 7-10 PM IST (evening leisure scroll = highest watch time)

So instead of publishing everything at 06:00 IST, the day is split:

  SLOT       UTC cron    IST     WHAT HAPPENS
  generate   30 0 * * *  06:00   Full pipeline: insights, revenue, generate,
                                 editorial, images, LinkedIn/blog/YouTube.
                                 Instagram is HELD for its optimal windows.
  morning    30 2 * * *  08:00   Instagram carousel/feed post (7-9 AM window)
  evening    30 14 * * * 20:00   Instagram reel-style single image with the
                                 reel's caption (7-10 PM window)

Content + images are committed to the repo by the generate run, so the
later stateless CI runs can load and publish them.

Controlled by ENABLE_TIMED_SLOTS=true (set in the workflow). When unset,
legacy behavior (publish everything at 06:00) is preserved.
"""
from __future__ import annotations
import datetime
import glob as _glob
import json
import logging
import os

logger = logging.getLogger(__name__)


def slots_enabled() -> bool:
    return os.getenv("ENABLE_TIMED_SLOTS", "false").lower() == "true"


def get_current_slot(now_utc: datetime.datetime = None) -> str:
    """
    Determine the slot from the current UTC hour.
      < 02:00 UTC  -> generate  (06:00 IST run)
      02-12 UTC    -> morning   (08:00 IST run)
      >= 12 UTC    -> evening   (20:00 IST run)
    """
    now_utc = now_utc or datetime.datetime.utcnow()
    h = now_utc.hour
    if h < 2:
        return "generate"
    if h < 12:
        return "morning"
    return "evening"


def _load_todays_content() -> dict | None:
    """Load the content JSON saved by this morning's generate run."""
    date_str = datetime.date.today().isoformat()
    path = os.path.join("output", f"content_{date_str}.json")
    if not os.path.exists(path):
        logger.error("[slots] No content file for today (%s) — generate run missing?", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("[slots] Could not read content file: %s", e)
        return None


def _find_reel_thumbnail() -> str | None:
    """Find today's reel thumbnail image on disk."""
    creative_dir = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))
    date_str = datetime.date.today().isoformat()
    for pattern in (f"reel_1_thumb_*_{date_str}.jpg", f"reel_1*{date_str}.jpg",
                    f"reel_hook_*_{date_str}.jpg"):
        matches = sorted(_glob.glob(os.path.join(creative_dir, pattern)))
        if matches:
            return matches[0]
    return None


def _track(result: dict, content: dict, slot: str, piece: dict) -> None:
    """Register the published media for tomorrow's insights fetch."""
    try:
        if result.get("success") and result.get("media_id"):
            from content_generator.analytics.insights_fetcher import track_published_post
            track_published_post(
                media_id    = result["media_id"],
                asset_id    = f"instagram_{slot}_day{content.get('day_number', 0)}",
                track       = "brand",
                hook        = str(piece.get("hook_text") or piece.get("title") or "")[:120],
                topic       = str(piece.get("save_mechanic") or piece.get("hook_archetype") or "")[:120],
                format_used = slot,
                hashtags    = str(result.get("hashtags_used") or ""),
            )
    except Exception as e:
        logger.warning("[slots] tracking failed: %s", e)


def run_publish_slot(slot: str) -> dict:
    """
    Execute a publish-only slot (morning or evening).
    Loads this morning's generated content and posts the slot's asset.
    """
    from content_generator.scheduler.run_lock import RunLock

    lock = RunLock(lock_path=os.path.join("output", f".running_{slot}"))
    lock.__enter__()
    if lock.already_ran:
        logger.info("[slots] %s slot already ran today — skipping", slot)
        return {"_skipped": True, "slot": slot, "reason": "already_ran"}

    content = _load_todays_content()
    if not content:
        return {"slot": slot, "success": False, "error": "no_content_file"}

    day = content.get("day_number", 0)

    if slot == "morning":
        # Carousel / feed post — 7-9 AM IST window
        from content_generator.publisher.instagram import post_content
        result = post_content(content, day=day)
        piece = content.get("carousel") or {}
        _track(result, content, slot, piece)
        logger.info("[slots] morning publish: %s", result.get("success"))
        return {"slot": slot, **result}

    if slot == "evening":
        # Reel-style single image with the reel's caption — 7-10 PM IST window
        from content_generator.publisher.instagram import (
            _post_single_image, _assemble_caption, is_configured,
        )
        if not is_configured():
            return {"slot": slot, "success": False, "error": "not_configured"}

        reels = content.get("reels") or []
        reel  = reels[0] if reels and isinstance(reels[0], dict) else {}
        if not reel:
            return {"slot": slot, "success": False, "error": "no_reel"}

        image = _find_reel_thumbnail()
        if not image:
            logger.warning("[slots] no reel thumbnail found — skipping evening post")
            return {"slot": slot, "success": False, "error": "no_image"}

        body = str(reel.get("caption") or reel.get("hook_text") or "").strip()
        cta  = str(reel.get("cta") or "").strip()
        if cta and cta.lower() not in body.lower():
            body = f"{body}\n\n{cta}"
        caption = _assemble_caption(body, reel, day)

        result = _post_single_image(image, caption)
        result["hashtags_used"] = " ".join(w for w in caption.split() if w.startswith("#"))
        _track(result, content, slot, reel)
        logger.info("[slots] evening publish: %s", result.get("success"))
        return {"slot": slot, **result}

    return {"slot": slot, "success": False, "error": f"unknown_slot_{slot}"}
