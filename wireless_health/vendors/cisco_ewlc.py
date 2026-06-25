"""Cisco eWLC (IOS-XE Embedded Wireless LAN Controller) SSH parser.

Parses output from Cisco IOS-XE WLC CLI commands and returns a normalized
metrics dict consumable by WirelessHealthEngine.

IMPORTANT: Cisco IOS-XE does not support paramiko exec_command().
Use collect_ssh_output(client) which drives invoke_shell() instead.

Commands collected:
    terminal length 0  (suppresses --More-- pagination)
    show version
    show ap summary
    show ap dot11 5ghz summary
    show ap dot11 24ghz summary
    show wireless client summary
"""

import re
import time
from typing import Any, Dict

SSH_COMMANDS = [
    'show version',
    'show ap summary',
    'show ap dot11 5ghz summary',
    'show ap dot11 24ghz summary',
    'show wireless client summary',
]

# ANSI escape code pattern (Cisco sometimes sends colour codes)
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mKJ]')


# ---------------------------------------------------------------------------
# SSH collector — tries exec_command first, falls back to invoke_shell
# ---------------------------------------------------------------------------

def collect_ssh_output(client, timeout: int = 30) -> str:
    """Collect IOS-XE command output via SSH.

    Strategy:
      1. exec_command — non-interactive, no PTY, works on most C9800 configs
         when disabled_algorithms is NOT set (required for rsa-sha2-256 host key).
      2. invoke_shell — interactive PTY session, used if the device rejects
         exec channels (some VTY configurations require this).

    Returns combined output string ready for parse_ssh_output().
    """
    try:
        output = _collect_via_exec(client, timeout)
        if output.strip():
            return output
        # Empty output from exec_command usually means the channel was rejected
        raise Exception('exec_command returned empty output')
    except Exception as exec_err:
        pass  # fall through to invoke_shell

    # Fallback: interactive shell
    try:
        return _collect_via_shell(client, timeout)
    except Exception as shell_err:
        raise Exception(
            f'Both SSH methods failed for Cisco eWLC. '
            f'exec_command: {exec_err} | invoke_shell: {shell_err}. '
            f'Check: VTY "transport input ssh", "exec-timeout 30 0", '
            f'user has privilege 15.'
        )


def _collect_via_exec(client, timeout: int) -> str:
    """Collect using exec_command (non-interactive — no PTY needed)."""
    parts = []
    for cmd in SSH_COMMANDS:
        _, stdout, _ = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='ignore').strip()
        if out:
            parts.append(f'--- {cmd} ---\n{out}')
    return '\n'.join(parts)


def _collect_via_shell(client, timeout: int) -> str:
    """Collect using invoke_shell (PTY-based interactive session)."""
    # Give IOS-XE a moment to finalize channel setup after authentication
    time.sleep(0.5)

    shell = client.invoke_shell(term='vt100', width=220, height=24)
    shell.settimeout(timeout)

    # Drain the login banner and wait for the initial prompt (#)
    _drain(shell, wait=2.5)

    # Disable --More-- pagination for this session
    shell.send('terminal length 0\n')
    _drain(shell, wait=0.8)

    parts = []
    for cmd in SSH_COMMANDS:
        shell.send(cmd + '\n')
        raw = _recv_until_prompt(shell, idle_secs=3.0, max_secs=timeout)
        cleaned = _clean_output(raw, cmd)
        if cleaned.strip():
            parts.append(f'--- {cmd} ---\n{cleaned}')

    return '\n'.join(parts)


def _drain(shell, wait: float) -> None:
    """Sleep briefly then discard any pending bytes in the receive buffer."""
    time.sleep(wait)
    while shell.recv_ready():
        shell.recv(65535)


def _recv_until_prompt(shell, idle_secs: float = 3.0, max_secs: float = 30) -> str:
    """Read until an IOS-XE exec prompt (hostname#) appears or timeouts fire."""
    buf = ''
    last_data = time.time()
    deadline = time.time() + max_secs

    while time.time() < deadline:
        if shell.recv_ready():
            chunk = shell.recv(8192).decode('utf-8', errors='ignore')
            buf += chunk
            last_data = time.time()
            # Prompt: a short token ending with # on its own line (strip ANSI first)
            tail = _ANSI_RE.sub('', buf[-400:])
            if re.search(r'^[^\s\r]{1,64}#\s*$', tail, re.MULTILINE):
                break
        else:
            if buf and (time.time() - last_data) > idle_secs:
                break
            time.sleep(0.05)

    return buf


def _clean_output(raw: str, cmd: str) -> str:
    """Strip ANSI codes, the echoed command line, and trailing prompt lines."""
    text = _ANSI_RE.sub('', raw)
    lines = []
    skip_echo = True
    for line in text.splitlines():
        stripped = line.strip()
        if skip_echo and cmd.strip() in stripped:
            skip_echo = False
            continue
        # Drop IOS prompt lines (e.g. "WLC-HOSTNAME#")
        if re.match(r'^[^\s\r]{1,64}[#>]\s*$', stripped):
            continue
        lines.append(line)
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def parse_ssh_output(raw_output: str, model: str = '') -> Dict[str, Any]:
    """Parse combined SSH stdout from a Cisco eWLC device.

    Returns metrics dict with keys usable by WirelessHealthEngine:
      ccq        — AP join ratio as percentage (0-100)
      snr        — average SNR across managed APs (dB)
      tx_power   — average TX power across managed APs (dBm)
      channel_width — most common channel width in use (MHz)
      tx_errors  — set when average channel utilization > 75%
      client_count — total associated wireless clients
      uptime     — controller uptime string
      wireless_mode — always "Controller"
      ap_total   — total APs known to the controller
      ap_joined  — APs in Registered/Up state
      channel_util — average channel utilization percentage
      ios_xe_version — IOS-XE version string
    """
    metrics: Dict[str, Any] = {}
    metrics['wireless_mode'] = 'Controller'

    _parse_version(raw_output, metrics)
    _parse_ap_summary(raw_output, metrics)
    _parse_ap_dot11_summary(raw_output, metrics)
    _parse_client_summary(raw_output, metrics)

    return metrics


