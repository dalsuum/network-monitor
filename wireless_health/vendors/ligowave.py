"""Ligowave SSH output parser.

Parses raw SSH command output from Ligowave DLB APC devices and
returns a normalized metrics dict consumable by WirelessHealthEngine.
Handles both standard Linux wireless tools and Ligowave-specific output.
"""

import re
from typing import Any, Dict, Optional

SSH_COMMANDS = [
    'uptime',
    'iwconfig',
    'cat /proc/net/wireless',
    'iw dev wlan0 station dump',
    'cat /proc/loadavg',
    'free -m',
]


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def parse_ssh_output(raw_output: str, model: str = '') -> Dict[str, Any]:
    """Parse combined SSH stdout from a Ligowave device.

    Expected input: concatenated output of:
        uptime, iwconfig wlan0, cat /proc/net/wireless,
        iw dev wlan0 station dump, cat /proc/loadavg, free -m
    """
    metrics: Dict[str, Any] = {}

    _parse_iwconfig(raw_output, metrics)
    _parse_proc_net_wireless(raw_output, metrics)
    _parse_iw_station_dump(raw_output, metrics)
    _parse_uptime(raw_output, metrics)
    _parse_loadavg(raw_output, metrics)
    _parse_free(raw_output, metrics)

    # Derive SNR if signal and noise are both known
    if 'snr' not in metrics and 'signal' in metrics and 'noise' in metrics:
        try:
            metrics['snr'] = round(metrics['signal'] - metrics['noise'], 1)
        except (TypeError, ValueError):
            pass

    return metrics


# ---------------------------------------------------------------------------
# iwconfig parser
# ---------------------------------------------------------------------------

def _parse_iwconfig(text: str, metrics: dict):
    """Extract metrics from iwconfig output."""

    # Wireless mode
    m = re.search(r'Mode:(\S+)', text)
    if m:
        metrics['wireless_mode'] = m.group(1).strip()

    # Frequency / channel
    m = re.search(r'Frequency:([\d.]+)\s*GHz', text)
    if m:
        try:
            metrics['frequency'] = round(float(m.group(1)) * 1000)  # GHz → MHz
        except ValueError:
            pass

    m = re.search(r'Frequency:(\d+)\s*MHz', text)
    if m:
        try:
            metrics['frequency'] = int(m.group(1))
        except ValueError:
            pass

    # SSID / ESSID
    m = re.search(r'ESSID:"([^"]*)"', text)
    if m:
        metrics['ssid'] = m.group(1)

    # Bit Rate (TX rate)
    m = re.search(r'Bit Rate[=:]\s*([\d.]+)\s*[Mm]b', text)
    if m:
        try:
            metrics['tx_rate'] = float(m.group(1))
        except ValueError:
            pass

    # Signal level
    m = re.search(r'Signal level[=:]\s*(-\d+)\s*dBm', text)
    if m:
        try:
            metrics['signal'] = int(m.group(1))
        except ValueError:
            pass

    # Noise level
    m = re.search(r'Noise level[=:]\s*(-\d+)\s*dBm', text)
    if m:
        try:
            metrics['noise'] = int(m.group(1))
        except ValueError:
            pass

    # TX Power
    m = re.search(r'Tx-Power[=:]\s*(\d+)\s*dBm', text, re.IGNORECASE)
    if m:
        try:
            metrics['tx_power'] = int(m.group(1))
        except ValueError:
            pass

    # TX / RX errors from iwconfig counters
    m = re.search(r'Tx excessive retries:(\d+)', text)
    if m:
        try:
            metrics['tx_errors'] = int(m.group(1))
        except ValueError:
            pass

    m = re.search(r'Invalid\s+misc:(\d+)', text)
    if m:
        try:
            metrics['rx_errors'] = int(m.group(1))
        except ValueError:
            pass

    # Access Point (peer MAC)
    m = re.search(r'Access Point:\s*([0-9A-Fa-f:]{17})', text)
    if m:
        metrics['peer_mac'] = m.group(1).upper()

    # Link quality fraction → CCQ-like percentage
    m = re.search(r'Link Quality=(\d+)/(\d+)', text)
    if m:
        try:
            num, den = int(m.group(1)), int(m.group(2))
            if den > 0:
                metrics.setdefault('ccq', round(num / den * 100, 1))
        except (ValueError, ZeroDivisionError):
            pass


# ---------------------------------------------------------------------------
# /proc/net/wireless parser
# ---------------------------------------------------------------------------

