"""
Instagram Insights Fetcher — closes the learning loop automatically.

Flow (runs inside the daily pipeline, zero manual work):
  1. When the publisher posts successfully, track_published_post() stores the
     media_id + creative metadata (hook, topic, format) in
     output/learning/published_posts.json
  2. Next morning, fetch_pending_insights() pulls metrics for every post that
     is >= MIN_AGE_HOURS old and not yet recorded, via the same Graph API
     credentials used for publishing (INSTAGRAM_ACCESS_TOKEN).
  3. Each result is fed into learning_engine.record_performance(), which
     powers the PATTERNS THAT WORKED / FAILED block in every future prompt.

No new secrets needed — reuses INSTAGRAM_ACCOUNT_ID + INSTAGRAM_ACCESS_TOKEN.
"""
from __future__ import annotations
import datetime
import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_GRAPH_API     = "https://graph.facebook.com/v18.0"
_LEARNING_DIR  = os.getenv("LEARNING_DIR", os.path.join("output", "learning"))
_POSTS_PATH    = os.path.join(_LEARNING_DIR, "published_posts.json")
_TIMEOUT       = 30

# Wait at least this long after posting before pulling metrics —
# a post needs time to accumulate meaningful numbers.
MIN_AGE_HOURS = 20

# Graph API media insights metrics (v18+). 'views' replaced impressions/plays.
_MEDIA_METRICS = "views,reach,saved,shares,comments,likes,total_interactions"


# ── Tracking published posts ──────────────────────────────────────────────────

