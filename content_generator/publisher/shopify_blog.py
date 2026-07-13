"""
Shopify Blog publisher — auto-posts the daily blog to p3online.in/blogs.

The blog is generated every day but had nowhere to go. This publishes it as a
Shopify article (SEO-friendly, drives organic search), attaching the day's
real-jar hero image and the meta description / tags the generator produced.

Requires (same secrets as revenue attribution, one extra scope):
  SHOPIFY_STORE_DOMAIN  your-store.myshopify.com
  SHOPIFY_ADMIN_TOKEN   Admin API token with write_content (+ read_content)

Degrades gracefully: not configured, no blog content, or an API error -> skip
without blocking the rest of the pipeline.
"""
from __future__ import annotations
import base64
import datetime
import glob as _glob
import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

_API_VERSION = "2024-10"
_TIMEOUT     = 40


def is_configured() -> bool:
    return bool(os.getenv("SHOPIFY_STORE_DOMAIN") and os.getenv("SHOPIFY_ADMIN_TOKEN"))


def _admin(path: str, method: str = "GET", body: dict | None = None) -> dict | None:
    domain = os.getenv("SHOPIFY_STORE_DOMAIN")
    token  = os.getenv("SHOPIFY_ADMIN_TOKEN")
    if not domain or not token:
        return None
    url = f"https://{domain}/admin/api/{_API_VERSION}/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    try:
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"X-Shopify-Access-Token": token,
                     "Content-Type": "application/json",
                     "User-Agent": "PurityBeans/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("[shopify_blog] %s %s failed: %s", method, path, e)
        return None


def _resolve_blog_id() -> str | None:
    """Use SHOPIFY_BLOG_ID if set, else the store's first blog."""
    explicit = os.getenv("SHOPIFY_BLOG_ID")
    if explicit:
        return explicit
    data = _admin("blogs.json")
    blogs = (data or {}).get("blogs") or []
    if blogs:
        return str(blogs[0].get("id"))
    logger.warning("[shopify_blog] No blog found on store — create one in Shopify admin")
    return None


def _hero_image_b64() -> str | None:
    """Today's composed real-jar image as base64 (Shopify article image)."""
    creative = os.getenv("CREATIVE_OUTPUT_DIR", os.path.join("output", "creative"))
    today = datetime.date.today().isoformat()
    for pat in (f"carousel_slide_1_*{today}.jpg", f"*{today}.jpg"):
        hits = sorted(_glob.glob(os.path.join(creative, pat)))
        if hits:
            try:
                with open(hits[0], "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                return None
    return None


def post_content(content: dict, day: int = 0) -> dict:
    """Publish today's blog as a Shopify article. Returns a result dict."""
    if not is_configured():
        logger.info("[shopify_blog] Not configured — set SHOPIFY_STORE_DOMAIN + "
                    "SHOPIFY_ADMIN_TOKEN (write_content)")
        return {"success": False, "error": "not_configured"}

    blog = content.get("blog_post") or {}
    title = str(blog.get("title") or "").strip()
    body  = str(blog.get("body_html") or "").strip()
    if not title or not body:
        logger.info("[shopify_blog] No blog content today — skipping")
        return {"success": False, "error": "no_blog_content"}

    blog_id = _resolve_blog_id()
    if not blog_id:
        return {"success": False, "error": "no_blog_id"}

    # Ensure intro + brand/CTA are present in the body
    intro = str(blog.get("intro") or "")
    if intro and intro not in body:
        body = f"<p>{intro}</p>\n{body}"
    website = os.getenv("WEBSITE_URL", "https://p3online.in")
    if "p3online.in" not in body:
        body += f'\n<p>Explore Purity Beans — 100% coffee, zero chicory: ' \
                f'<a href="{website}">{website}</a></p>'

    tags = blog.get("tags")
    if isinstance(tags, list):
        tags = ", ".join(str(t) for t in tags)

    article = {
        "title":        title,
        "author":       "Purity Beans",
        "body_html":    body,
        "tags":         str(tags or "coffee, instant coffee, purity beans"),
        "published":    True,
        "summary_html": str(blog.get("meta_description") or "")[:320],
    }
    if blog.get("slug"):
        article["handle"] = str(blog["slug"])
    hero = _hero_image_b64()
    if hero:
        article["image"] = {"attachment": hero, "alt": str(blog.get("image_alt") or title)}

    resp = _admin(f"blogs/{blog_id}/articles.json", method="POST", body={"article": article})
    art  = (resp or {}).get("article") or {}
    if art.get("id"):
        domain = os.getenv("SHOPIFY_STORE_DOMAIN", "")
        handle = art.get("handle", "")
        url = f"https://{domain}/blogs/news/{handle}" if handle else ""
        logger.info("[shopify_blog] Published article %s (%s)", art["id"], title)
        return {"success": True, "article_id": str(art["id"]), "url": url, "error": None}

    return {"success": False, "error": (resp or {}).get("errors", "publish_failed")}
