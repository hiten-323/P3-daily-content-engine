import os

from content_generator.publisher import shopify_blog


def test_shopify_blog_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SHOPIFY_BLOG_ENABLED", raising=False)
    assert shopify_blog.blog_enabled() is False


def test_shopify_blog_requires_explicit_enable(monkeypatch):
    monkeypatch.setenv("SHOPIFY_BLOG_ENABLED", "false")
    assert shopify_blog.blog_enabled() is False
    monkeypatch.setenv("SHOPIFY_BLOG_ENABLED", "true")
    assert shopify_blog.blog_enabled() is True


def test_disabled_blog_never_reaches_shopify_write(monkeypatch):
    monkeypatch.delenv("SHOPIFY_BLOG_ENABLED", raising=False)
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "example.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ADMIN_TOKEN", "test-token")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Shopify admin API must not be called while blog publishing is disabled")

    monkeypatch.setattr(shopify_blog, "_admin", fail_if_called)
    result = shopify_blog.post_content({"blog_post": {"title": "x", "body_html": "y"}})
    assert result == {"success": False, "error": "blog_disabled"}
