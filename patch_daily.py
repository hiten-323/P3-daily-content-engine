with open("content_generator/scheduler/daily.py", "r") as f:
    content = f.read()

old_logic = """    # 2. Emergency fallback — never miss a day
    if len(valid_assets) < MIN_REQUIRED_ASSETS:
        logger.warning(
            "[publish] Only %d valid assets (need %d) — activating emergency fallback: "
            "publishing top %d by score", len(valid_assets), MIN_REQUIRED_ASSETS, MIN_REQUIRED_ASSETS
        )
        valid_assets = _best_assets_by_score(content, MIN_REQUIRED_ASSETS)"""

new_logic = """    # 2. Emergency block — never publish unvalidated content
    if len(valid_assets) == 0:
        logger.error(
            "[publish] 0 valid assets — aborting publish! "
            "Missing a day is preferable to publishing unsafe content."
        )
        return {"skipped": True, "reason": "no_valid_assets",
                "published_platforms": [], "summary": "Publish aborted: 0 valid assets."}
    elif len(valid_assets) < MIN_REQUIRED_ASSETS:
        logger.warning(
            "[publish] Only %d valid assets (need %d) — proceeding with available validated assets.",
            len(valid_assets), MIN_REQUIRED_ASSETS
        )"""

content = content.replace(old_logic, new_logic)

with open("content_generator/scheduler/daily.py", "w") as f:
    f.write(content)
