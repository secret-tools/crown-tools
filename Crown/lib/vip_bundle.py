"""Format portable VIP Python v2. La lecture n'exécute aucun fichier."""
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from .constants import resolve_input_path
from .vip_policy import validate_pack_policy, require_allowed_module

LIMIT = 200_000_000

def safe_path(name):
    if not isinstance(name, str):
        raise ValueError('Chemin invalide.')
    parts = name.split('/')
    if not name or '\\' in name or any(p in ('', '.', '..') for p in parts):
        raise ValueError('Chemin interdit : ' + name)
    for p in parts:
        if any(ord(c) < 32 or c in ':*?"<>|' for c in p) or p.endswith((' ', '.')):
            raise ValueError('Chemin Windows invalide : ' + name)
        if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])', p.split('.')[0]):
            raise ValueError('Nom réservé : ' + name)
    return PurePosixPath(name)

def label(value, limit):
    if not isinstance(value, str) or not 0 < len(value.strip()) <= limit or '|' in value or not value.isprintable():
        raise ValueError('Nom ou catégorie invalide.')
    return value.strip()

def validate(archive):
    infos = archive.infolist()
    if len(infos) > 20000 or sum(i.file_size for i in infos) > LIMIT:
        raise ValueError('Pack trop volumineux (200 Mo ou 20 000 fichiers).')
    names = set()
    for i in infos:
        safe_path(i.filename)
        require_allowed_module({'entry': i.filename})
        if i.filename.casefold() in names or i.flag_bits & 1 or stat.S_ISLNK(i.external_attr >> 16):
            raise ValueError('Doublon, lien ou fichier chiffré interdit.')
        names.add(i.filename.casefold())
        if i.filename != 'vip.json' and not i.filename.startswith('tools/'):
            raise ValueError('Fichier hors du dossier tools.')
    if archive.getinfo('vip.json').file_size > 1_000_000:
        raise ValueError('Manifeste trop volumineux.')
    pack = json.loads(archive.read('vip.json'))
    if not isinstance(pack, dict) or pack.get('version') != 2:
        raise ValueError('Format VIP Python non reconnu.')
    label(pack.get('name'), 60)
    modules = pack.get('modules')
    if not isinstance(modules, list) or not 1 <= len(modules) <= 1000:
        raise ValueError('Le pack doit contenir 1 à 1000 options.')
    seen = set()
    actual = {i.filename for i in infos}
    for m in modules:
        if not isinstance(m, dict):
            raise ValueError('Option invalide.')
        name = label(m.get('name'), 60)
        label(m.get('category'), 40)
        label(m.get('description'), 200)
        entry = m.get('entry', '')
        safe_path(entry)
        if m.get('action') != 'python' or entry not in actual or not entry.startswith('tools/') or not entry.endswith('.py'):
            raise ValueError('Point de lancement absent ou invalide.')
        if name.casefold() in seen:
            raise ValueError('Nom d’option en double : ' + name)
        seen.add(name.casefold())
    validate_pack_policy(pack)
    return pack

def load_bundle(path):
    path = resolve_input_path(path)
    if path.stat().st_size > LIMIT:
        raise ValueError('Archive trop volumineuse.')
    with zipfile.ZipFile(path) as archive:
        pack = validate(archive)
    pack['_archive_path'] = str(path.resolve())
    validate_pack_policy(pack)
    return pack
