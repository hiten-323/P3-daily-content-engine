"""
Scheduler name resolution.

The generate and publish entry points import what they need INSIDE the function
(deliberately — it keeps module import cheap and avoids cycles). That makes them
fragile under refactoring: moving a block of code between functions silently
leaves its imports behind, and the resulting NameError only appears when the
slot actually fires, at 00:30 UTC, in production.

That nearly shipped: extracting the generate body into its own function left
timed_step, RetryManager and assert_healthy imported in the wrapper while the
code using them moved away.

This walks each entry point's AST and asserts every free name resolves to a
local, an argument, an in-function import, a module global, or a builtin.
Cheap, static, and it catches the whole class rather than one instance.
"""
from __future__ import annotations

import ast
import builtins
import inspect


def _unresolved(fn_node: ast.AST, module) -> list[str]:
    bound: set[str] = set()
    used: set[str] = set()
    for node in ast.walk(fn_node):
        if isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.Name):
            (bound if isinstance(node.ctx, ast.Store) else used).add(node.id)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                bound.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                bound.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)          # except ... as e
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not fn_node:
            bound.add(node.name)
        elif isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
    known = set(dir(module)) | set(dir(builtins))
    return sorted(n for n in used - bound if n not in known)


def _check(module, *function_names: str) -> None:
    tree = ast.parse(inspect.getsource(module))
    by_name = {n.name: n for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for fname in function_names:
        assert fname in by_name, f"{module.__name__}.{fname} not found"
        missing = _unresolved(by_name[fname], module)
        assert not missing, (
            f"{module.__name__}.{fname} references names that resolve to nothing: "
            f"{missing} — an import was probably left behind in another function"
        )


def test_generate_entry_points_resolve_every_name() -> None:
    from content_generator.scheduler import daily
    _check(daily, "run_full_pipeline", "_run_generate_slot")


def test_publish_entry_points_resolve_every_name() -> None:
    from content_generator.scheduler import slots
    _check(slots, "run_publish_slot", "_execute_publish_slot", "_track", "_held")
