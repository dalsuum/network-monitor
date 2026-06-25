"""Aggregate recommendation engine.

Collects per-metric recommendations, deduplicates, prioritises by severity,
and generates a clean ordered list of actionable items.
"""

from typing import Dict, List
from .types import MetricEvaluation


# Priority order for metric-level issues (highest impact first)
_PRIORITY_ORDER = [
    'signal', 'snr', 'noise', 'signal_balance', 'ccq',
    'errors', 'cpu', 'temperature', 'tx_power',
    'channel_width', 'frequency', 'data_rate', 'mcs',
]


def build_recommendations(metrics: Dict[str, MetricEvaluation]) -> tuple:
    """Return (key_issues, recommendations) sorted by priority."""
    key_issues: List[str] = []
    recommendations: List[str] = []
    seen_recs = set()

    for metric_key in _PRIORITY_ORDER:
        m = metrics.get(metric_key)
        if not m or m.value is None:
            continue
        for issue in m.issues:
            if issue not in key_issues:
                key_issues.append(issue)
        for rec in m.recommendations:
            norm = rec.lower().strip()
            if norm not in seen_recs:
                seen_recs.add(norm)
                recommendations.append(rec)

    # Collect remaining metrics not in priority list
    for key, m in metrics.items():
        if key in _PRIORITY_ORDER or m.value is None:
            continue
        for issue in m.issues:
            if issue not in key_issues:
                key_issues.append(issue)
        for rec in m.recommendations:
            norm = rec.lower().strip()
            if norm not in seen_recs:
                seen_recs.add(norm)
                recommendations.append(rec)

    if not key_issues and not recommendations:
        recommendations.append('No immediate action required — link health is good.')

    return key_issues, recommendations
