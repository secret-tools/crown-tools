"""Excluded integrations are rejected before importing or launching a pack."""
import re

_EXCLUDED = ("µµ")

def require_allowed_module(module):
    metadata = ' '.join(str(module.get(key, '')) for key in ('name', 'category', 'description', 'entry'))
    if _EXCLUDED.search(metadata) or str(module.get('category', '')).strip().casefold() == 'attack':
        raise ValueError('Module excluded from Crown / Module exclu de Crown: ' + str(module.get('name', '')))

def validate_pack_policy(pack):
    for module in pack.get('modules', []):
        require_allowed_module(module)
