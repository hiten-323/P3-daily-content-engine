with open("content_generator/core/learning_engine.py", "r") as f:
    content = f.read()

old_weighted_score = """def _weighted_score(entry: dict) -> float:
    \"\"\"
    Reward adjusted for recency AND objective compatibility — what ranking uses.
    Recent evidence collected under the current objective dominates.
    \"\"\"
    return (_engagement_score(entry.get("metrics", {}))
            * _recency_factor(entry)
            * _objective_factor(entry))"""

new_weighted_score = """def _weighted_score(entry: dict) -> tuple[float, float]:
    \"\"\"
    Reward adjusted for recency AND objective compatibility — what ranking uses.
    Recent evidence collected under the current objective dominates.
    \"\"\"
    engagement = _engagement_score(entry.get("metrics", {}))
    factor = _recency_factor(entry) * _objective_factor(entry)
    return (engagement[0] * factor, engagement[1] * factor)"""

content = content.replace(old_weighted_score, new_weighted_score)

old_analyze = """    winners = [e for e, s in scored if s >= median and s > 0]
    # Only condemn a post by the yardstick it was BUILT for. Content created
    # under a previous objective may score low under today's weights without
    # having actually failed — retiring it would import a bias from an
    # abandoned strategy. Cross-objective posts can inform winners (at a
    # discount) but are never added to the never-repeat list.
    failed = [e for e, s in scored
              if s <= median * 0.5 and _objective_factor(e) == 1.0]"""

# the median of tuples can be handled, but comparing s > 0 needs a tuple logic: s > (0,0) or similar.
new_analyze = """    winners = [e for e, s in scored if s >= median and s > (0, 0)]
    # Only condemn a post by the yardstick it was BUILT for. Content created
    # under a previous objective may score low under today's weights without
    # having actually failed — retiring it would import a bias from an
    # abandoned strategy. Cross-objective posts can inform winners (at a
    # discount) but are never added to the never-repeat list.
    failed = [e for e, s in scored
              if s <= (median[0] * 0.5, median[1] * 0.5) and _objective_factor(e) == 1.0]"""

content = content.replace(old_analyze, new_analyze)

old_analyze_return = """        return {"winners": [], "failed": [], "median_score": 0.0, "count": 0}"""
new_analyze_return = """        return {"winners": [], "failed": [], "median_score": (0.0, 0.0), "count": 0}"""
content = content.replace(old_analyze_return, new_analyze_return)

with open("content_generator/core/learning_engine.py", "w") as f:
    f.write(content)
