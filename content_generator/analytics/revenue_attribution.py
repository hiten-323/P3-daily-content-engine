"""
Shopify Revenue Attribution — the engine learns from money, not just likes.

Every morning (after insights_fetch) this module:
  1. Pulls yesterday's orders from the Shopify Admin API
  2. Splits them into Instagram-attributed vs other
     (referring_site / landing_site containing instagram.com, l.instagram.com,
      or a utm_source=instagram parameter)
  3. Attributes Instagram revenue to the posts published in the attribution
     window (same day + 1) and updates their learning-engine entries
  4. Snapshots daily revenue so the founder can see the trend

Honest attribution note: Instagram captions cannot carry clickable links, so
per-post attribution uses day-level matching (posts published in the window
share the day's Instagram-attributed revenue). It is directional, not exact —
but over months it reliably separates content that sells from content that
doesn't.

Required GitHub Secrets:
    SHOPIFY_STORE_DOMAIN  — e.g. "purity-beans.myshopify.com"
    SHOPIFY_ADMIN_TOKEN   — Admin API access token (read_orders scope)
      Create: Shopify admin -> Settings -> Apps -> Develop apps ->
      Create app -> Configure Admin API scopes -> read_orders -> Install
"""
from __future__ import annotations
import datetime
import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_LEARNING_DIR = os.getenv("LEARNING_DIR", os.path.join("output", "learning"))
_REV_PATH     = os.path.join(_LEARNING_DIR, "revenue_log.json")
_API_VERSION  = "2024-10"
_TIMEOUT      = 30

_IG_MARKERS = ("instagram.com", "l.instagram.com", "utm_source=instagram", "utm_source=ig")


def is_configured() -> bool:
    return bool(os.getenv("SHOPIFY_STORE_DOMAIN")) and bool(os.getenv("SHOPIFY_ADMIN_TOKEN"))


# ── Shopify API ───────────────────────────────────────────────────────────────

def _shopify_get(path: str, params: dict) -> dict | None:
    domain = os.getenv("SHOPIFY_STORE_DOMAIN")
    token  = os.getenv("SHOPIFY_ADMIN_TOKEN")
    if not domain or not token:
        return None
    url = f"https://{domain}/admin/api/{_API_VERSION}/{path}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={
            "X-Shopify-Access-Token": token,
            "User-Agent": "PurityBeans/1.0",
        })
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("[revenue] Shopify API failed (%s): %s", path, e)
        return None


def _fetch_orders_since(since: datetime.datetime) -> list[dict]:
    """Fetch paid orders created since the given time (max 250 — plenty daily)."""
    data = _shopify_get("orders.json", {
        "status":          "any",
        "financial_status": "paid",
        "created_at_min":  since.isoformat(),
        "limit":           250,
        "fields":          "id,created_at,total_price,landing_site,referring_site,"
                           "customer,source_name,discount_codes",
    })
    return (data or {}).get("orders", [])


def _is_instagram_order(order: dict) -> bool:
    haystack = " ".join([
        str(order.get("landing_site") or ""),
        str(order.get("referring_site") or ""),
        str(order.get("source_name") or ""),
    ]).lower()
    return any(m in haystack for m in _IG_MARKERS)


# ── Attribution ───────────────────────────────────────────────────────────────

def run_revenue_attribution(window_hours: int = 48) -> dict:
    """
    Main entry point — called by the daily pipeline.

    Returns {"orders": n, "revenue": x, "ig_orders": n, "ig_revenue": x,
             "attributed_posts": n} or a skip marker when not configured.
    """
    if not is_configured():
        logger.info("[revenue] Shopify not configured — skipping "
                    "(set SHOPIFY_STORE_DOMAIN + SHOPIFY_ADMIN_TOKEN)")
        return {"skipped": True}

    now    = datetime.datetime.now()
    since  = now - datetime.timedelta(hours=window_hours)
    orders = _fetch_orders_since(since)

    total_rev = sum(float(o.get("total_price") or 0) for o in orders)
    ig_orders = [o for o in orders if _is_instagram_order(o)]
    ig_rev    = sum(float(o.get("total_price") or 0) for o in ig_orders)
    returning = sum(
        1 for o in orders
        if (o.get("customer") or {}).get("orders_count", 1) and
           int((o.get("customer") or {}).get("orders_count", 1)) > 1
    )

    # Daily revenue snapshot (last 365 kept)
    snapshot = {
        "date":       now.date().isoformat(),
        "orders":     len(orders),
        "revenue":    round(total_rev, 2),
        "ig_orders":  len(ig_orders),
        "ig_revenue": round(ig_rev, 2),
        "aov":        round(total_rev / len(orders), 2) if orders else 0.0,
        "returning_customers": returning,
    }
    _append_snapshot(snapshot)

    # Attribute Instagram revenue to posts in the window
    attributed = _attribute_to_posts(ig_rev, len(ig_orders), since)

    logger.info(
        "[revenue] %d orders / Rs %.0f total | Instagram: %d orders / Rs %.0f "
        "-> attributed to %d post(s)",
        len(orders), total_rev, len(ig_orders), ig_rev, attributed,
    )
    return {**snapshot, "attributed_posts": attributed}


def _append_snapshot(snapshot: dict) -> None:
    os.makedirs(_LEARNING_DIR, exist_ok=True)
    entries = []
    if os.path.exists(_REV_PATH):
        try:
            with open(_REV_PATH, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []
    # One snapshot per date — replace same-day reruns
    entries = [e for e in entries if e.get("date") != snapshot["date"]]
    entries.append(snapshot)
    with open(_REV_PATH, "w", encoding="utf-8") as f:
        json.dump(entries[-365:], f, indent=2)


def _attribute_to_posts(ig_revenue: float, ig_orders: int, since: datetime.datetime) -> int:
    """
    Add revenue/orders to learning-engine entries for posts published in the
    window. Day-level attribution: revenue is split across the window's posts.
    """
    if ig_orders == 0:
        return 0
    try:
        from content_generator.core import learning_engine as le
    except Exception:
        return 0

    entries = le._load_log()
    in_window = []
    for e in entries:
        try:
            when = datetime.datetime.fromisoformat(str(e.get("posted_at", ""))[:19])
        except Exception:
            continue
        if when >= since:
            in_window.append(e)

    if not in_window:
        return 0

    per_post_rev    = ig_revenue / len(in_window)
    per_post_orders = ig_orders / len(in_window)
    for e in in_window:
        m = e.setdefault("metrics", {})
        m["revenue"] = round(m.get("revenue", 0) + per_post_rev, 2)
        m["orders"]  = round(m.get("orders", 0) + per_post_orders, 2)
    le._save_log(entries)
    return len(in_window)


def get_revenue_trend(days: int = 30) -> dict:
    """Revenue summary for founder report."""
    if not os.path.exists(_REV_PATH):
        return {}
    try:
        with open(_REV_PATH, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception:
        return {}
    recent = entries[-days:]
    if not recent:
        return {}
    return {
        "days":            len(recent),
        "total_revenue":   round(sum(e.get("revenue", 0) for e in recent), 2),
        "total_orders":    sum(e.get("orders", 0) for e in recent),
        "ig_revenue":      round(sum(e.get("ig_revenue", 0) for e in recent), 2),
        "ig_orders":       sum(e.get("ig_orders", 0) for e in recent),
        "avg_aov":         round(sum(e.get("aov", 0) for e in recent) / len(recent), 2),
    }
