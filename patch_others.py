with open("content_generator/creative/audio_director.py", "r") as f:
    content = f.read()

content = content.replace("scores.setdefault(cat, []).append(_engagement_score(e[\"metrics\"]))", "scores.setdefault(cat, []).append(_engagement_score(e[\"metrics\"])[1])")

with open("content_generator/creative/audio_director.py", "w") as f:
    f.write(content)

with open("content_generator/assets/lead_magnets.py", "r") as f:
    content = f.read()

content = content.replace("scores.setdefault(kw, []).append(_engagement_score(e[\"metrics\"]))", "scores.setdefault(kw, []).append(_engagement_score(e[\"metrics\"])[1])")

with open("content_generator/assets/lead_magnets.py", "w") as f:
    f.write(content)
