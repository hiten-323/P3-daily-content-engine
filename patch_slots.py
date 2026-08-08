with open("content_generator/scheduler/slots.py", "r") as f:
    content = f.read()

old_logic = """        reels = content.get("reels") or []
        reel  = reels[0] if reels and isinstance(reels[0], dict) else {}"""

new_logic = """        reel = content.get("growth_reel") or {}
        if not reel:
            reels = content.get("reels") or []
            reel  = reels[0] if reels and isinstance(reels[0], dict) else {}"""

content = content.replace(old_logic, new_logic)

with open("content_generator/scheduler/slots.py", "w") as f:
    f.write(content)