def _parse_proc_net_wireless(text: str, metrics: dict):
    """Parse /proc/net/wireless table if present in the output.

    Handles any interface name (ra0, ath0, wlan0, etc.) and both value
    formats: with trailing dot (e.g. -59.) and without (e.g. -59).
    """
    for line in text.splitlines():
        # Format: "  ra0: 0000   10.  -59   -95   ..."
        #         "  wlan0: 0000   90.  -57.  -95.  ..."
        m = re.match(r'\s*\w+:\s+\w+\s+([\d.]+)\s+(-?\d+)\.?\s+(-?\d+)', line)
        if not m:
            continue
        try:
            link_val  = float(m.group(1))
            sig_val   = int(m.group(2))
            noise_val = int(m.group(3))
            # Skip header/garbage rows — real values are always negative dBm
            if sig_val >= 0 or noise_val >= 0:
                continue
            if 'signal' not in metrics:
                metrics['signal'] = sig_val
            if 'noise' not in metrics:
                metrics['noise'] = noise_val
            # link quality is already on 0-100 scale on most drivers
            if 'ccq' not in metrics and link_val >= 0:
                metrics['ccq'] = round(min(link_val, 100), 1)
        except (ValueError, IndexError):
            pass


# ---------------------------------------------------------------------------
# iw dev station dump parser
# ---------------------------------------------------------------------------

def _parse_iw_station_dump(text: str, metrics: dict):
    """Parse `iw dev wlan0 station dump` output."""

    # Station MAC address (peer)
    m = re.search(r'Station\s+([0-9A-Fa-f:]{17})', text)
    if m:
        metrics.setdefault('peer_mac', m.group(1).upper())

    # Signal (last rx signal)
    m = re.search(r'signal:\s+(-\d+)\s+\[(-\d+),\s*(-\d+)\]\s*dBm', text)
    if m:
        try:
            avg = int(m.group(1))
            chain0 = int(m.group(2))
            chain1 = int(m.group(3))
            metrics.setdefault('signal', avg)
            # Use the two chains as main/aux if not already set
            metrics.setdefault('signal_aux', chain1)
        except ValueError:
            pass

    m = re.search(r'signal:\s+(-\d+)\s+dBm', text)
    if m:
        try:
            metrics.setdefault('signal', int(m.group(1)))
        except ValueError:
            pass

    # RX bitrate
    m = re.search(r'rx bitrate:\s+([\d.]+)\s+MBit/s', text)
    if m:
        try:
            metrics.setdefault('rx_rate', float(m.group(1)))
        except ValueError:
            pass

    # TX bitrate
    m = re.search(r'tx bitrate:\s+([\d.]+)\s+MBit/s', text)
    if m:
        try:
            metrics.setdefault('tx_rate', float(m.group(1)))
        except ValueError:
            pass

    # MCS index from tx bitrate line
    m = re.search(r'tx bitrate:.+MCS\s*(\d+)', text)
    if m:
        try:
            metrics['mcs'] = int(m.group(1))
        except ValueError:
            pass

    # Channel width from tx bitrate line
    for width in (80, 40, 20):
        if f'{width}MHz' in text or f'{width} MHz' in text:
            metrics.setdefault('channel_width', width)
            break

    # TX/RX packet counts for error rate calculation
    m = re.search(r'tx packets:\s+(\d+)', text)
    tx_pkts = int(m.group(1)) if m else None

    m = re.search(r'tx retries:\s+(\d+)', text)
    if m and tx_pkts:
        try:
            retries = int(m.group(1))
            metrics.setdefault('tx_errors', retries)
        except ValueError:
            pass

    m = re.search(r'rx drop misc:\s+(\d+)', text)
    if m:
        try:
            metrics.setdefault('rx_errors', int(m.group(1)))
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Uptime parser
# ---------------------------------------------------------------------------

def _parse_uptime(text: str, metrics: dict):
    # "13:45:21 up  4:05,  load average: 0.59..."  — no "X user" on embedded devices
    # "13:44:45 up 3 days, 13:37,  load average: 0.00..."
    m = re.search(r'up\s+(.+?),\s+load average', text)
    if m:
        metrics['uptime'] = m.group(1).strip()
        return
    # Fallback: "up X days, HH:MM, N user(s)"
    m = re.search(r'up\s+([\d:dhms ,]+),\s+\d+\s+user', text)
    if m:
        metrics['uptime'] = m.group(1).strip()


# ---------------------------------------------------------------------------
# /proc/loadavg → CPU approximation
# ---------------------------------------------------------------------------

def _parse_loadavg(text: str, metrics: dict):
    """Approximate CPU usage from 1-min load average and CPU count."""
    m = re.search(r'^([\d.]+)\s+([\d.]+)\s+([\d.]+)', text, re.MULTILINE)
    if m:
        try:
            load1 = float(m.group(1))
            # Embedded devices typically have 1-2 CPU cores
            cpu_count = 1
            m_cores = re.search(r'processor\s*:\s*(\d+)', text)
            if m_cores:
                cpu_count = int(m_cores.group(1)) + 1
            metrics['cpu'] = round(min(load1 / cpu_count * 100, 100), 1)
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# free -m → Memory usage
# ---------------------------------------------------------------------------

def _parse_free(text: str, metrics: dict):
    m = re.search(r'Mem:\s+(\d+)\s+(\d+)\s+(\d+)', text)
    if m:
        try:
            total = int(m.group(1))
            used  = int(m.group(2))
            if total > 0:
                metrics['memory'] = round(used / total * 100, 1)
        except (ValueError, ZeroDivisionError):
            pass
