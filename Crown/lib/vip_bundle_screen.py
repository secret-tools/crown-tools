"""Lancement direct des options Python d'un pack VIP."""
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from rich.text import Text
from textual.app import SuspendNotSupported
from textual.screen import ModalScreen
from textual.widgets import Static
from .vip_bundle import validate
from .vip_imports import ImportedScriptScreen, run_in_terminal


def resolve_entry_path(root: Path, entry_rel: str, lang: str) -> Path:
    """Résout le chemin du script selon la langue du profil Crown (fr, en, es, de, zh, ar)."""
    p_str = str(entry_rel).replace("\\", "/")
    
    # 1. Vérifier si un script dédié à la langue exacte existe (<lang>.py, ex: es.py, de.py)
    for ext in ["/fr.py", "/en.py"]:
        if p_str.endswith(ext):
            candidate = p_str[:-len(ext)] + f"/{lang}.py"
            if (root / candidate).is_file():
                return root / candidate

    # 2. Si le profil Crown est en Français, utiliser fr.py
    if lang == "fr":
        for ext in ["/en.py"]:
            if p_str.endswith(ext):
                candidate = p_str[:-len(ext)] + "/fr.py"
                if (root / candidate).is_file():
                    return root / candidate
        return root / entry_rel

    # 3. Pour TOUTES les autres langues (English, Español, Deutsch, 中文, العربية) :
    # Si le script par défaut est en français (fr.py), basculer sur en.py (standard international)
    if p_str.endswith("/fr.py"):
        candidate = p_str[:-5] + "en.py"
        if (root / candidate).is_file():
            return root / candidate
    elif p_str.endswith("fr.py"):
        candidate = p_str[:-5] + "en.py"
        if (root / candidate).is_file():
            return root / candidate

    return root / entry_rel


def launch_bundle_module(app, module, archive):
    """Lance directement une option Python du pack VIP sans passer par un écran intermédiaire."""
    try:
        from .vip_policy import require_allowed_module
        require_allowed_module(module)
        from .vip_integrated_screen import get_extracted_vip_root
        root = get_extracted_vip_root(archive)

        # Langue du profil Crown (ex: 'fr', 'en')
        lang = getattr(app, 'lang', 'fr') or 'fr'
        target_script = resolve_entry_path(root, module['entry'], lang)

        # Synchroniser les fichiers de configuration de la suite pour que get_settings().lang lise la bonne langue
        settings_payload = {
            "language": "en" if lang == "en" else "fr",
            "theme": "red",
            "username": getattr(app, 'username', 'Operator')
        }
        for cfg_path in [
            root / "config" / "settings.json",
            root / "tools" / "config" / "settings.json",
            root / "tools" / "lib" / "config" / "settings.json",
        ]:
            try:
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(settings_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        old_pythonpath = os.environ.get('PYTHONPATH')
        os.environ['PYTHONPATH'] = os.pathsep.join([str(root), str(root / 'tools')] + ([old_pythonpath] if old_pythonpath else []))
        os.environ['CROWN_LANG'] = lang
        os.environ['CROWN_MODULE_NAME'] = module['name']
        os.environ['CROWN_MODULE_CAT'] = module.get('category', 'VIP')
        try:
            with app.suspend():
                run_in_terminal(target_script, module['name'])
        finally:
            if old_pythonpath is None:
                os.environ.pop('PYTHONPATH', None)
            else:
                os.environ['PYTHONPATH'] = old_pythonpath
            os.environ.pop('CROWN_LANG', None)
            os.environ.pop('CROWN_MODULE_NAME', None)
            os.environ.pop('CROWN_MODULE_CAT', None)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, SuspendNotSupported) as error:
        if hasattr(app, 'notify'):
            app.notify(str(error), severity='error')


class BundleScriptScreen(ImportedScriptScreen):
    """Ancien écran modal conservé pour compatibilité."""
    def __init__(self, module, archive):
        super().__init__(module)
        self.archive = archive

    def on_mount(self):
        super().on_mount()
        self.query_one('#imported-remove').remove()
        self.query_one('#imported-script-error', Static).update('Les fichiers enregistrés dans le dossier temporaire seront supprimés à la fermeture. Choisis un autre dossier pour conserver tes résultats.')

    def launch(self):
        launch_bundle_module(self.app, self.entry, self.archive)
        self.dismiss(False)
