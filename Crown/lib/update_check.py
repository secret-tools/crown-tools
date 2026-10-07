import json
import re
import time
from dataclasses import dataclass
from urllib.request import Request, urlopen

from .version import VERSION

REPOSITORY = 'https://github.com/secret-tools/crown-tools'
HEAD_URL = REPOSITORY + '.git/info/refs?service=git-upload-pack'
RAW_ROOT = 'https://raw.githubusercontent.com/secret-tools/crown-tools/'
DOWNLOAD_URL = REPOSITORY + '/archive/refs/heads/main.zip'
DISCORD_URL = 'https://discord.gg/kaostools'
TELEGRAM_URL = 'https://t.me/v0idtool'


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise ValueError('Expected a stable version such as 1.0.1')
    return tuple(map(int, value.split('.')))


def parse_git_head(data):
    position = 0
    commits = []
    if not data.startswith(b'001e# service=git-upload-pack\n0000'):
        raise ValueError('Invalid Git advertisement')
    while position < len(data):
        if position + 4 > len(data):
            raise ValueError('Truncated Git packet')
        size = int(data[position:position + 4], 16)
        if size == 0:
            position += 4
            continue
        if size < 4 or position + size > len(data):
            raise ValueError('Invalid Git packet size')
        packet = data[position + 4:position + size].split(b'\x00', 1)[0].rstrip(b'\n')
        match = re.fullmatch(rb'([0-9a-f]{40}) refs/heads/main', packet)
        if match:
            commits.append(match.group(1).decode('ascii'))
        position += size
    if len(commits) != 1:
        raise ValueError('Missing or ambiguous main branch')
    return commits[0]


@dataclass(frozen=True)
class UpdateStatus:
    state: str
    current: str = VERSION
    latest: str = ''
    notes: str = ''
    commit: str = ''
    notes_by_language: dict | None = None


def check_for_update(current=VERSION, opener=urlopen):
    version_tuple(current)
    def fetch_json(url):
        request = Request(url + '?_=' + str(time.time_ns()), headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'Crown-Tools/' + current,
            'Cache-Control': 'no-cache, no-store',
        })
        with opener(request, timeout=6) as response:
            data = response.read(16385)
        if len(data) > 16384:
            raise ValueError('Version response too large')
        return json.loads(data)
    try:
        request = Request(HEAD_URL, headers={
            'User-Agent': 'Crown-Tools/' + current,
            'Cache-Control': 'no-cache, no-store',
            'Pragma': 'no-cache',
        })
        with opener(request, timeout=6) as response:
            advertisement = response.read(1048577)
        if len(advertisement) > 1048576:
            raise ValueError('Git advertisement too large')
        commit = parse_git_head(advertisement)
        manifest = fetch_json(RAW_ROOT + commit + '/version.json')
        latest = manifest['version']
        version_tuple(latest)
        notes = manifest.get('notes', '')
        if not isinstance(notes, str) or len(notes) > 2000:
            raise ValueError('Invalid release notes')
        translations = manifest.get('notes_by_language', {})
        if (not isinstance(translations, dict) or len(translations) > 6
                or any(key not in {'en', 'fr', 'es', 'de', 'zh', 'ar'}
                       or not isinstance(value, str) or len(value) > 2000
                       for key, value in translations.items())):
            raise ValueError('Invalid translated release notes')
        return UpdateStatus('current' if latest == current else 'required', current, latest, notes, commit, translations)
    except (OSError, ValueError, TypeError, KeyError):
        return UpdateStatus('unavailable', current)


def require_current_version(language=None):
    from .update_screen import UpdateGate
    return UpdateGate(language=language).run()