# ---------------------------------------------------------------------------
# show version
# ---------------------------------------------------------------------------

def _parse_version(text: str, metrics: dict):
    # "Cisco IOS XE Software, Version 17.9.4a"
    m = re.search(r'IOS[-\s]XE\s+Software.*?Version\s+([\d.a-zA-Z]+)', text, re.IGNORECASE)
    if m:
        metrics['ios_xe_version'] = m.group(1)

    # "<hostname> uptime is 3 weeks, 2 days, 11 hours, 5 minutes"
    m = re.search(r'uptime is\s+(.+?)(?:\r?\n|$)', text, re.IGNORECASE)
    if m:
        metrics['uptime'] = m.group(1).strip()


# ---------------------------------------------------------------------------
# show ap summary
# ---------------------------------------------------------------------------

def _parse_ap_summary(text: str, metrics: dict):
    # "Number of APs: 8"  or  "Total number of APs: 8"
    m = re.search(r'(?:Total\s+)?[Nn]umber of APs\s*:\s*(\d+)', text)
    if m:
        metrics['ap_total'] = int(m.group(1))

    # Count AP table rows that have an IP address and end with "Registered"
    registered = 0
    total_from_table = 0
    for line in text.splitlines():
        if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line):
            total_from_table += 1
            if 'Registered' in line:
                registered += 1

    if total_from_table > 0 and 'ap_total' not in metrics:
        metrics['ap_total'] = total_from_table

    if registered:
        metrics['ap_joined'] = registered

    total = metrics.get('ap_total', 0)
    if total > 0 and registered >= 0:
        ratio = round(registered / total * 100, 1)
        metrics['ap_join_ratio'] = ratio
        # Map to CCQ slot — AP join health is the primary WLC quality metric
        metrics['ccq'] = ratio


# ---------------------------------------------------------------------------
# show ap dot11 5ghz summary / 24ghz summary
# ---------------------------------------------------------------------------

def _parse_ap_dot11_summary(text: str, metrics: dict):
    """Extract per-AP SNR, TX power, and channel width; average across all APs."""
    snr_values = []
    txpwr_values = []
    channel_widths = []
    util_values = []

    for line in text.splitlines():
        # AP data rows contain "Enabled" or "Disabled" admin state
        if 'Enabled' not in line and 'Disabled' not in line:
            continue

        # TX power in dBm: "(14 dBm)" or "(11 dBm)"
        m = re.search(r'\((\d+)\s*dBm\)', line)
        if m:
            try:
                dbm = int(m.group(1))
                if 0 < dbm <= 36:
                    txpwr_values.append(dbm)
            except ValueError:
                pass

        # SNR: integer immediately after the parenthesised dBm value
        # e.g. "Up   40   *5/8 (14 dBm)   32   1   (149)"
        m = re.search(r'\(\d+\s*dBm\)\s+(\d{1,2})\b', line)
        if m:
            try:
                snr = int(m.group(1))
                if 3 <= snr <= 60:
                    snr_values.append(snr)
            except ValueError:
                pass

        # Channel width: 20, 40, or 80 between "Up" and TxPwr column
        m = re.search(r'\bUp\b\s+(20|40|80)\b', line)
        if m:
            channel_widths.append(int(m.group(1)))

        # Channel utilization percentage (Load column, if present)
        m = re.search(r'\b(\d{1,3})%', line)
        if m:
            try:
                util = int(m.group(1))
                if 0 <= util <= 100:
                    util_values.append(util)
            except ValueError:
                pass

    if snr_values:
        metrics['snr'] = round(sum(snr_values) / len(snr_values), 1)

    if txpwr_values:
        metrics['tx_power'] = round(sum(txpwr_values) / len(txpwr_values), 1)

    if channel_widths:
        # Most common channel width in the fleet
        from statistics import mode as stat_mode
        try:
            metrics['channel_width'] = stat_mode(channel_widths)
        except Exception:
            metrics['channel_width'] = channel_widths[0]

    if util_values:
        avg_util = round(sum(util_values) / len(util_values), 1)
        metrics['channel_util'] = avg_util
        if avg_util > 75:
            # Signal high channel utilization to the errors evaluator
            metrics['tx_errors'] = int(avg_util)


# ---------------------------------------------------------------------------
# show wireless client summary
# ---------------------------------------------------------------------------

def _parse_client_summary(text: str, metrics: dict):
    # "Number of Local Clients : 45"  or  "Number of Clients: 45"
    m = re.search(r'Number of (?:Local )?Clients\s*[:\s]\s*(\d+)', text, re.IGNORECASE)
    if m:
        metrics['client_count'] = int(m.group(1))
        return
    # Fallback: "45 clients"
    m = re.search(r'\b(\d+)\s+client', text, re.IGNORECASE)
    if m:
        metrics['client_count'] = int(m.group(1))
