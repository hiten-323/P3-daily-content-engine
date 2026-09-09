"""Single-source-of-truth safety guard for the GitHub engine blog path."""
from __future__ import annotations
import os


def assert_blog_disabled() -> None:
    """Raise unless the GitHub engine blog publisher was explicitly enabled."""
    if os.getenv("SHOPIFY_BLOG_ENABLED", "false").strip().lower() != "true":
        raise RuntimeError("GitHub blog publishing is disabled; Cowork is the production blog publisher")
