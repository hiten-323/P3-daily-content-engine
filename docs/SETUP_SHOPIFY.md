# Setup: One Shopify token unlocks BOTH blog publishing AND revenue learning

The engine reuses a single Admin API token for two things. Add the scopes you
want; each degrades gracefully if its scope is missing.

## Create the token (once)
Shopify admin → Settings → Apps and sales channels → Develop apps →
Create an app → Configure Admin API scopes → tick:

- **write_content** + **read_content**  → daily blog auto-publishes to p3online.in/blogs (SEO/organic search)
- **read_orders**                       → revenue attribution + EVPOI come alive (the learning loop learns from money, not just likes)

Install → copy the `shpat_...` token.

## Add GitHub secrets
- `SHOPIFY_STORE_DOMAIN` = your-store.myshopify.com
- `SHOPIFY_ADMIN_TOKEN`  = the shpat_ token
- (optional) `SHOPIFY_BLOG_ID` = specific blog; defaults to the store's first blog

## Why read_orders matters (from the strategic review)
Without order data, EVPOI stays ₹0 and the weekly brief can't tell which content
made money — the learning loop is starved. Adding read_orders lets the engine
attribute Instagram-driven revenue to posts (first-touch via Shopify customer
journeys) and rank content by profit, not vanity metrics.

Nothing breaks if you skip a scope — the matching feature just stays dormant.
