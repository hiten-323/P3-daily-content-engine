# Setup: Shoppable Instagram Posts (Product Tagging)

Makes the engine's Instagram posts tappable — viewers tap a product tag and go
straight to the product page. Removes the "link in bio" detour.

The engine code is ready. These steps are the parts only you can do (Meta
requires manual approval — no API can bypass it).

## One-time setup

### 1. Connect your product catalog (easiest via Shopify)
- Shopify admin → **Settings → Apps and sales channels → add "Facebook & Instagram"** channel
- Connect it to your Meta Business account and the Facebook Page linked to your
  Instagram. This automatically syncs your Purity Beans products into a Meta
  catalog — no manual product entry.

### 2. Turn on Instagram Shopping
- Meta **Commerce Manager** (business.facebook.com/commerce) → your catalog →
  confirm products are approved (they must have image, price, description).
- Instagram app → **Settings → Business → Set up a shop / Shopping** → submit
  for review. Approval usually takes a few days.
- After approval: **Settings → Business → Shopping → select your catalog.**

### 3. Get the ID and add ONE GitHub Secret

Pick one:

- **Simple (one product for all posts):** in Commerce Manager open a product and
  copy its **Product ID**. Add secret `IG_PRODUCT_ID` = that id.
- **Smart (engine picks per post):** copy your **Catalog ID** (Commerce Manager →
  Settings). Add secret `IG_CATALOG_ID` = that id. The engine then matches
  bold / ultra blend / purista / purica in each post's text to the right product.

GitHub → repo → Settings → Secrets and variables → Actions → New secret.

## What happens after that

- Every engine image post that resolves a product becomes shoppable automatically.
- If the product can't be resolved or shopping isn't approved yet, posts publish
  normally without tags — nothing breaks.
- **Reels:** product tags on actual reel videos are added when you upload the
  reel in the Instagram app (tap "Tag products"). The engine tags the
  image/feed posts it publishes itself.

## Verify it worked

After the next run, open the posted image on Instagram — a shopping bag icon and
a tappable product tag should appear. In the run logs you'll see
`[product_tags] tagging post with product <id>`.
