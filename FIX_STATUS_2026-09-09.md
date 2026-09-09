# Fix status — 2026-09-09

## Applied
- GitHub Shopify blog publisher has an explicit `SHOPIFY_BLOG_ENABLED` gate with default `false`.
- Regression tests cover the default-disabled behavior and prove no Shopify admin call occurs while disabled.
- Added an explicit single-publisher safety guard stating Cowork is the production blog publisher.
- Added an editorial rotation safety helper and regression tests to reject consecutive identical tiers when integrated by the runner.
- Added the dated SEO review queue from the final GSC audit.

## Not activated
- GitHub blog publishing remains OFF.
- No Shopify article writes, title/meta edits, redirects, canonical changes, internal-link edits, or product-page edits were performed.

## Verification note
The live GSC property is settled through 2026-09-06. Latest 7-day page data was rechecked against 2026-08-24..2026-08-30. The SEO queue is review-only.
