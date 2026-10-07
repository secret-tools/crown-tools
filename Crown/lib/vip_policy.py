"""Validation commune des modules VIP, sans exécution des scripts."""
import re
import unicodedata

_EXCLUDED = (
    'µµµ',
)


def require_allowed_module(module):
    """Valide les noms, catégories et chemins des modules."""
    if not isinstance(module, dict):
        raise ValueError('Option VIP invalide.')

    for field in ('name', 'category', 'entry'):
        value = module.get(field, '')
        if not isinstance(value, str):
            raise ValueError('Champ VIP invalide : ' + field)

        value = unicodedata.normalize('NFKC', value).casefold()
        normalized = re.sub(r'[^a-z0-9]+', ' ', value).strip()
        compact = normalized.replace(' ', '')

        for excluded in _EXCLUDED:
            if excluded in normalized or excluded.replace(' ', '') in compact:
                raise ValueError('Intégration VIP exclue : ' + excluded)


def validate_pack_policy(pack):
    """Valide les modules avant l’activation du catalogue."""
    if not isinstance(pack, dict) or not isinstance(pack.get('modules'), list):
        raise ValueError('Pack VIP invalide.')

    for module in pack['modules']:
        require_allowed_module(module)
