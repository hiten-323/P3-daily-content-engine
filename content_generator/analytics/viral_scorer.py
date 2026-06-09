"""
Viral score formula for ranking content performance.

Score range: 0–100
Weights: views 20%, retention 25%, shares 30%, saves 20%, comments 5%

Normalization ceilings (Indian FMCG Instagram benchmarks):
  views:     100,000
  retention: 100 %
  shares:    1,000
  saves:     2,000
  comments:  500
"""

_CEILINGS = {
    "views":     100_000,
    "retention": 100.0,
    "shares":    1_000,
    "saves":     2_000,
    "comments":  500,
}

_WEIGHTS = {
    "views":     0.20,
    "retention": 0.25,
    "shares":    0.30,
    "saves":     0.20,
    "comments":  0.05,
}


def compute_viral_score(
    views: int = 0,
    retention: float = 0.0,
    shares: int = 0,
    saves: int = 0,
    comments: int = 0,
) -> float:
    """Return a 0–100 viral score. Higher = more viral."""
    raw = {
        "views":     views,
        "retention": retention,
        "shares":    shares,
        "saves":     saves,
        "comments":  comments,
    }
    total = sum(
        min(max(raw[k], 0) / _CEILINGS[k], 1.0) * _WEIGHTS[k]
        for k in _WEIGHTS
    )
    return round(total * 100, 1)


def score_batch(metrics_list: list[dict]) -> list[dict]:
    """Add viral_score to each metrics dict and return sorted descending."""
    for m in metrics_list:
        m["viral_score"] = compute_viral_score(
            views=m.get("views", 0),
            retention=m.get("retention", 0.0),
            shares=m.get("shares", 0),
            saves=m.get("saves", 0),
            comments=m.get("comments", 0),
        )
    return sorted(metrics_list, key=lambda x: x["viral_score"], reverse=True)
