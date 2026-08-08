with open("content_generator/analytics/insights_fetcher.py", "r") as f:
    content = f.read()

old_logic = """        # account, not the media — but an even split across the day's posts is
        # far better than dropping three primary KPIs entirely.
        if due:
            if follows_gained_total:
                metrics["follows_gained"] = follows_gained_total // len(due)
            if acct.get("profile_views"):
                metrics["profile_visits"] = int(acct["profile_views"]) // len(due)
            if acct.get("website_clicks"):
                metrics["website_clicks"] = int(acct["website_clicks"]) // len(due)"""

new_logic = """        # account, not the media — but an even split across the day's posts is
        # far better than dropping three primary KPIs entirely.
        # DO NOT divide account-level metrics and attribute them to individual posts.
        pass"""

content = content.replace(old_logic, new_logic)

account_logic_old = """    # Follower snapshot: compare with last snapshot to estimate follows gained
    follower_count = _fetch_follower_count()
    acct = _fetch_account_insights()   # profile_views, website_clicks (account-level)"""

account_logic_new = """    # Follower snapshot: compare with last snapshot to estimate follows gained
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
        logger.debug("[insights] Failed to write account metrics: %s", e)"""

content = content.replace(account_logic_old, account_logic_new)

with open("content_generator/analytics/insights_fetcher.py", "w") as f:
    f.write(content)
