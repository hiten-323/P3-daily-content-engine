with open("content_generator/core/reward.py", "r") as f:
    content = f.read()

old_score = """def score(metrics: dict, kpi: str | None = None) -> float:
    \"\"\"Reward for one post's metrics under the active KPI profile.\"\"\"
    w = get_weights(kpi)
    m = metrics or {}
    sum_main = float(sum(float(m.get(k, 0) or 0) * weight for k, weight in w.items() if k not in ["revenue", "orders"]))
    revenue_score = float((m.get("revenue") or 0) * w.get("revenue", 0) + (m.get("orders") or 0) * w.get("orders", 0))
    # Lexicographic/gated optimization: revenue strictly outranks engagement
    return float(sum_main + revenue_score * 10000)"""

new_score = """def score(metrics: dict, kpi: str | None = None) -> tuple[float, float]:
    \"\"\"Reward for one post's metrics under the active KPI profile.\"\"\"
    w = get_weights(kpi)
    m = metrics or {}
    revenue_score = float((m.get("revenue") or 0) * w.get("revenue", 0) + (m.get("orders") or 0) * w.get("orders", 0))
    sum_main = float(sum(float(m.get(k, 0) or 0) * weight for k, weight in w.items() if k not in ["revenue", "orders"]))
    # Lexicographic/gated optimization: revenue strictly outranks engagement
    return (revenue_score, sum_main)"""

content = content.replace(old_score, new_score)

with open("content_generator/core/reward.py", "w") as f:
    f.write(content)
