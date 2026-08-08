with open("content_generator/core/learning_engine.py", "r") as f:
    content = f.read()

old_func = """def _engagement_score(m: dict) -> float:"""
new_func = """def _engagement_score(m: dict) -> tuple[float, float]:"""
content = content.replace(old_func, new_func)

with open("content_generator/core/learning_engine.py", "w") as f:
    f.write(content)
