"""Local user preferences and first-run setup; no account or network required."""
import json
import os
import re
from .themes import PALETTES
from .localization import LANGUAGES
from pathlib import Path

PROFILE_PATH=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.config'))/'CrownTools'/'settings.json'
LEGACY_PROFILE_PATH=PROFILE_PATH.with_name('profile.json')
CROWN_PROFILE_PATH=PROFILE_PATH.parent.parent/'CrownTools'/'settings.json'
CROWN_LEGACY_PROFILE_PATH=CROWN_PROFILE_PATH.with_name('profile.json')
PREVIOUS_PROFILE_PATH=PROFILE_PATH.parent.parent/'LarpTools'/'profile.json'

def read_settings(path):
    path=Path(path)
    if path==PROFILE_PATH and not path.exists():
        for previous_path in (CROWN_PROFILE_PATH,CROWN_LEGACY_PROFILE_PATH,LEGACY_PROFILE_PATH,PREVIOUS_PROFILE_PATH):
            if previous_path == path:continue
            previous=read_settings(previous_path)
            if previous:
                try:write_profile(path,previous)
                except OSError:pass
                return previous
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict):return {}
        if isinstance(data.get('username'),str) and data['username'].strip().casefold()=='kaos':
            data['username']='Crown'
            try:write_profile(path,data)
            except OSError:pass
        return data
    except (OSError,ValueError):return {}

def read_vip(path):
    vip=read_settings(path).get('vip',{})
    if not isinstance(vip,dict):return {}
    if vip.get('key')!='2027':return {}
    zip_path=vip.get('zip_path','')
    if isinstance(zip_path,str) and zip_path:
        from .constants import resolve_relocated_input
        zip_path=str(resolve_relocated_input(zip_path))
    return {'key':'2027','zip_path':zip_path if isinstance(zip_path,str) else ''}

def write_vip(path,data):
    settings=read_settings(path)
    settings['vip']=data
    write_profile(path,settings)

def read_profile(path):
    path=Path(path)
    try:
        data=read_settings(path)
        if not isinstance(data,dict):return {}
        if not isinstance(data.get('username'),str) or not 1<=len(data['username'].strip())<=24:return {}
        if data.get('language') not in LANGUAGES:return {}
        if data.get('theme') not in PALETTES:return {}
        if data.get('accent') and not re.fullmatch(r'#[0-9a-fA-F]{6}',str(data['accent'])):return {}
        return {k:data[k] for k in ('username','language','theme','accent','motion') if k in data}
    except (OSError,ValueError):return {}

def write_profile(path,data):
    path=Path(path)
    # Profile edits must not erase the remembered VIP access.
    try:
        existing=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):existing={}
    if isinstance(existing,dict):data={**existing,**data}
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

