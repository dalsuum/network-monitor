"""Wireless Link Health Analysis Engine.

Public API:
    from wireless_health import WirelessHealthEngine
    from wireless_health.vendors.ligowave import parse_ssh_output
"""

from .engine import WirelessHealthEngine

__all__ = ['WirelessHealthEngine']
