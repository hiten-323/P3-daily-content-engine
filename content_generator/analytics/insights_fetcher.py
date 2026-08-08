
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
from config.api_versions import META_GRAPH_BASE
import datetime
import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_GRAPH_API     = META_GRAPH_BASE
_LEARNING_DIR  = os.getenv("LEARNING_DIR", os.path.join("output", "learning"))
_POSTS_PATH    = os.path.join(_LEARNING_DIR, "published_posts.json")
_TIMEOUT       = 30

# Wait at least this long after posting before pulling metrics —
# a post needs time to accumulate meaningful numbers.
MIN_AGE_HOURS = 20

# How many runs to keep retrying a post whose insights call fails before
# abandoning it. Abandoning writes NO performance row — an unmeasured post must
# leave no trace in the learning log rather than a fabricated zero one.
MAX_FETCH_ATTEMPTS = 5

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
    kpi_at_creation: str = "",
    policy_version: str = "",
    scroller_mechanism: str = "",
    scroller_state: str = "",
    psychology_frame: str = "",
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
        "kpi_at_creation": kpi_at_creation,
        "policy_version": policy_version,
        "scroller_mechanism": scroller_mechanism,
        "scroller_state": scroller_state,
        "psychology_frame": psychology_frame,
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
    likes    = fields.get("like_count") if fields else None
    comments = fields.get("comments_count") if fields else None
    is_reel  = str((fields or {}).get("media_product_type", "")).upper() == "REELS"

    # 2. Insight metrics — reels support watch-time metrics, feed/carousel do not.
    #    ig_reels_avg_watch_time is in MILLISECONDS; ig_reels_video_view_total_time
    #    is total ms across all views. Both are reels-only and 400 on other types.
    metric_sets = (
        (["reach", "saved", "shares", "total_interactions", "views",
          "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"] if is_reel
         else ["reach", "saved", "shares", "total_interactions"]),
        (["reach", "saved", "shares", "views"] if is_reel
         else ["reach", "saved", "shares"]),
        ["reach", "saved"],
        ["reach"],
    )
    raw = {}
    for metrics in metric_sets:
        data = _graph_get(f"{media_id}/insights", {"metric": ",".join(metrics)})
        if data and "data" in data:
            for item in data["data"]:
                values = item.get("values") or [{}]
                raw[item.get("name", "")] = values[0].get("value")
            break

    # A failed insights call must NOT be written as measured zeros. This
    # previously returned reach/saves/shares = 0 whenever the endpoint errored,
    # the caller marked the post recorded, and it was never retried — so 50
    # posts entered the learning log as "reached nobody, saved by nobody" when
    # in truth they were never measured at all. Every downstream system (reward,
    # viral memory, never-repeat list) then trained on that fiction.
    #
    # `raw` empty means the endpoint gave us nothing. A genuine zero still
    # arrives as a present key with value 0, so real zeros are preserved.
    if not raw:
        logger.warning(
            "[insights] No insight metrics returned for %s — not recording. "
            "Zeros here would be fabricated, not measured.", media_id)
        return None

    out = {
        "views":          raw.get("views"),
        "reach":          raw.get("reach"),
        "saves":          raw.get("saved"),
        "shares":         raw.get("shares"),
        "comments":       comments,
        "likes":          likes,
    }
    # Watch time — reels only, reported in milliseconds. Omit the keys entirely
    # on non-reels rather than writing 0: a carousel has no watch time, and a
    # zero would drag the average as if it were a reel nobody watched.
    avg_ms = raw.get("ig_reels_avg_watch_time")
    if avg_ms:
        out["avg_view_duration_s"] = round(float(avg_ms) / 1000.0, 2)
    total_ms = raw.get("ig_reels_video_view_total_time")
    if total_ms:
        out["watch_time_s"] = round(float(total_ms) / 1000.0, 2)
    return out


