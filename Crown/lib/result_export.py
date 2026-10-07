"""Store option results under Output, without overwriting existing reports."""
from datetime import datetime, timezone
import re
from . import constants

EXTENSIONS = {'CSV to JSON': '.json', 'JSON to CSV': '.csv',
              'JSON Format': '.json', 'JSON Minify': '.json',
              'TOML to JSON': '.json', 'XML Format': '.xml', 'Text Diff': '.diff'}

def save_result(tool, content, *, structured=False):
    name = re.sub(r'[^a-zA-Z0-9_-]+', '-', tool).strip('-') or 'Result'
    directory = constants.OUTPUT_DIR / name
    directory.mkdir(parents=True, exist_ok=True)
    extension = '.json' if structured else EXTENSIONS.get(tool, '.txt')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    for index in range(1000):
        path = directory / f'{stamp}{"_"+str(index) if index else ""}{extension}'
        try:
            with path.open('x', encoding='utf-8', newline='') as stream:
                stream.write(content)
            return path
        except FileExistsError:
            continue
    raise OSError('Impossible de créer un nom de rapport unique')