def _load_posts() -> list[dict]:
    if not os.path.exists(_POSTS_PATH):
        return []
    try:
        with open(_POSTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("[insights] Could not read published posts: %s", e)
        return []


def _save_posts(posts: list[dict]) -> None:
    os.makedirs(_LEARNING_DIR, exist_ok=True)
    with open(_POSTS_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def track_published_post(
    media_id: str,
    asset_id: str,
    track: str = "brand",
    hook: str = "",
    topic: str = "",
    format_used: str = "",
    hashtags: str = "",
) -> None:
    """Record a successfully published post so its insights can be fetched later."""
    if not media_id:
        return
    posts = _load_posts()
    if any(p.get("media_id") == media_id for p in posts):
        return  # already tracked
    posts.append({
        "media_id":    media_id,
        "asset_id":    asset_id,
        "track":       track,
        "hook":        hook,
        "topic":       topic,
        "format":      format_used,
        "hashtags":    hashtags,
        "published_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "insights_recorded": False,
    })
    _save_posts(posts)
    logger.info("[insights] Tracking published post %s (%s)", media_id, asset_id)


# ── Fetching insights ─────────────────────────────────────────────────────────

def _graph_get(path: str, params: dict) -> dict | None:
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        return None
    params = {**params, "access_token": token}
    url = f"{_GRAPH_API}/{path}?{urllib.parse.urlencode(params)}"
    try:
        req  = urllib.request.Request(url, headers={"User-Agent": "PurityBeans/1.0"})
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("[insights] Graph API call failed (%s): %s", path, e)
        return None


def _fetch_media_insights(media_id: str) -> dict | None:
    """
    Fetch insight metrics for one media object.

    Fix for the HTTP 400 storm: likes/comments are media FIELDS, not insight
    metrics, and 'views' is only valid on reels/video — mixing them into the
    /insights `metric` param 400s for image/carousel media. So we:
      1. read like_count/comments_count from the media object fields (always valid)
      2. request only valid insight metrics, and progressively narrow on failure
    Returns a metrics dict, or None if the object is truly unreadable.
    """
    # 1. Engagement counts via media FIELDS (valid for every media type)
    fields = _graph_get(media_id, {"fields": "like_count,comments_count,media_product_type"})
    likes    = (fields or {}).get("like_count", 0) or 0
    comments = (fields or {}).get("comments_count", 0) or 0
    is_reel  = str((fields or {}).get("media_product_type", "")).upper() == "REELS"

    # 2. Insight metrics — reels support 'views', feed/carousel do not
    metric_sets = (
        (["reach", "saved", "shares", "total_interactions", "views"] if is_reel
         else ["reach", "saved", "shares", "total_interactions"]),
        ["reach", "saved"],
        ["reach"],
    )
    raw = {}
    for metrics in metric_sets:
        data = _graph_get(f"{media_id}/insights", {"metric": ",".join(metrics)})
        if data and "data" in data:
            for item in data["data"]:
                values = item.get("values") or [{}]
                raw[item.get("name", "")] = values[0].get("value", 0) or 0
            break

    if not raw and fields is None:
        return None   # object genuinely unreadable (deleted / permission)

    return {
        "views":          raw.get("views", raw.get("reach", 0)),
        "reach":          raw.get("reach", 0),
        "saves":          raw.get("saved", 0),
        "shares":         raw.get("shares", 0),
        "comments":       comments,
        "likes":          likes,
        "profile_visits": 0,
    }


def _fetch_follower_count() -> int | None:
    """Current follower count — used to compute follows gained between runs."""
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    if not account_id:
        return None
    data = _graph_get(account_id, {"fields": "followers_count"})
    if data and "followers_count" in data:
        return int(data["followers_count"])
    return None


def fetch_pending_insights() -> dict:
    """
    Main entry point — called by the daily pipeline.

    For every tracked post that is old enough and not yet recorded:
    fetch insights and feed learning_engine.record_performance().
    Also snapshots follower count so growth is visible over time.

    Returns {"recorded": int, "pending": int, "follower_count": int|None}
    """
    if not os.getenv("INSTAGRAM_ACCESS_TOKEN"):
        logger.info("[insights] Instagram not configured — skipping insights fetch")
        return {"recorded": 0, "pending": 0, "follower_count": None}

    from content_generator.core.learning_engine import record_performance

    posts    = _load_posts()
    now      = datetime.datetime.now()
    recorded = 0
    pending  = 0

    # Follower snapshot: compare with last snapshot to estimate follows gained
    follower_count = _fetch_follower_count()
    prev_count     = None
    snap_path      = os.path.join(_LEARNING_DIR, "follower_snapshots.json")
    snapshots      = []
    if os.path.exists(snap_path):
        try:
            with open(snap_path, "r", encoding="utf-8") as f:
                snapshots = json.load(f)
            if snapshots:
                prev_count = snapshots[-1].get("count")
        except Exception:
            snapshots = []
    if follower_count is not None:
        snapshots.append({"date": now.isoformat(timespec="seconds"), "count": follower_count})
        os.makedirs(_LEARNING_DIR, exist_ok=True)
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(snapshots[-365:], f, indent=2)

    follows_gained_total = (
        max(0, follower_count - prev_count)
        if follower_count is not None and prev_count is not None else 0
    )

    due = []
    for post in posts:
        if post.get("insights_recorded"):
            continue
        try:
            published = datetime.datetime.fromisoformat(post["published_at"])
        except Exception:
            published = now
        if (now - published).total_seconds() < MIN_AGE_HOURS * 3600:
            pending += 1
            continue
        due.append(post)

    for post in due:
        metrics = _fetch_media_insights(post["media_id"])
        if metrics is None:
            pending += 1
            continue
        # Attribute the day's follower gain evenly across the day's posts
        if follows_gained_total and due:
            metrics["follows_gained"] = follows_gained_total // len(due)

        record_performance(
            asset_id    = post["asset_id"],
            track       = post.get("track", "brand"),
            hook        = post.get("hook", ""),
            topic       = post.get("topic", ""),
            format_used = post.get("format", ""),
            posted_at   = post.get("published_at", ""),
            metrics     = metrics,
            notes       = "auto-recorded by insights_fetcher",
        )
        post["insights_recorded"] = True
        recorded += 1
        logger.info("[insights] Recorded %s: %s", post["asset_id"], metrics)

        # Feed the adaptive hashtag bank — each tag earns/loses standing
        try:
            from content_generator.analytics.hashtag_bank import record_post_hashtags
            if post.get("hashtags"):
                record_post_hashtags(post["hashtags"], metrics)
        except Exception as e:
            logger.debug("[insights] hashtag attribution skipped: %s", e)

    _save_posts(posts)
    logger.info(
        "[insights] Done — %d recorded, %d pending, followers=%s",
        recorded, pending, follower_count,
    )
    return {"recorded": recorded, "pending": pending, "follower_count": follower_count}
