"""
Founder Policy Engine — the founder edits founder_policies.yaml, never prompts.

Every pipeline step reads policy through this module. Missing file or keys fall
back to safe defaults, so the engine never breaks on a bad edit.

    from content_generator.core.founder_policy import policy
    if policy().auto_publish: ...
    brief_bias = policy().strategy_bias()
"""
from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)

def _policy_path() -> str:
    return os.getenv("FOUNDER_POLICY_FILE", "founder_policies.yaml")


_DEFAULTS = {
    "target_kpi": "followers",
    "brand_voice": {"premium": True, "aggressive_sales": False, "educational": True},
    "priority_segments": ["general"],
    "auto_publish": True,
    "max_daily_posts": {"instagram": 3, "facebook": 2, "linkedin": 1, "youtube": 1},
    "legal_risk_threshold": 0.25,
    "require_real_jar": True,
    "active_campaign_override": "",
}


class FounderPolicy:
    def __init__(self, data: dict):
        self._d = data

    def __getattr__(self, name):
        if name in self._d:
            return self._d[name]
        if name in _DEFAULTS:
            return _DEFAULTS[name]
        raise AttributeError(name)

    def get(self, key, default=None):
        return self._d.get(key, _DEFAULTS.get(key, default))

    # ── Derived helpers (what the pipeline actually consumes) ────────────────

    def strategy_bias(self) -> str:
        """A prompt-injectable sentence encoding the founder's policy intent."""
        kpi = self.get("target_kpi", "followers")
        voice = self.get("brand_voice", {})
        segs = ", ".join(self.get("priority_segments", ["general"]))
        campaign = self.get("active_campaign_override", "")

        kpi_line = {
            "followers":  "Optimize for FOLLOWER GROWTH — shareable, non-salesy value.",
            "engagement": "Optimize for ENGAGEMENT — comments, saves, conversation.",
            "revenue":    "Optimize for REVENUE — route qualified attention to purchase.",
        }.get(kpi, "Optimize for FOLLOWER GROWTH.")

        bits = [f"FOUNDER POLICY: {kpi_line}"]
        tone = []
        if voice.get("premium", True):
            tone.append("premium/editorial")
        if voice.get("educational", True):
            tone.append("educational")
        tone.append("assertive sales" if voice.get("aggressive_sales") else "value-first (soft CTAs)")
        bits.append("Voice: " + ", ".join(tone) + ".")
        bits.append(f"Prioritize speaking to: {segs}.")
        if campaign:
            bits.append(f"Active campaign focus: {campaign}.")
        return " ".join(bits)

    def as_dict(self) -> dict:
        return dict(self._d)


_cached: FounderPolicy | None = None


def load_policy(force: bool = False) -> FounderPolicy:
    global _cached
    if _cached is not None and not force:
        return _cached
    data = dict(_DEFAULTS)
    path = _policy_path()
    try:
        if os.path.exists(path):
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                # shallow-merge so partial files keep defaults for missing keys
                for k, v in loaded.items():
                    data[k] = v
            logger.info("[policy] Loaded founder policies (target_kpi=%s, auto_publish=%s)",
                        data.get("target_kpi"), data.get("auto_publish"))
        else:
            logger.info("[policy] No founder_policies.yaml — using safe defaults")
    except Exception as e:
        logger.warning("[policy] Could not read %s (%s) — using defaults", path, e)
    _cached = FounderPolicy(data)
    return _cached


def policy() -> FounderPolicy:
    return load_policy()
