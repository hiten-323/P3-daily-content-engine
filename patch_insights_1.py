with open("content_generator/analytics/insights_fetcher.py", "r") as f:
    content = f.read()

import re

old_likes_logic = """    likes    = (fields or {}).get("like_count", 0) or 0
    comments = (fields or {}).get("comments_count", 0) or 0"""

new_likes_logic = """    likes    = fields.get("like_count") if fields else None
    comments = fields.get("comments_count") if fields else None"""

content = content.replace(old_likes_logic, new_likes_logic)

old_raw_logic = """                raw[item.get("name", "")] = values[0].get("value", 0) or 0"""
new_raw_logic = """                raw[item.get("name", "")] = values[0].get("value")"""

content = content.replace(old_raw_logic, new_raw_logic)

old_out_logic = """    out = {
        "views":          raw.get("views", raw.get("reach", 0)),
        "reach":          raw.get("reach", 0),
        "saves":          raw.get("saved", 0),
        "shares":         raw.get("shares", 0),
        "comments":       comments,
        "likes":          likes,
    }"""
new_out_logic = """    out = {
        "views":          raw.get("views"),
        "reach":          raw.get("reach"),
        "saves":          raw.get("saved"),
        "shares":         raw.get("shares"),
        "comments":       comments,
        "likes":          likes,
    }"""
content = content.replace(old_out_logic, new_out_logic)

with open("content_generator/analytics/insights_fetcher.py", "w") as f:
    f.write(content)
