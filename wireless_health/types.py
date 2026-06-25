"""Data classes for wireless link health analysis."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MetricEvaluation:
    """Evaluation result for a single wireless metric."""
    name: str
    display_name: str
    value: Any
    unit: str
    quality: str        # Excellent / Very Good / Good / Fair / Poor / Critical
    score: float        # 0-100
    color: str          # green / lime / yellow / orange / red / grey
    reference_range: str
    explanation: str
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    historical_trend: Optional[str] = None  # up / down / stable

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'display_name': self.display_name,
            'value': self.value,
            'unit': self.unit,
            'quality': self.quality,
            'score': round(self.score, 1),
            'color': self.color,
            'reference_range': self.reference_range,
            'explanation': self.explanation,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'historical_trend': self.historical_trend,
        }


@dataclass
class RFInsight:
    """Educational RF insight entry."""
    topic: str
    title: str
    body: str

    def to_dict(self) -> dict:
        return {'topic': self.topic, 'title': self.title, 'body': self.body}


@dataclass
class FleetEntry:
    """Summary row for fleet dashboard display."""
    device_name: str
    device_id: Optional[int]
    ip_address: str
    site: str
    vendor: str
    model: str
    signal: Optional[float]
    snr: Optional[float]
    noise: Optional[float]
    overall_score: float
    health_classification: str
    health_color: str
    star_rating: str
    key_issues: List[str]
    timestamp: str

    def to_dict(self) -> dict:
        return {
            'device_name': self.device_name,
            'device_id': self.device_id,
            'ip_address': self.ip_address,
            'site': self.site,
            'vendor': self.vendor,
            'model': self.model,
            'signal': self.signal,
            'snr': self.snr,
            'noise': self.noise,
            'overall_score': round(self.overall_score, 1),
            'health_classification': self.health_classification,
            'health_color': self.health_color,
            'star_rating': self.star_rating,
            'key_issues': self.key_issues,
            'timestamp': self.timestamp,
        }


@dataclass
class LinkAnalysisResult:
    """Complete wireless link health analysis result."""
    device_name: str
    device_id: Optional[int]
    ip_address: str
    vendor: str
    model: str
    site: str
    timestamp: str
    metrics: Dict[str, MetricEvaluation]
    overall_score: float
    star_rating: str
    health_classification: str
    health_color: str
    key_issues: List[str]
    recommendations: List[str]
    rf_insights: List[RFInsight]
    summary: Dict[str, Any]
    raw_metrics: Dict[str, Any]

    def to_fleet_entry(self) -> FleetEntry:
        return FleetEntry(
            device_name=self.device_name,
            device_id=self.device_id,
            ip_address=self.ip_address,
            site=self.site,
            vendor=self.vendor,
            model=self.model,
            signal=self.raw_metrics.get('signal'),
            snr=self.raw_metrics.get('snr'),
            noise=self.raw_metrics.get('noise'),
            overall_score=self.overall_score,
            health_classification=self.health_classification,
            health_color=self.health_color,
            star_rating=self.star_rating,
            key_issues=self.key_issues,
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict:
        return {
            'device_name': self.device_name,
            'device_id': self.device_id,
            'ip_address': self.ip_address,
            'vendor': self.vendor,
            'model': self.model,
            'site': self.site,
            'timestamp': self.timestamp,
            'overall_score': round(self.overall_score, 1),
            'star_rating': self.star_rating,
            'health_classification': self.health_classification,
            'health_color': self.health_color,
            'key_issues': self.key_issues,
            'recommendations': self.recommendations,
            'rf_insights': [i.to_dict() for i in self.rf_insights],
            'summary': self.summary,
            'metrics': {k: v.to_dict() for k, v in self.metrics.items() if v.value is not None},
        }
