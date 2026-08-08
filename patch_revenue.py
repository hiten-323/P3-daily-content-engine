import json

with open("content_generator/analytics/revenue_attribution.py", "r") as f:
    content = f.read()

import re
old_attribution_logic = """
    # Attribute Instagram revenue to posts in the window
    attributed = _attribute_to_posts(ig_rev, len(ig_orders), since)
"""
new_attribution_logic = """
    # Deduplicate by order ID so we don't attribute the same order multiple times
    attributed_orders_path = os.path.join(_LEARNING_DIR, "attributed_orders.json")
    attributed_ledger = []
    if os.path.exists(attributed_orders_path):
        try:
            with open(attributed_orders_path, "r", encoding="utf-8") as f:
                attributed_ledger = json.load(f)
        except Exception:
            pass

    ledger_set = set(attributed_ledger)
    new_ig_orders = [o for o in ig_orders if str(o.get("id")) not in ledger_set]
    new_ig_rev = sum(float(o.get("total_price") or 0) for o in new_ig_orders)

    # Add new orders to the ledger
    for o in new_ig_orders:
        ledger_set.add(str(o.get("id")))
    with open(attributed_orders_path, "w", encoding="utf-8") as f:
        json.dump(list(ledger_set)[-5000:], f)

    # Attribute Instagram revenue to posts in the window
    attributed = _attribute_to_posts(new_ig_rev, len(new_ig_orders), since)
"""

content = content.replace(old_attribution_logic, new_attribution_logic)

old_log = """
    logger.info(
        "[revenue] %d orders / Rs %.0f total | Instagram: %d orders / Rs %.0f "
        "-> attributed to %d post(s)",
        len(orders), total_rev, len(ig_orders), ig_rev, attributed,
    )
"""
new_log = """
    logger.info(
        "[revenue] %d orders / Rs %.0f total | Instagram: %d orders / Rs %.0f "
        "-> attributed to %d post(s)",
        len(orders), total_rev, len(new_ig_orders), new_ig_rev, attributed,
    )
"""
content = content.replace(old_log, new_log)

with open("content_generator/analytics/revenue_attribution.py", "w") as f:
    f.write(content)
