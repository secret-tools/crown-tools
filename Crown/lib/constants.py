"""Project paths, independent of the working directory."""
from pathlib import Path
APP_DIR=Path(__file__).resolve().parents[1]
PROJECT_DIR=APP_DIR.parent
LEGACY_DIR=APP_DIR/'lib'/'legacy'
STYLES_DIR=APP_DIR/'styles'
INPUT_DIR=PROJECT_DIR/'Input'
OUTPUT_DIR=PROJECT_DIR/'Output'
DOCS_DIR=PROJECT_DIR/'Docs'
SCREENSHOTS_DIR=OUTPUT_DIR/'Screenshots'

def resolve_input_path(value):
    """Relative user files belong to Input; explicit absolute paths stay valid."""
    path=Path(str(value).strip().strip('"').strip("'")).expanduser()
    if path.is_absolute():return resolve_relocated_input(path)
    if path.drive:raise ValueError('Chemin absolu requis pour un lecteur / Absolute drive path required')
    parts=path.parts
    if parts and parts[0].casefold() in {'input','crown - input'}:parts=parts[1:]
    candidate=INPUT_DIR.joinpath(*parts).resolve()
    if not candidate.is_relative_to(INPUT_DIR.resolve()):
        raise ValueError('Chemin relatif hors Input : utiliser un chemin absolu / Use an absolute path outside Input')
    return candidate

def ensure_data_dirs():
    for directory in (INPUT_DIR,OUTPUT_DIR,SCREENSHOTS_DIR):directory.mkdir(parents=True,exist_ok=True)

def resolve_relocated_input(value):
    """Resolve old project-owned input paths without rewriting user settings."""
    path=Path(value).expanduser()
    if path.exists():return path
    if not path.is_absolute():return path
    for old,new in [(PROJECT_DIR/'VIP-Test',INPUT_DIR/'VIP-Test'),(PROJECT_DIR/'Crown - Input',INPUT_DIR),(PROJECT_DIR.parent/'Crown-Tools'/'Input',INPUT_DIR)]:
        try:relative=path.relative_to(old)
        except ValueError:continue
        candidate=new/relative
        if candidate.exists() and candidate.resolve().is_relative_to(INPUT_DIR.resolve()):return candidate
    return path