def _fetch_account_insights() -> dict:
    """
    Account-level daily insights: profile views and website (bio link) clicks.

    These are NOT available per media — Instagram reports them for the account
    only. They are attributed across the day's posts the same way follows_gained
    already is. That attribution is an approximation and is labelled as such;
    true per-post link CTR needs a link-in-bio router handing out per-post URLs.
    """
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    if not account_id:
        return {}
    data = _graph_get(f"{account_id}/insights",
                      {"metric": "profile_views,website_clicks", "period": "day"})
    # `.get("value")` NOT `.get("value", 0) or 0` — the same unknown-vs-zero rule
    # the media path already follows. A missing value means Instagram did not
    # report it; writing 0 would claim we measured zero profile views, which then
    # enters the learning log as fact. None stays absent, and the caller below
    # only attributes a signal it actually received.
    out = {}
    for item in ((data or {}).get("data") or []):
        values = item.get("values") or [{}]
        val = values[0].get("value")
        if val is not None:
            out[item.get("name", "")] = val
    return out


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

    posts     = _load_posts()
    now       = datetime.datetime.now()
    recorded  = 0
    pending   = 0
    abandoned = 0

    # Follower snapshot: compare with last snapshot to estimate follows gained
    follower_count = _fetch_follower_count()
    acct = _fetch_account_insights()   # profile_views, website_clicks (account-level)
    
    # Store account daily metrics independently
    try:
        acct_path = os.path.join(_LEARNING_DIR, "account_metrics.json")
        acct_log = []
        if os.path.exists(acct_path):
            with open(acct_path, "r", encoding="utf-8") as f:
                acct_log = json.load(f)
        acct_log.append({
            "date": now.isoformat(timespec="seconds"),
            "follower_count": follower_count,
            "profile_views": acct.get("profile_views"),
            "website_clicks": acct.get("website_clicks")
        })
        os.makedirs(_LEARNING_DIR, exist_ok=True)
        with open(acct_path, "w", encoding="utf-8") as f:
            json.dump(acct_log[-365:], f, indent=2)
    except Exception as e:
        logger.debug("[insights] Failed to write account metrics: %s", e)
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
            # Retry on a later run instead of inventing numbers. Give up after
            # MAX_FETCH_ATTEMPTS so a deleted or permission-denied media object
            # isn't probed forever — and abandon it WITHOUT writing a row, so
            # the learning log contains only real measurements.
            attempts = int(post.get("fetch_attempts", 0)) + 1
            post["fetch_attempts"] = attempts
            if attempts >= MAX_FETCH_ATTEMPTS:
                post["insights_recorded"] = True
                post["insights_failed"]   = True
                abandoned += 1
                logger.warning(
                    "[insights] Giving up on %s after %d attempts — never "
                    "measured, no row written", post.get("asset_id"), attempts)
            else:
                pending += 1
            continue
        # Account-level signals attributed evenly across the day's posts. These
        # are approximations by construction — Instagram reports them for the
        # account, not the media — but an even split across the day's posts is
        # far better than dropping three primary KPIs entirely.
        # DO NOT divide account-level metrics and attribute them to individual posts.
        pass

        record_performance(
            asset_id    = post["asset_id"],
            track       = post.get("track", "brand"),
            hook        = post.get("hook", ""),
            topic       = post.get("topic", ""),
            format_used = post.get("format", ""),
            posted_at   = post.get("published_at", ""),
            metrics     = metrics,
            notes       = "auto-recorded by insights_fetcher",
            kpi_at_creation=post.get("kpi_at_creation", ""),
            policy_version=post.get("policy_version", ""),
            scroller_mechanism=post.get("scroller_mechanism", ""),
            scroller_state=post.get("scroller_state", ""),
            psychology_frame=post.get("psychology_frame", "")
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
        "[insights] Done — %d recorded, %d pending, %d abandoned unmeasured, followers=%s",
        recorded, pending, abandoned, follower_count,
    )
    if abandoned:
        logger.warning(
            "[insights] %d post(s) were never measured. Check that the token has "
            "instagram_manage_insights and that the account is a Business/Creator "
            "account — insights are unavailable on personal accounts.", abandoned)
    return {"recorded": recorded, "pending": pending, "abandoned": abandoned,
            "follower_count": follower_count}
