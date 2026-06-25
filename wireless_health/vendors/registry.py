"""Vendor Profile Registry.

Loads JSON config files from wireless_health/config/ and provides
lookup by (vendor, model). Adding a new vendor requires only a new
JSON file — no code changes needed.
"""

import json
import os
import re
from typing import Dict, Optional

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')


def _slug(text: str) -> str:
    """Convert vendor/model string to a filesystem-safe slug."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


class VendorRegistry:
    """Registry of vendor/model profiles loaded from JSON config files."""

    def __init__(self):
        self._profiles: Dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        """Load all JSON profiles from the config directory."""
        if not os.path.isdir(_CONFIG_DIR):
            return
        for fname in os.listdir(_CONFIG_DIR):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(_CONFIG_DIR, fname)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                vendor = data.get('vendor', '')
                model  = data.get('model', '')
                key    = f'{_slug(vendor)}_{_slug(model)}'
                self._profiles[key] = data
            except Exception:
                pass  # silently skip malformed files

    def get_profile(self, vendor: str, model: str) -> Optional[dict]:
        """Return the profile dict for a vendor/model combination, or None."""
        key = f'{_slug(vendor)}_{_slug(model)}'
        return self._profiles.get(key)

    def list_profiles(self) -> list:
        """Return list of all loaded profile summaries."""
        return [
            {
                'vendor': p.get('vendor'),
                'model':  p.get('model'),
                'type':   p.get('type'),
            }
            for p in self._profiles.values()
        ]

    def get_vendors(self) -> list:
        """Return sorted list of unique vendor names."""
        return sorted({p.get('vendor', '') for p in self._profiles.values() if p.get('vendor')})

    def get_models_for_vendor(self, vendor: str) -> list:
        """Return sorted list of model names for a given vendor."""
        return sorted(
            p.get('model', '') for p in self._profiles.values()
            if p.get('vendor', '').lower() == vendor.lower() and p.get('model')
        )
