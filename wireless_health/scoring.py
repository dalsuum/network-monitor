"""Weighted score aggregation and health classification."""

from typing import Dict, Optional
from .types import MetricEvaluation


# Default scoring weights (sum = 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    'signal':          0.25,
    'snr':             0.25,
    'noise':           0.20,
    'signal_balance':  0.10,
    'tx_power':        0.05,
    'channel_width':   0.05,
    'errors':          0.05,
    'cpu':             0.025,
    'temperature':     0.025,
}


def calculate_overall_score(
    metrics: Dict[str, MetricEvaluation],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate weighted overall health score (0-100).

    Only metrics with actual values contribute. Remaining weight is
    redistributed proportionally across contributing metrics.
    """
    w = weights or DEFAULT_WEIGHTS

    contributing: Dict[str, float] = {}
    for key, weight in w.items():
        m = metrics.get(key)
        if m and m.value is not None and m.score > 0:
            contributing[key] = weight

    if not contributing:
        return 0.0

    total_weight = sum(contributing.values())
    score = 0.0
    for key, weight in contributing.items():
        score += metrics[key].score * (weight / total_weight)

    return round(min(max(score, 0), 100), 2)


def classify_health(score: float) -> tuple:
    """Return (classification, star_rating, color) for a numeric score."""
    if score >= 95:
        return 'Excellent',  '★★★★★', 'green'
    elif score >= 90:
        return 'Very Good',  '★★★★☆', 'lime'
    elif score >= 80:
        return 'Good',       '★★★★',  'lime'
    elif score >= 70:
        return 'Fair',       '★★★',   'yellow'
    elif score >= 60:
        return 'Poor',       '★★',    'orange'
    else:
        return 'Critical',   '★',     'red'
