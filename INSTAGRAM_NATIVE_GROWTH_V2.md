# Instagram Native Growth V2 — 2026-07-24

Implemented after visual audit of the live Instagram grid.

## Fixed at architecture level
- Removes the old assumption that every asset must be a black/moody poster.
- Adds shared mobile-first Instagram-native rules.
- Adds a hard QA module for leaked `SLIDE 1:` labels, bad glyphs, excessive canvas copy, and incomplete Reel plans.
- Missing Reel audio is no longer described as acceptable; auto-published Reels should have an embedded licensed/local track,
  otherwise route to a manual Instagram music step rather than silently publishing a silent Reel.
- Growth objective now explicitly follows non-follower reach -> watch -> completion -> shares/saves -> profile -> follow -> website.
- Adds creative pillar rotation guidance to stop repetitive anti-chicory creatives.
- Preserves exact Purity Beans packaging whenever the product is shown.

## Important operational limitation
Instagram's API does not provide a compliant way for this engine to attach arbitrary trending in-app Instagram music.
For automated publishing, use music you have rights to in `music_library/`. For trending Instagram-library audio, generate a manual
posting instruction and add the sound in Instagram.

## Zero-view diagnostic
Creative quality alone cannot explain literal zero views. Publisher/analytics should verify media processing/status and retrieve the
correct insight metrics after publish. Do not use zero-view rows as creative-learning evidence until publication/measurement is verified.
