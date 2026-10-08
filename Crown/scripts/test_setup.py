"""Installation smoke tests; run with the project's virtual environment."""
import asyncio
import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.deps import bootstrap
bootstrap()
from lib.localization import display_arabic
from lib.ui import CrownApp

spec = importlib.util.spec_from_file_location('installer', ROOT / 'lib/setup_modules.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
assert installer.dependencies_ready(ROOT / 'requirements.txt')
for module in installer.MODULES:
    __import__(module)
assert display_arabic('مرحبا') != 'مرحبا'

async def check_interface():
    with tempfile.TemporaryDirectory() as folder:
        app = CrownApp(boot=False, profile_path=Path(folder) / 'profile.json', welcome_links=False)
        async with app.run_test(size=(100, 30)) as pilot:
            app.motion = False
            await pilot.pause(0.1)
            assert app.query_one('#cards') is not None
            assert app.catalog
            app.action_search()
            await pilot.pause(0.1)
            await pilot.press('escape')
            await pilot.pause(0.1)
asyncio.run(check_interface())
print('Dependency imports, Arabic rendering, dashboard and search: OK')

