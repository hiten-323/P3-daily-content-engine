"""Safety helpers for editorial rotation.

The daily engine should not repeatedly emit the same intent family. This helper
is intentionally additive: callers can use it to reject a candidate tier when
it matches the previous run, without changing the existing content catalog.
"""
from __future__ import annotations


def avoid_consecutive_tier(candidate: str, previous: str | None) -> bool:
    """Return True when candidate is safe to use after previous."""
    if not previous:
        return True
    return candidate.strip().lower() != previous.strip().lower()
