"""Excluded integrations are rejected before importing or launching a pack."""
import re

_EXCLUDED = re.compile(r"(?<![a-z])(?:key[\s_-]*logger|(?:email|sms)[\s_-]*bomb(?:er|ing)?|ddos|nuker?|raid|spam(?:mer|ming)?|stealer|token[\s_-]*grabber|nitro[\s_-]*(?:gen|generator)|dox(?:ing|xer|[\s_-]*creator)?)(?![a-z])", re.IGNORECASE)

def require_allowed_module(module):
    metadata = ' '.join(str(module.get(key, '')) for key in ('name', 'category', 'description', 'entry'))
    if _EXCLUDED.search(metadata) or str(module.get('category', '')).strip().casefold() == 'attack':
        raise ValueError('Module excluded from Crown / Module exclu de Crown: ' + str(module.get('name', '')))

def validate_pack_policy(pack):
    for module in pack.get('modules', []):
        require_allowed_module(module)
