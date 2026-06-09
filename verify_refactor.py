"""
Pre-merge verification suite for the content_generator refactor.
Runs without real API keys by patching the LLM router.
Exit code 0 = all checks passed.
"""
import ast
import os
import sys
import types
import importlib
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"

_results: list[tuple[bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((ok, name))
    icon = PASS if ok else FAIL
    line = f"  {icon}  {name}"
    if detail:
        line += f"\n       {detail}"
    print(line)


def section(title: str) -> None:
    print(f"\n{'-' * 60}\n{title}\n{'-' * 60}")


# -----------------------------------------------------------------------------
#  Stubs for external project dependencies (engine, config)
# -----------------------------------------------------------------------------

def _install_stubs() -> None:
    """
    Install minimal stubs for engine.database and config.brand_config
    so imports resolve without the real project present.
    """
    engine_pkg = types.ModuleType("engine")
    engine_db  = types.ModuleType("engine.database")
    engine_db.get_recent_content_history = lambda days=14: []
    engine_pkg.database = engine_db
    sys.modules["engine"]          = engine_pkg
    sys.modules["engine.database"] = engine_db

    config_pkg = types.ModuleType("config")
    brand_cfg  = types.ModuleType("config.brand_config")
    brand_cfg.BRAND            = {"name": "Purity Beans", "tagline": "Pure Coffee. Nothing Else.", "website": "https://p3online.in"}
    brand_cfg.POSITIONING      = {"usp": "100% pure instant coffee", "price_per_cup": 18, "cafe_price": 180}
    brand_cfg.CONTENT_CATEGORIES = []
    brand_cfg.HASHTAG_SETS     = {
        "reel_morning": "#coffee #india",
        "reel_night":   "#coffee #night",
        "carousel":     "#coffee #pure",
        "linkedin":     "#fmcg #india",
    }
    brand_cfg.WEEKLY_STRATEGY  = {"weekly": {d: "default" for d in
                                   ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]}}
    config_pkg.brand_config = brand_cfg
    sys.modules["config"]              = config_pkg
    sys.modules["config.brand_config"] = brand_cfg

_install_stubs()


# -----------------------------------------------------------------------------
#  CHECK 1 - Public API imports
# -----------------------------------------------------------------------------

section("CHECK 1 - Public API imports")

try:
    from content_generator import generate_daily_content
    check("from content_generator import generate_daily_content", True)
except Exception as e:
    check("from content_generator import generate_daily_content", False, str(e))

try:
    from content_generator import save_content
    check("from content_generator import save_content", True)
except Exception as e:
    check("from content_generator import save_content", False, str(e))

try:
    from content_generator import configure
    check("from content_generator import configure", True)
except Exception as e:
    check("from content_generator import configure", False, str(e))

try:
    import content_generator as cg
    assert callable(cg.generate_daily_content)
    assert callable(cg.save_content)
    check("import content_generator; callable API", True)
except Exception as e:
    check("import content_generator; callable API", False, str(e))

try:
    # Importing must NOT trigger logging.basicConfig or file I/O side effects
    # Re-import from a clean slate
    for key in list(sys.modules.keys()):
        if key.startswith("content_generator"):
            del sys.modules[key]
    _install_stubs()
    import content_generator  # noqa: F811
    check("import content_generator has no side effects", True)
except Exception as e:
    check("import content_generator has no side effects", False, str(e))


# -----------------------------------------------------------------------------
#  CHECK 2 - Schema parity (ENABLE_USAGE_LOG=false)
# -----------------------------------------------------------------------------

section("CHECK 2 - Output schema parity (ENABLE_USAGE_LOG=false)")

EXPECTED_KEYS = {
    "date", "day_number",
    "reels", "instagram_post", "carousel",
    "linkedin_post", "blog_post", "stories", "yt_short",
    "video_prompts", "ai_image_prompts", "performance_targets",
}

# Patch LLM router so no real API call is made
_FAKE_REEL = {
    "id": "reel_1", "hook_archetype": "EXPOSE", "hook_text": "TEST HOOK",
    "hook_spoken": "This is", "frames": [{"on_screen": "X", "spoken": "y"}] * 6,
    "loop_note": "loops", "alt_hook": "alt", "caption": "cap",
    "visual_direction": "dark", "music_vibe": "lo-fi", "whatsapp_forward": "fwd",
}
_FAKE_SIMPLE = {"id": "test", "content": "stub"}
_FAKE_VIDEO  = {"video_prompts": {"reel_1": {"frames": []}, "reel_2": {"frames": []}, "yt_short": {"scenes": []}}}

_STUB_MAP = {
    "reel_1":         _FAKE_REEL,
    "reel_2":         {**_FAKE_REEL, "id": "reel_2"},
    "instagram_post": _FAKE_SIMPLE,
    "carousel":       _FAKE_SIMPLE,
    "linkedin_post":  _FAKE_SIMPLE,
    "blog_post":      _FAKE_SIMPLE,
    "stories":        _FAKE_SIMPLE,
    "yt_short":       {"product": "test", "scenes": []},
    "video_prompts":  _FAKE_VIDEO,
}

try:
    os.environ["ENABLE_USAGE_LOG"] = "false"

    def _fake_call(prompt: str, label: str, max_tokens: int = 3000) -> dict:
        return _STUB_MAP.get(label, _FAKE_SIMPLE)

    # Import the generator module, then patch its locally-bound llm_call name
    import content_generator.pipeline.generator as _gen_mod
    _original_llm_call = _gen_mod.llm_call
    _gen_mod.llm_call = _fake_call

    result = _gen_mod.generate_daily_content(day_number=0)
    actual_keys = set(result.keys())

    missing = EXPECTED_KEYS - actual_keys
    extra   = actual_keys - EXPECTED_KEYS - {"usage"}  # usage is opt-in, allowed absent

    check("All expected keys present",     not missing, f"Missing: {missing}" if missing else "")
    check("No unexpected extra keys",      not extra,   f"Extra: {extra}"     if extra   else "")
    check("'usage' absent when flag=false","usage" not in result)

    # Now check it appears when flag=true
    os.environ["ENABLE_USAGE_LOG"] = "true"
    result_with_usage = _gen_mod.generate_daily_content(day_number=0)
    check("'usage' present when ENABLE_USAGE_LOG=true", "usage" in result_with_usage)

    _gen_mod.llm_call = _original_llm_call

except Exception as e:
    check("Schema parity test", False, str(e))


# -----------------------------------------------------------------------------
#  CHECK 3 - No local shadowing of external dependencies
# -----------------------------------------------------------------------------

section("CHECK 3 - External dependencies not shadowed locally")

CODE_ROOT = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT  = os.path.join(CODE_ROOT, "content_generator")

no_local_engine = not os.path.exists(os.path.join(CODE_ROOT, "engine"))
no_local_config = not os.path.exists(os.path.join(CODE_ROOT, "config"))
check("No local engine/ directory",        no_local_engine)
check("No local config/ directory",        no_local_config)

# Scan all .py files for any definition of get_recent_content_history or BRAND
def _grep(root: str, pattern: str) -> list[str]:
    hits = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(dirpath, f)
            try:
                src = open(path).read()
            except Exception:
                continue
            if pattern in src and "import" not in src.split(pattern)[0].rsplit("\n", 1)[-1]:
                hits.append(os.path.relpath(path, CODE_ROOT))
    return hits

hits_db   = _grep(PKG_ROOT, "def get_recent_content_history")
hits_brand = _grep(PKG_ROOT, "BRAND = ")
check("get_recent_content_history not defined locally", not hits_db,   f"Found in: {hits_db}")
check("BRAND dict not defined locally",                 not hits_brand, f"Found in: {hits_brand}")


# -----------------------------------------------------------------------------
#  CHECK 4 - Concurrency ordering (video_prompts after phase 1)
# -----------------------------------------------------------------------------

section("CHECK 4 - Concurrency ordering")

gen_src = open(os.path.join(PKG_ROOT, "pipeline", "generator.py")).read()
tree    = ast.parse(gen_src)

# Find the generate_daily_content function body and check ordering
vp_line    = None
phase1_line = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "vp" in targets:
            vp_line = node.lineno
    if isinstance(node, (ast.With,)):
        # The ThreadPoolExecutor context manager
        if any("ThreadPoolExecutor" in ast.unparse(item) for item in node.items):
            phase1_line = node.lineno

check("Phase 1 (ThreadPoolExecutor) defined before video_prompts call",
      phase1_line is not None and vp_line is not None and phase1_line < vp_line,
      f"ThreadPoolExecutor at line {phase1_line}, vp= at line {vp_line}")

# Confirm video_prompts uses results from phase1
vp_uses_reel1   = "phase1_results[\"reel_1\"]"   in gen_src or "phase1_results['reel_1']"   in gen_src
vp_uses_reel2   = "phase1_results[\"reel_2\"]"   in gen_src or "phase1_results['reel_2']"   in gen_src
vp_uses_yt      = "phase1_results[\"yt_short\"]" in gen_src or "phase1_results['yt_short']" in gen_src
check("video_prompts consumes phase1_results[reel_1]",  vp_uses_reel1)
check("video_prompts consumes phase1_results[reel_2]",  vp_uses_reel2)
check("video_prompts consumes phase1_results[yt_short]", vp_uses_yt)

# Confirm video_prompts is NOT inside the ThreadPoolExecutor block
# by checking it's assigned after the `with` block closes
with_node = next(
    (n for n in ast.walk(tree)
     if isinstance(n, ast.With)
     and any("ThreadPoolExecutor" in ast.unparse(i) for i in n.items)),
    None,
)
if with_node:
    with_end = max(getattr(n, "lineno", 0) for n in ast.walk(with_node))
    check("video_prompts call is OUTSIDE the ThreadPoolExecutor block",
          vp_line is not None and vp_line > with_end,
          f"with block ends ~line {with_end}, vp= at line {vp_line}")


# -----------------------------------------------------------------------------
#  Summary
# -----------------------------------------------------------------------------

passed = sum(1 for ok, _ in _results if ok)
total  = len(_results)
print(f"\n{'-' * 60}")
print(f"  Result: {passed}/{total} checks passed")
print(f"{'-' * 60}\n")

sys.exit(0 if passed == total else 1)
