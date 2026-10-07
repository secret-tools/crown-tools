"""Compatibility boundary for the original 15 tool implementations."""
import importlib.util
from .constants import LEGACY_DIR
spec=importlib.util.spec_from_file_location('crown_original',LEGACY_DIR/'main.py')
legacy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
legacy._sound_enabled=False

from .localization import translate
import settings as legacy_settings
_original_translate=legacy.t

def tool_translate(key,lang='fr',**kwargs):
    entries=legacy_settings.TRANSLATIONS.get(key,{})
    if lang in entries:return _original_translate(key,lang,**kwargs)
    return translate(_original_translate(key,'en',**kwargs),lang)

legacy.t=tool_translate
