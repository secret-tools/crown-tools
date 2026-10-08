"""Resolve packaged dependencies before importing the UI."""
from pathlib import Path
import sys
import os
import subprocess
from .constants import APP_DIR, LEGACY_DIR, PROJECT_DIR

def bootstrap():
    # Direct `python main.py` uses the same dedicated runtime as start.bat.
    local_python=PROJECT_DIR/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if sys.prefix==sys.base_prefix and local_python.is_file() and Path(sys.executable).resolve()!=local_python.resolve():
        try:
            probe = subprocess.run(
                [str(local_python), '-c', 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            probe = None
        if probe is not None and probe.returncode == 0:
            os.execv(str(local_python),[str(local_python),*sys.argv])
    if sys.version_info < (3,12):
        raise RuntimeError('Python 3.12 ou plus requis / Python 3.12+ required')
    # The bundled binary wheels were built for Python 3.12.
    if sys.version_info[:2]==(3,12) and (APP_DIR/'packages').is_dir() and sys.prefix==sys.base_prefix:
        sys.path.insert(0,str(APP_DIR/'packages'))
    sys.path.insert(0,str(LEGACY_DIR))
