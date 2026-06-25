"""RF engineering insights — educational context served with analysis results."""

from typing import Dict, Optional
from .types import RFInsight, MetricEvaluation


_ALL_INSIGHTS = [
    RFInsight(
        topic='snr',
        title='Why SNR Matters More Than Raw Signal',
        body=(
            'Signal strength alone does not determine link quality. A strong -55 dBm signal '
            'in a -80 dBm noise environment gives SNR = 25 dB (Good). The same -55 dBm signal '
            'in a -65 dBm noise environment gives SNR = 10 dB (Critical). SNR determines which '
            'MCS (modulation) the radio can use: SNR > 30 dB enables 64-QAM (MCS 7), while '
            'SNR < 15 dB forces BPSK (MCS 0), reducing throughput by 10x.'
        ),
    ),
    RFInsight(
        topic='noise',
        title='How Noise Floor Limits Throughput',
        body=(
            'The noise floor is the baseline RF energy level the receiver must overcome. '
            'Every 3 dB increase in noise floor halves the effective SNR, which typically '
            'drops the MCS index by 1-2 levels. A link running at 300 Mbps (MCS 7, 40 MHz) '
            'with a -95 dBm noise floor may fall to 150 Mbps if noise rises to -90 dBm '
            '(MCS 5). Interference sources include co-channel APs, radar, microwave ovens, '
            'and DECT phones.'
        ),
    ),
    RFInsight(
        topic='signal',
        title='Why Stronger Signal Is Not Always Better',
        body=(
            'Very strong signal (-30 to -40 dBm) can actually cause problems: the receiver '
            'ADC may saturate (overload), increasing error rates. Some radios automatically '
            'reduce RX gain at very high signal levels. Additionally, high TX power causes '
            'RF pollution to neighboring networks and may violate regulatory limits. '
            'The optimal target is -50 to -65 dBm — strong enough for high MCS, '
            'weak enough to avoid overload and interference.'
        ),
    ),
    RFInsight(
        topic='channel_width',
        title='Channel Width Trade-offs: Throughput vs Stability',
        body=(
            '20 MHz channels are most resistant to interference and have the longest range. '
            '40 MHz doubles throughput but doubles spectrum usage and interference risk. '
            '80 MHz maximizes throughput but requires a clean RF environment and strong signal. '
            'A wider channel in a noisy environment can actually result in lower real throughput '
            'than a narrower channel with better SNR. Rule of thumb: use 40 MHz for PTMP sector '
            'APs, 80 MHz only for clean PTP links with SNR > 35 dB.'
        ),
    ),
    RFInsight(
        topic='dfs',
        title='DFS Channels: Benefits and Risks',
        body=(
            'DFS (Dynamic Frequency Selection) channels in UNII-2 (5250-5350 MHz) and UNII-2e '
            '(5470-5725 MHz) are required to detect and avoid radar signals. When radar is '
            'detected, the radio must vacate the channel within 10 seconds and cannot return '
            'for 30 minutes. This causes service outages. However, DFS channels are less '
            'congested than UNII-1/3 because consumer devices rarely support them, making '
            'them attractive for carrier-grade links where the outage risk is acceptable.'
        ),
    ),
    RFInsight(
        topic='ccq',
        title='CCQ: What It Measures and Why It Drops',
        body=(
            'CCQ (Connection Quality) measures the ratio of successful data delivery to '
            'theoretical maximum. A CCQ of 90% means 10% of capacity is lost to retransmissions '
            'and overhead. CCQ drops when: (1) interference causes frame errors requiring '
            'retransmission, (2) signal is too weak forcing low MCS, (3) hidden node problem '
            'creates collisions, or (4) the AP is congested with too many associated clients. '
            'CCQ below 70% typically indicates a problem requiring investigation.'
        ),
    ),
    RFInsight(
        topic='phy_rate',
        title='PHY Rate vs Real Throughput',
        body=(
            'The PHY rate shown in radio statistics is the raw modulation speed — not actual '
            'usable throughput. Real TCP throughput is typically 60-75% of PHY rate due to: '
            '802.11 CSMA/CA overhead (backoff, SIFS/DIFS intervals), ACK frames, frame headers, '
            'TCP/IP protocol overhead, and retransmissions. A 300 Mbps PHY rate delivers roughly '
            '180-220 Mbps of real TCP throughput. UDP throughput is higher (~80% of PHY rate) '
            'because it has no ACK mechanism.'
        ),
    ),
    RFInsight(
        topic='rssi',
        title='RSSI vs dBm: Understanding the Difference',
        body=(
            'RSSI (Received Signal Strength Indicator) is a unitless relative measurement (0-100 '
            'or 0-255 depending on driver) used internally by the radio chipset. The dBm values '
            'shown in wireless statistics are a conversion from RSSI using a vendor-specific '
            'formula. Different vendors calibrate RSSI differently, so comparing dBm values '
            'across vendors requires caution. Ligowave dBm values are well-calibrated and '
            'represent actual received power at the antenna port.'
        ),
    ),
]

# Map topic → insight for fast lookup
_INSIGHTS_BY_TOPIC: Dict[str, RFInsight] = {i.topic: i for i in _ALL_INSIGHTS}


def select_insights(metrics: Dict[str, MetricEvaluation]) -> list:
    """Choose relevant RF insights based on which metrics have issues."""
    selected = []
    topics_added = set()

    def _add(topic: str):
        if topic not in topics_added and topic in _INSIGHTS_BY_TOPIC:
            selected.append(_INSIGHTS_BY_TOPIC[topic])
            topics_added.add(topic)

    snr = metrics.get('snr')
    noise = metrics.get('noise')
    signal = metrics.get('signal')
    ccq = metrics.get('ccq')
    cw = metrics.get('channel_width')
    freq = metrics.get('frequency')

    # Always include SNR insight — most impactful
    _add('snr')

    if noise and noise.value is not None and noise.value > -90:
        _add('noise')

    if signal and signal.value is not None and signal.value > -55:
        _add('signal')  # explain "too strong" risk

    if cw and cw.value is not None:
        _add('channel_width')

    if freq and freq.issues:
        _add('dfs')

    if ccq and ccq.value is not None and ccq.value < 90:
        _add('ccq')

    # Always add PHY rate explanation
    _add('phy_rate')

    # Cap at 5 insights to avoid overwhelming the user
    return selected[:5]
