"""Per-metric evaluation functions for wireless link health analysis.

Each evaluator accepts raw metric values and returns a MetricEvaluation
with quality rating, score, color, and actionable recommendations.
"""

from typing import Optional
from .types import MetricEvaluation


def _quality_color(quality: str) -> str:
    """Map quality label to CSS color token."""
    return {
        'Outstanding': 'green',
        'Excellent': 'green',
        'Very Good': 'lime',
        'Good': 'lime',
        'Stable': 'lime',
        'Normal': 'green',
        'Moderate': 'yellow',
        'Fair': 'yellow',
        'Weak': 'orange',
        'High': 'orange',
        'Noisy': 'orange',
        'Poor': 'orange',
        'Very Low': 'yellow',
        'Very High': 'orange',
        'Excessive': 'red',
        'Hot': 'orange',
        'Critical': 'red',
        'Severe Interference': 'red',
        'Antenna Misalignment Warning': 'red',
    }.get(quality, 'yellow')


# ---------------------------------------------------------------------------
# Signal Level
# ---------------------------------------------------------------------------

def evaluate_signal(value: Optional[float]) -> MetricEvaluation:
    name = 'signal'
    display_name = 'Signal Level (Main)'
    unit = 'dBm'
    ref = '-30~-45 Excellent | -46~-55 Very Good | -56~-65 Good | -66~-70 Fair | -71~-75 Weak | -76~-80 Poor | <-80 Critical'
    expl = (
        'Received signal power from the remote radio. Higher (less negative) values indicate '
        'stronger signal. Optimal range is -30 to -65 dBm for reliable high-throughput links. '
        'Signal below -75 dBm causes significant retransmissions and throughput loss.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value >= -45:
        quality, score = 'Excellent', 100
    elif value >= -55:
        quality, score = 'Very Good', 95
    elif value >= -65:
        quality, score = 'Good', 90
    elif value >= -70:
        quality, score = 'Fair', 75
    elif value >= -75:
        quality, score = 'Weak', 60
    elif value >= -80:
        quality, score = 'Poor', 40
    else:
        quality, score = 'Critical', 10

    issues, recs = [], []
    if value < -80:
        issues.append(f'Signal critically low at {value} dBm — link at risk of dropping')
        recs += [
            'Realign antenna for optimal line-of-sight',
            'Increase antenna mounting height to clear obstructions',
            'Verify clear LOS — check for new obstructions (trees, buildings)',
            'Inspect all RF connectors and coaxial cables for damage or corrosion',
        ]
    elif value < -75:
        issues.append(f'Signal poor at {value} dBm — link unstable under load')
        recs += [
            'Fine-tune antenna alignment for maximum signal',
            'Consider upgrading to a higher-gain antenna',
            'Check for physical obstructions blocking the LOS path',
        ]
    elif value < -70:
        issues.append(f'Signal weak at {value} dBm — marginal performance')
        recs.append('Improve antenna alignment to recover signal margin')

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


def evaluate_signal_aux(value: Optional[float]) -> MetricEvaluation:
    name = 'signal_aux'
    display_name = 'Signal Level (Aux)'
    unit = 'dBm'
    ref = 'Same thresholds as main signal — auxiliary receive chain'
    expl = (
        'Auxiliary receive chain signal level. Should be close to the main signal. '
        'A large difference between main and aux chains indicates a hardware or antenna problem.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value >= -45:
        quality, score = 'Excellent', 100
    elif value >= -55:
        quality, score = 'Very Good', 95
    elif value >= -65:
        quality, score = 'Good', 90
    elif value >= -70:
        quality, score = 'Fair', 75
    elif value >= -75:
        quality, score = 'Weak', 60
    elif value >= -80:
        quality, score = 'Poor', 40
    else:
        quality, score = 'Critical', 10

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl)


def evaluate_signal_balance(main: Optional[float], aux: Optional[float]) -> MetricEvaluation:
    name = 'signal_balance'
    display_name = 'Chain Balance (Main vs Aux)'
    unit = 'dB'
    ref = '0-2 dB Excellent | 3-5 dB Good | 6-8 dB Fair | >8 dB Antenna Misalignment Warning'
    expl = (
        'Difference between main and aux receive chain signal levels. '
        'A balanced system has less than 3 dB difference between chains. '
        'Large imbalance indicates a failed antenna chain, damaged cable, or connector issue.'
    )
    if main is None or aux is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    diff = abs(main - aux)

    if diff <= 2:
        quality, score = 'Excellent', 100
    elif diff <= 5:
        quality, score = 'Good', 85
    elif diff <= 8:
        quality, score = 'Fair', 60
    else:
        quality, score = 'Antenna Misalignment Warning', 20

    issues, recs = [], []
    if diff > 8:
        issues.append(f'Severe chain imbalance: {diff:.1f} dB — hardware fault likely')
        recs += [
            'Possible antenna chain imbalance — inspect radio hardware',
            'Check both antenna RF connector connections for corrosion or looseness',
            'Verify correct antenna polarization (V/H matching on both ends)',
            'Test each RF chain independently to isolate the faulty chain',
        ]
    elif diff > 5:
        issues.append(f'Chain imbalance: {diff:.1f} dB difference detected')
        recs += [
            'Check antenna RF connectors and cables',
            'Verify antenna polarization alignment',
        ]

    return MetricEvaluation(name, display_name, round(diff, 1), unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# SNR
# ---------------------------------------------------------------------------

def evaluate_snr(value: Optional[float], chain: str = 'Main') -> MetricEvaluation:
    name = 'snr' if chain == 'Main' else 'snr_aux'
    display_name = f'SNR ({chain})'
    unit = 'dB'
    ref = '>40 Outstanding | 35-40 Excellent | 30-35 Very Good | 25-30 Good | 20-25 Fair | 15-20 Poor | <15 Critical'
    expl = (
        'Signal-to-Noise Ratio — the margin between signal power and the noise floor. '
        'Higher SNR enables higher MCS index (faster modulation), directly determining '
        'maximum throughput. SNR < 20 dB severely limits data rates. '
        'SNR is more meaningful than raw signal level alone.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value > 40:
        quality, score = 'Outstanding', 100
    elif value >= 35:
        quality, score = 'Excellent', 95
    elif value >= 30:
        quality, score = 'Very Good', 90
    elif value >= 25:
        quality, score = 'Good', 80
    elif value >= 20:
        quality, score = 'Fair', 65
    elif value >= 15:
        quality, score = 'Poor', 45
    else:
        quality, score = 'Critical', 10

    issues, recs = [], []
    if value < 15:
        issues.append(f'SNR critically low at {value} dB — link barely functional')
        recs += [
            'Improve antenna alignment to maximize received signal',
            'Identify and mitigate RF interference sources near the radio',
            'Consider higher-gain antennas to improve the signal-to-noise margin',
            'Perform a spectrum scan to locate interference sources',
        ]
    elif value < 20:
        issues.append(f'SNR low at {value} dB — throughput severely limited')
        recs += [
            'Improve antenna alignment',
            'Reduce channel width to improve noise immunity',
            'Investigate nearby interference sources',
        ]
    elif value < 25:
        issues.append(f'SNR marginal at {value} dB — monitor for degradation')
        recs.append('Fine-tune antenna alignment to recover SNR margin')

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# Noise Floor
# ---------------------------------------------------------------------------

def evaluate_noise_floor(value: Optional[float]) -> MetricEvaluation:
    name = 'noise'
    display_name = 'Noise Floor'
    unit = 'dBm'
    ref = '<=-100 Outstanding | -98 Excellent | -95 Excellent | -92 Very Good | -90 Good | -87 Moderate | -85 Noisy | >-85 Severe Interference'
    expl = (
        'Background RF noise energy at the receiver. Lower (more negative) is better. '
        'High noise floor shrinks SNR even with strong signal, capping the maximum data rate. '
        'Common sources: nearby APs on the same channel, microwave ovens, radar, Bluetooth, '
        'poorly shielded equipment. Even a -5 dBm noise increase halves effective range.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value <= -100:
        quality, score = 'Outstanding', 100
    elif value <= -98:
        quality, score = 'Excellent', 97
    elif value <= -95:
        quality, score = 'Excellent', 93
    elif value <= -92:
        quality, score = 'Very Good', 85
    elif value <= -90:
        quality, score = 'Good', 78
    elif value <= -87:
        quality, score = 'Moderate', 60
    elif value <= -85:
        quality, score = 'Noisy', 40
    else:
        quality, score = 'Severe Interference', 10

    issues, recs = [], []
    if value > -85:
        issues.append(f'Severe RF interference — noise floor {value} dBm')
        recs += [
            'Heavy RF interference detected — perform spectrum analysis immediately',
            'Switch to a different, less-congested 5 GHz channel',
            'Reduce channel width to 20 MHz for better noise immunity',
            'Consider DFS channels (UNII-2/2e) if not already in use',
        ]
    elif value > -87:
        issues.append(f'High noise floor at {value} dBm — significant interference')
        recs += [
            'Switch to a less congested channel',
            'Consider reducing channel width to improve noise immunity',
        ]
    elif value > -90:
        issues.append(f'Elevated noise floor at {value} dBm — moderate interference present')
        recs.append('Monitor for interference growth — consider a channel survey')

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# CCQ (Connection Quality — Ligowave proprietary)
# ---------------------------------------------------------------------------

def evaluate_ccq(value: Optional[float]) -> MetricEvaluation:
    name = 'ccq'
    display_name = 'CCQ (Connection Quality)'
    unit = '%'
    ref = '95-100% Excellent | 85-95% Good | 70-85% Fair | 50-70% Poor | <50% Critical'
    expl = (
        'CCQ (Client Connection Quality) is a Ligowave-proprietary metric representing '
        'effective throughput as a percentage of theoretical maximum. It factors in '
        'retransmissions, PHY errors, and retry rates. A CCQ of 95% means the link is '
        'delivering 95% of what the PHY rate would theoretically allow.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value >= 95:
        quality, score = 'Excellent', 100
    elif value >= 85:
        quality, score = 'Good', 85
    elif value >= 70:
        quality, score = 'Fair', 65
    elif value >= 50:
        quality, score = 'Poor', 40
    else:
        quality, score = 'Critical', 10

    issues, recs = [], []
    if value < 50:
        issues.append(f'CCQ critically low at {value}% — severe link degradation')
        recs += [
            'Investigate retransmissions — check for RF interference or physical blockage',
            'Run a link test to measure actual throughput vs PHY rate',
        ]
    elif value < 70:
        issues.append(f'Poor CCQ at {value}% — link operating below potential')
        recs.append('Investigate link efficiency — check for retransmissions or interference')

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# Transmit Power
# ---------------------------------------------------------------------------

def evaluate_tx_power(value: Optional[float], signal: Optional[float] = None) -> MetricEvaluation:
    name = 'tx_power'
    display_name = 'Transmit Power'
    unit = 'dBm'
    ref = '0-10 Very Low | 11-18 Low | 19-24 Moderate | 25-29 High | 30+ Very High'
    expl = (
        'Transmit power determines coverage range and interference to neighboring radios. '
        'Stronger is not always better — excessive TX power causes RF pollution, may violate '
        'regulatory limits, and is unnecessary when the remote end is already close. '
        'Optimal power achieves target signal quality without exceeding it.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value <= 10:
        quality, score = 'Very Low', 75
    elif value <= 18:
        quality, score = 'Low', 85
    elif value <= 24:
        quality, score = 'Moderate', 100
    elif value <= 29:
        quality, score = 'High', 80
    else:
        quality, score = 'Very High', 60

    issues, recs = [], []
    if value > 28 and signal is not None and signal > -55:
        score = max(score - 25, 20)
        quality = 'Excessive'
        issues.append(f'TX power {value} dBm is excessive — remote signal already {signal} dBm')
        recs += [
            f'Reduce TX power — {value} dBm is unnecessary given strong {signal} dBm received signal',
            'Excessive TX power causes RF pollution to neighboring wireless networks',
            'Lower TX power to 20-23 dBm, verify link stability, adjust further as needed',
        ]
    elif value > 28:
        issues.append(f'TX power high at {value} dBm — verify regulatory compliance')
        recs.append('Verify transmit power complies with local regulations for this frequency band')

    color_map = {
        'Moderate': 'green', 'Low': 'lime', 'Very Low': 'yellow',
        'High': 'yellow', 'Very High': 'orange', 'Excessive': 'red',
    }
    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            color_map.get(quality, 'yellow'), ref, expl,
                            issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# Channel Width
# ---------------------------------------------------------------------------

def evaluate_channel_width(value: Optional[int]) -> MetricEvaluation:
    name = 'channel_width'
    display_name = 'Channel Width'
    unit = 'MHz'
    ref = '20 MHz Stable/Low interference | 40 MHz Higher throughput | 80 MHz Max throughput (clean RF only)'
    if value is None:
        expl = 'Channel width could not be determined.'
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value == 20:
        quality, score = 'Stable', 88
        expl = (
            '20 MHz: Best stability and interference immunity. Preferred for long-distance '
            'links or congested RF environments. Lowest throughput ceiling but most reliable.'
        )
    elif value == 40:
        quality, score = 'Good', 95
        expl = (
            '40 MHz: Good balance of throughput and interference immunity. '
            'Doubles theoretical throughput vs 20 MHz. Suitable for most deployments '
            'with moderate RF congestion.'
        )
    elif value == 80:
        quality, score = 'High Throughput', 90
        expl = (
            '80 MHz: Maximum throughput but highest interference susceptibility. '
            'Only recommended in clean RF environments with strong signal. '
            'Occupies significant spectrum — verify no co-channel interference.'
        )
    else:
        quality, score = 'Non-Standard', 70
        expl = f'{value} MHz is a non-standard channel width for 5 GHz 802.11 operation.'

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            'green' if score >= 88 else 'yellow', ref, expl)


# ---------------------------------------------------------------------------
# Frequency / Channel
# ---------------------------------------------------------------------------

def evaluate_frequency(value: Optional[float]) -> MetricEvaluation:
    name = 'frequency'
    display_name = 'Channel Frequency'
    unit = 'MHz'
    ref = '5170-5250 UNII-1 (no DFS) | 5250-5350 UNII-2 (DFS) | 5470-5725 UNII-2e (DFS) | 5725-5850 UNII-3 (no DFS)'
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref,
                                'Operating frequency could not be determined.')

    if 5170 <= value < 5250:
        band, dfs, risk = 'UNII-1', False, 'Low'
    elif 5250 <= value < 5350:
        band, dfs, risk = 'UNII-2', True, 'Medium'
    elif 5470 <= value < 5725:
        band, dfs, risk = 'UNII-2e', True, 'Medium'
    elif 5725 <= value <= 5850:
        band, dfs, risk = 'UNII-3', False, 'Low'
    else:
        band, dfs, risk = 'Unknown', False, 'Unknown'

    issues, recs = [], []
    if dfs:
        issues.append(f'DFS channel in {band} — radar events may cause 30-60 s service interruptions')
        recs.append(
            'DFS channels may cause brief outages when radar is detected. '
            'Ensure devices support DFS and consider a non-DFS channel for critical links.'
        )

    quality = 'Good' if not dfs else 'Fair'
    score = 90 if not dfs else 75
    expl = (
        f'{value} MHz — {band} band. '
        f'DFS required: {"Yes (radar detection active)" if dfs else "No"}. '
        f'Interference risk: {risk}.'
    )
    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            'green' if not dfs else 'yellow', ref, expl,
                            issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# Data Rate / PHY Rate
# ---------------------------------------------------------------------------

def evaluate_data_rate(tx_rate: Optional[float], rx_rate: Optional[float],
                       channel_width: Optional[int] = None) -> MetricEvaluation:
    name = 'data_rate'
    display_name = 'Data Rate (TX / RX)'
    unit = 'Mbps'
    ref = 'Relative to channel width: 20 MHz ~150 | 40 MHz ~300 | 80 MHz ~433 Mbps'
    expl = (
        'PHY (physical layer) data rate — the raw link speed negotiated between radios. '
        'Actual TCP throughput is typically 60-75% of PHY rate due to protocol overhead, '
        'ACK frames, and retransmissions. PHY rate is driven by MCS index and channel width.'
    )
    if tx_rate is None and rx_rate is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    max_rate_map = {20: 150, 40: 300, 80: 433}
    max_rate = max_rate_map.get(channel_width, 300)
    rate = max(tx_rate or 0, rx_rate or 0)
    pct = (rate / max_rate * 100) if max_rate else 0

    tcp_est = round(rate * 0.65)
    udp_est = round(rate * 0.80)

    if pct >= 75:
        quality, score = 'Excellent', 95
    elif pct >= 50:
        quality, score = 'Good', 78
    elif pct >= 30:
        quality, score = 'Fair', 55
    else:
        quality, score = 'Poor', 30

    value_display = f'{int(tx_rate or 0)} / {int(rx_rate or 0)}'
    detail = (
        f'TX: {tx_rate} Mbps | RX: {rx_rate} Mbps | '
        f'Est. TCP throughput: ~{tcp_est} Mbps | Est. UDP: ~{udp_est} Mbps'
    )
    return MetricEvaluation(name, display_name, value_display, unit, quality, score,
                            _quality_color(quality), ref, detail)


# ---------------------------------------------------------------------------
# MCS Index
# ---------------------------------------------------------------------------

def evaluate_mcs(value: Optional[int]) -> MetricEvaluation:
    name = 'mcs'
    display_name = 'MCS Index'
    unit = ''
    ref = 'MCS 7/9 (64-QAM/256-QAM) Excellent | MCS 4-6 Good | MCS 1-3 Fair | MCS 0 Critical'
    expl = (
        'MCS (Modulation and Coding Scheme) index determines the modulation used. '
        'MCS 0 = BPSK (lowest, most robust). MCS 7 = 64-QAM. MCS 9 = 256-QAM (highest, requires best SNR). '
        'Low MCS is automatically selected by the radio when SNR is insufficient for higher modulations.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value >= 7:
        quality, score = 'Excellent', 100
    elif value >= 5:
        quality, score = 'Good', 80
    elif value >= 3:
        quality, score = 'Fair', 58
    elif value >= 1:
        quality, score = 'Poor', 38
    else:
        quality, score = 'Critical', 10

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl)


# ---------------------------------------------------------------------------
# CPU Usage
# ---------------------------------------------------------------------------

def evaluate_cpu(value: Optional[float]) -> MetricEvaluation:
    name = 'cpu'
    display_name = 'CPU Usage'
    unit = '%'
    ref = '<50% Normal | 50-75% Moderate | 75-90% High | >90% Critical'
    expl = (
        'CPU utilization of the radio processor. High CPU usage can cause packet drop, '
        'increased latency, and missed beacons. Bursts during scanning or firmware operations '
        'are normal. Sustained high CPU warrants investigation.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value < 50:
        quality, score = 'Normal', 100
    elif value < 75:
        quality, score = 'Moderate', 80
    elif value < 90:
        quality, score = 'High', 45
    else:
        quality, score = 'Critical', 15

    issues, recs = [], []
    if value > 90:
        issues.append(f'CPU critically high at {value}% — packet drops likely')
        recs.append('Investigate high CPU — possible firmware issue, excessive clients, or traffic spike')
    elif value > 75:
        issues.append(f'CPU elevated at {value}% — monitor for performance impact')

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------

def evaluate_temperature(value: Optional[float]) -> MetricEvaluation:
    name = 'temperature'
    display_name = 'Temperature'
    unit = '°C'
    ref = '<60°C Normal | 60-75°C Warm | 75-85°C Hot | >85°C Critical'
    expl = (
        'Device operating temperature. Outdoor wireless equipment tolerates wide temperature '
        'ranges (-30°C to +70°C typically), but sustained high temperature reduces '
        'hardware lifespan and can cause radio calibration drift. Direct sun exposure '
        'and poor ventilation are common causes of overheating.'
    )
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    if value < 60:
        quality, score = 'Normal', 100
    elif value < 75:
        quality, score = 'Warm', 85
    elif value < 85:
        quality, score = 'Hot', 45
    else:
        quality, score = 'Critical', 10

    issues, recs = [], []
    if value > 85:
        issues.append(f'Temperature critically high at {value}°C — hardware at risk')
        recs += [
            'Ensure adequate ventilation — remove obstructions around radio enclosure',
            'Add sun shield if device is exposed to direct sunlight',
        ]
    elif value > 75:
        issues.append(f'Temperature elevated at {value}°C — monitor closely')

    return MetricEvaluation(name, display_name, value, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues, recommendations=recs)


# ---------------------------------------------------------------------------
# TX / RX Errors
# ---------------------------------------------------------------------------

def evaluate_errors(tx_errors: Optional[int], rx_errors: Optional[int]) -> MetricEvaluation:
    name = 'errors'
    display_name = 'TX / RX Errors'
    unit = 'count'
    ref = '0 Excellent | 1-10 Good | 11-100 Fair | 101-1000 Poor | >1000 Critical'
    expl = (
        'Cumulative count of failed frame transmissions. Some errors are normal in wireless '
        'environments due to channel variability. High TX errors indicate the remote radio '
        'cannot receive frames; high RX errors indicate the local radio is having difficulty '
        'decoding received frames, often due to interference or low SNR.'
    )
    if tx_errors is None and rx_errors is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)

    total = (tx_errors or 0) + (rx_errors or 0)
    if total == 0:
        quality, score = 'Excellent', 100
    elif total <= 10:
        quality, score = 'Good', 85
    elif total <= 100:
        quality, score = 'Fair', 65
    elif total <= 1000:
        quality, score = 'Poor', 35
    else:
        quality, score = 'Critical', 10

    issues = []
    if total > 100:
        issues.append(f'High error count — TX: {tx_errors}, RX: {rx_errors}')

    value_display = f'TX: {tx_errors or 0}  RX: {rx_errors or 0}'
    return MetricEvaluation(name, display_name, value_display, unit, quality, score,
                            _quality_color(quality), ref, expl, issues=issues)


# ---------------------------------------------------------------------------
# Uptime / SSID / Peer MAC / Security — informational only
# ---------------------------------------------------------------------------

def evaluate_uptime(value: Optional[str]) -> MetricEvaluation:
    name = 'uptime'
    display_name = 'Uptime'
    unit = ''
    ref = 'Longer uptime indicates stability'
    expl = 'Device uptime. Frequent reboots indicate power instability, firmware crashes, or watchdog triggers.'
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', ref, expl)
    return MetricEvaluation(name, display_name, value, unit, 'Info', 100, 'green', ref, expl)


def evaluate_ssid(value: Optional[str]) -> MetricEvaluation:
    name = 'ssid'
    display_name = 'SSID'
    unit = ''
    expl = 'Network name (SSID) broadcasted by the access point.'
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', '', expl)
    return MetricEvaluation(name, display_name, value, unit, 'Info', 100, 'green', '', expl)


def evaluate_peer_mac(value: Optional[str]) -> MetricEvaluation:
    name = 'peer_mac'
    display_name = 'Peer MAC'
    unit = ''
    expl = 'MAC address of the associated peer radio.'
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', '', expl)
    return MetricEvaluation(name, display_name, value, unit, 'Info', 100, 'green', '', expl)


def evaluate_wireless_mode(value: Optional[str]) -> MetricEvaluation:
    name = 'wireless_mode'
    display_name = 'Wireless Mode'
    unit = ''
    expl = 'Operating mode: Master (AP), Managed (Station/CPE), or Monitor.'
    if value is None:
        return MetricEvaluation(name, display_name, None, unit, 'N/A', 0, 'grey', '', expl)
    return MetricEvaluation(name, display_name, value, unit, 'Info', 100, 'green', '', expl)
