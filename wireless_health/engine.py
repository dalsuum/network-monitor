"""Wireless Link Health Analysis Engine — main orchestrator.

Usage:
    engine = WirelessHealthEngine()
    result = engine.analyze(
        raw_metrics={'signal': -62, 'snr': 28, 'noise': -90, ...},
        vendor='Ligowave',
        model='DLB APC 5M-90 V3',
        device_name='Tower-01',
        device_id=5,
        ip_address='192.168.1.10',
        site='Main Tower',
    )
    print(result.to_dict())
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .types import LinkAnalysisResult, MetricEvaluation
from .evaluators import (
    evaluate_signal, evaluate_signal_aux, evaluate_signal_balance,
    evaluate_snr, evaluate_noise_floor, evaluate_ccq, evaluate_tx_power,
    evaluate_channel_width, evaluate_frequency, evaluate_data_rate,
    evaluate_mcs, evaluate_cpu, evaluate_temperature, evaluate_errors,
    evaluate_uptime, evaluate_ssid, evaluate_peer_mac, evaluate_wireless_mode,
)
from .scoring import calculate_overall_score, classify_health
from .recommendations import build_recommendations
from .insights import select_insights
from .vendors.registry import VendorRegistry


class WirelessHealthEngine:
    """Vendor-aware wireless link health analysis engine."""

    def __init__(self):
        self.registry = VendorRegistry()

    def analyze(
        self,
        raw_metrics: Dict[str, Any],
        vendor: str = 'Generic',
        model: str = '',
        device_name: str = 'Unknown',
        device_id: Optional[int] = None,
        ip_address: str = '',
        site: str = '',
    ) -> LinkAnalysisResult:
        """Run full health analysis on a set of normalized wireless metrics."""

        profile = self.registry.get_profile(vendor, model)
        weights = profile.get('scoring_weights') if profile else None

        m = raw_metrics
        signal      = m.get('signal')
        signal_aux  = m.get('signal_aux')
        snr         = m.get('snr')
        snr_aux     = m.get('snr_aux')
        noise       = m.get('noise')
        ccq         = m.get('ccq')
        tx_power    = m.get('tx_power')
        channel_w   = m.get('channel_width')
        frequency   = m.get('frequency')
        tx_rate     = m.get('tx_rate')
        rx_rate     = m.get('rx_rate')
        mcs         = m.get('mcs')
        cpu         = m.get('cpu')
        temperature = m.get('temperature')
        tx_errors   = m.get('tx_errors')
        rx_errors   = m.get('rx_errors')
        uptime      = m.get('uptime')
        ssid        = m.get('ssid')
        peer_mac    = m.get('peer_mac')
        wireless_mode = m.get('wireless_mode')

        metrics: Dict[str, MetricEvaluation] = {
            'signal':          evaluate_signal(signal),
            'signal_aux':      evaluate_signal_aux(signal_aux),
            'signal_balance':  evaluate_signal_balance(signal, signal_aux),
            'snr':             evaluate_snr(snr, 'Main'),
            'snr_aux':         evaluate_snr(snr_aux, 'Aux'),
            'noise':           evaluate_noise_floor(noise),
            'ccq':             evaluate_ccq(ccq),
            'tx_power':        evaluate_tx_power(tx_power, signal),
            'channel_width':   evaluate_channel_width(channel_w),
            'frequency':       evaluate_frequency(frequency),
            'data_rate':       evaluate_data_rate(tx_rate, rx_rate, channel_w),
            'mcs':             evaluate_mcs(mcs),
            'cpu':             evaluate_cpu(cpu),
            'temperature':     evaluate_temperature(temperature),
            'errors':          evaluate_errors(tx_errors, rx_errors),
            'uptime':          evaluate_uptime(uptime),
            'ssid':            evaluate_ssid(ssid),
            'peer_mac':        evaluate_peer_mac(peer_mac),
            'wireless_mode':   evaluate_wireless_mode(wireless_mode),
        }

        overall_score = calculate_overall_score(metrics, weights)
        classification, stars, health_color = classify_health(overall_score)
        key_issues, recommendations = build_recommendations(metrics)
        rf_insights = select_insights(metrics)

        # Build human-readable summary card
        summary = self._build_summary(metrics, overall_score, tx_rate, rx_rate)

        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        return LinkAnalysisResult(
            device_name=device_name,
            device_id=device_id,
            ip_address=ip_address,
            vendor=vendor,
            model=model,
            site=site,
            timestamp=ts,
            metrics=metrics,
            overall_score=overall_score,
            star_rating=stars,
            health_classification=classification,
            health_color=health_color,
            key_issues=key_issues,
            recommendations=recommendations,
            rf_insights=rf_insights,
            summary=summary,
            raw_metrics=raw_metrics,
        )

    @staticmethod
    def _build_summary(metrics, score, tx_rate, rx_rate) -> dict:
        def _q(key): return metrics[key].quality if metrics.get(key) and metrics[key].value is not None else 'N/A'

        # Estimate TCP throughput from data rate metric
        max_rate = max((tx_rate or 0), (rx_rate or 0))
        tcp_est = f'~{round(max_rate * 0.65)} Mbps' if max_rate else 'N/A'

        # Interference label from noise
        noise_m = metrics.get('noise')
        if noise_m and noise_m.value is not None:
            if noise_m.value > -85:
                interference = 'Severe'
            elif noise_m.value > -87:
                interference = 'High'
            elif noise_m.value > -90:
                interference = 'Moderate'
            else:
                interference = 'Low'
        else:
            interference = 'N/A'

        # Alignment label from signal_balance
        bal = metrics.get('signal_balance')
        if bal and bal.value is not None:
            if bal.value <= 2:
                alignment = 'Excellent'
            elif bal.value <= 5:
                alignment = 'Good'
            elif bal.value <= 8:
                alignment = 'Fair'
            else:
                alignment = 'Misaligned'
        else:
            alignment = 'N/A'

        return {
            'Signal':             _q('signal'),
            'SNR':                _q('snr'),
            'Noise':              _q('noise'),
            'Alignment':          alignment,
            'Interference':       interference,
            'Expected Throughput': tcp_est,
        }
