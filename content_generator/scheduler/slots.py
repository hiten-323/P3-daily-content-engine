"""
Time-slot publishing — different content at its algorithm-optimal time.

The engine's own platform knowledge says:
  - Feed posts / carousels: 7-9 AM IST (commute + morning coffee scroll)
  - Reels: 7-10 PM IST (evening leisure scroll = highest watch time)

So instead of publishing everything at 06:00 IST, the day is split:

  SLOT       UTC cron    IST     WHAT HAPPENS
  generate   30 0 * * *  06:00   Full pipeline: insights, revenue, generate,
                                 editorial, images, LinkedIn/blog/YouTube.
                                 Instagram + Facebook HELD for their windows.
  morning    30 4 * * *  10:00   IG carousel + FB mirror (owner-chosen time)
  evening    30 16 * * * 22:00   IG reel-style post + FB mirror
                                 (owner-chosen time)

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
    forced = os.getenv("FORCE_SLOT")
    if forced in ("generate", "morning", "evening"):
        logger.info("[slots] Current slot forced by FORCE_SLOT env: %s", forced)
        return forced

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

    # Respect the founder policy dry-run switch here too — the publish slots
    # must honor auto_publish=false, not just the generate slot.
    try:
        from content_generator.core.founder_policy import policy
        if not policy().get("auto_publish", True):
            logger.warning("[slots] auto_publish=false — %s slot generates nothing "
                           "and posts nothing (dry run)", slot)
            return {"_skipped": True, "slot": slot, "reason": "auto_publish_disabled"}
    except Exception as _e:
        logger.debug("[slots] optional step failed: %s", _e)

    lock = RunLock(lock_path=os.path.join("output", f".running_{slot}"))
    lock.__enter__()
    if lock.already_ran:
        logger.info("[slots] %s slot already ran today — skipping", slot)
        return {"_skipped": True, "slot": slot, "reason": "already_ran"}

    content = _load_todays_content()
    if not content:
        logger.info("[slots] Content file not found. Triggering daily pipeline to generate content first...")
        try:
            from content_generator.scheduler.daily import run_full_pipeline
            content = run_full_pipeline()
        except Exception as e:
            logger.error("[slots] Failed to generate content via daily pipeline: %s", e)
            return {"slot": slot, "success": False, "error": f"generation_failed: {e}"}

        if not content or not isinstance(content, dict) or content.get("_skipped"):
            logger.error("[slots] Content generation returned empty or skipped status")
            return {"slot": slot, "success": False, "error": "generation_skipped_or_failed"}

    day = content.get("day_number", 0)

    if slot == "morning":
        # Carousel / feed post + Instagram Story — 10:00 IST (owner-chosen)
        from content_generator.publisher.instagram import post_content, post_story
        result = post_content(content, day=day)
        piece = content.get("carousel") or {}
        _track(result, content, slot, piece)
        _mirror_to_facebook(content, day, slot)
        # Instagram Story (image, 24h) — separate method, same slot
        try:
            story_res = post_story(content, day=day)
            logger.info("[slots] instagram story: %s", story_res.get("success"))
            result["story"] = story_res
        except Exception as e:
            logger.warning("[slots] instagram story failed: %s", e)
        logger.info("[slots] morning publish: %s", result.get("success"))
        return {"slot": slot, **result}

    if slot == "evening":
        # Reel video (free motion reel) with image fallback — 22:00 IST
        from content_generator.publisher.instagram import (
            _post_single_image, _assemble_caption, is_configured, post_reel_video,
        )
        if not is_configured():
            return {"slot": slot, "success": False, "error": "not_configured"}

        reels = content.get("reels") or []
        reel  = reels[0] if reels and isinstance(reels[0], dict) else {}
        if not reel:
            return {"slot": slot, "success": False, "error": "no_reel"}

        body = str(reel.get("caption") or reel.get("hook_text") or "").strip()
        cta  = str(reel.get("cta") or "").strip()
        if cta and cta.lower() not in body.lower():
            body = f"{body}\n\n{cta}"
        caption = _assemble_caption(body, reel, day)

        # 1. Try an actual REEL VIDEO — HERO video first (founder-produced,
        #    the format that actually spreads), else the free motion reel.
        result = None
        try:
            from content_generator.publisher.video_host import upload_video, is_configured as vhost_ok
            hero = _find_hero_video()
            if hero:
                video_path, is_hero = hero, True
                logger.info("[slots] using HERO video: %s", os.path.basename(hero))
            else:
                from content_generator.creative.reel_video import build_reel_video
                video_path, is_hero = build_reel_video(reel, day), False
            if video_path and vhost_ok():
                video_url = upload_video(video_path)
                if video_url:
                    result = post_reel_video(video_url, caption)
                    if result.get("success"):
                        logger.info("[slots] evening published as %s REEL VIDEO",
                                    "HERO" if is_hero else "motion")
                        if is_hero:
                            _mark_hero_posted(video_path)
        except Exception as e:
            logger.warning("[slots] reel video path failed (%s) — falling back to image", e)

        # 2. Fallback: reel-style single image
        if not result or not result.get("success"):
            image = _find_reel_thumbnail()
            if not image:
                return {"slot": slot, "success": False, "error": "no_image"}
            result = _post_single_image(image, caption)
            _mirror_to_facebook(content, day, slot, image=image, message=caption)
        else:
            _mirror_to_facebook(content, day, slot, message=caption)

        result["hashtags_used"] = " ".join(w for w in caption.split() if w.startswith("#"))
        _track(result, content, slot, reel)
        logger.info("[slots] evening publish: %s", result.get("success"))
        return {"slot": slot, **result}

    return {"slot": slot, "success": False, "error": f"unknown_slot_{slot}"}


_HERO_DIR    = os.getenv("HERO_VIDEO_DIR", "hero_videos")
_HERO_POSTED = os.path.join(os.getenv("LEARNING_DIR", os.path.join("output", "learning")),
                            "hero_posted.json")


def _find_hero_video() -> str | None:
    """
    Return the oldest founder-produced hero video not yet posted.
    Drop .mp4/.mov files in hero_videos/ and the prime evening slot uses them
    first (the format that actually spreads) — slideshow is only the fallback.
    """
    if not os.path.isdir(_HERO_DIR):
        return None
    posted = set()
    if os.path.exists(_HERO_POSTED):
        try:
            posted = set(json.load(open(_HERO_POSTED, encoding="utf-8")))
        except Exception:
            posted = set()
    vids = []
    for ext in ("*.mp4", "*.mov", "*.MP4", "*.MOV"):
        vids += _glob.glob(os.path.join(_HERO_DIR, ext))
    fresh = [v for v in vids if os.path.basename(v) not in posted]
    if not fresh:
        return None
    return sorted(fresh, key=os.path.getmtime)[0]   # oldest first


def _mark_hero_posted(path: str) -> None:
    try:
        posted = []
        if os.path.exists(_HERO_POSTED):
            posted = json.load(open(_HERO_POSTED, encoding="utf-8"))
        posted.append(os.path.basename(path))
        os.makedirs(os.path.dirname(_HERO_POSTED), exist_ok=True)
        json.dump(posted[-500:], open(_HERO_POSTED, "w", encoding="utf-8"), indent=2)
    except Exception as e:
        logger.debug("[slots] could not mark hero posted: %s", e)


def _mirror_to_facebook(content: dict, day: int, slot: str,
                        image: str | None = None, message: str | None = None) -> None:
    """Facebook copies Instagram's timing: same slot, same image, same text."""
    try:
        from content_generator.publisher.facebook import post_content as fb_post
        r = fb_post(content, day=day, preferred_image=image, message_override=message)
        logger.info("[slots] facebook mirror (%s): %s", slot, r.get("success"))
    except Exception as e:
        logger.warning("[slots] facebook mirror failed (%s): %s", slot, e)
