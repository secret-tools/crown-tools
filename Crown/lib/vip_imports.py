"""Explicit local Python imports, stored independently from data-only ZIP packs.

An import validates syntax and copies bytes; it never imports or executes Python.
Launching is an explicit terminal action, in a child process, not a sandbox.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from rich.text import Text
from textual.app import SuspendNotSupported
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Select, Static

from .config import read_settings, write_profile
from .vip_policy import require_allowed_module
from .constants import INPUT_DIR, OUTPUT_DIR, resolve_input_path

MAX_SOURCE = 2_000_000

def clean_label(value, limit):
    if not isinstance(value, str):
        raise ValueError('Nom ou catégorie invalide.')
    value=value.strip()
    if not 1<=len(value)<=limit or '|' in value or not all(c.isprintable() for c in value):
        raise ValueError(f'Utilise entre 1 et {limit} caractères, sans le caractère |.')
    return value

def imports_root(settings_path):
    return Path(settings_path).parent/'vip-options'

def read_imports(settings_path):
    entries=read_settings(settings_path).get('vip_imports',[])
    if not isinstance(entries,list) or len(entries)>200:
        raise ValueError('La liste des options importées est invalide dans settings.json.')
    result=[];ids=set();names=set()
    for entry in entries:
        if not isinstance(entry,dict) or not re.fullmatch('[0-9a-f]{32}',str(entry.get('id',''))):
            raise ValueError('Identifiant d’option importée invalide.')
        try:require_allowed_module(entry)
        except ValueError:continue
        name=clean_label(entry.get('name'),60);category=clean_label(entry.get('category'),40)
        if entry['id'] in ids or name.casefold() in names:
            raise ValueError('Option importée en double dans settings.json.')
        if not re.fullmatch('[0-9a-f]{64}',str(entry.get('sha256',''))):
            raise ValueError('Empreinte de fichier importé invalide.')
        ids.add(entry['id']);names.add(name.casefold())
        result.append(dict(id=entry['id'],name=name,category=category,sha256=entry['sha256']))
    return result

def script_path(settings_path,entry):
    identifier=entry.get('id','')
    if not isinstance(identifier,str) or not re.fullmatch('[0-9a-f]{32}',identifier):
        raise ValueError('Identifiant d’option invalide.')
    root=imports_root(settings_path).resolve()
    path=(root/identifier/'main.py').resolve()
    if not path.is_relative_to(root):
        raise ValueError('Chemin du script invalide.')
    return path

def import_script(settings_path,source,name,category,reserved_names=()):
    name=clean_label(name,60);category=clean_label(category,40)
    require_allowed_module({'name':name,'category':category,'entry':str(source)})
    entries=read_imports(settings_path)
    if len(entries)>=200:raise ValueError('Maximum : 200 options importées.')
    names={n.casefold() for n in reserved_names}|{e['name'].casefold() for e in entries}
    if name.casefold() in names:raise ValueError('Ce nom existe déjà. Choisis un autre nom.')
    path=resolve_input_path(source)
    if path.suffix.lower()!='.py' or not path.is_file():
        raise ValueError('Sélectionne un fichier Python .py existant.')
    with path.open('rb') as stream:content=stream.read(MAX_SOURCE+1)
    if len(content)>MAX_SOURCE:raise ValueError('Fichier trop volumineux (2 Mo maximum).')
    try:compile(content,str(path),'exec')
    except (SyntaxError,ValueError) as error:
        raise ValueError(f'Python invalide : {error}') from error
    entry=dict(id=uuid.uuid4().hex,name=name,category=category,sha256=hashlib.sha256(content).hexdigest())
    destination=script_path(settings_path,entry)
    destination.parent.mkdir(parents=True,exist_ok=False)
    try:
        destination.write_bytes(content)
        write_profile(settings_path,{'vip_imports':entries+[entry]})
    except OSError:
        # Roll back only the new file and its empty, uniquely owned directory.
        destination.unlink(missing_ok=True)
        destination.parent.rmdir()
        raise
    return entry

def forget_script(settings_path,identifier):
    entries=read_imports(settings_path)
    write_profile(settings_path,{'vip_imports':[e for e in entries if e['id']!=identifier]})

def checked_script(settings_path,entry):
    path=script_path(settings_path,entry)
    try:
        with path.open('rb') as stream:content=stream.read(MAX_SOURCE+1)
    except OSError as error:
        raise ValueError('Le script conservé est introuvable. Retire l’option puis importe-la à nouveau.') from error
    if len(content)>MAX_SOURCE or hashlib.sha256(content).hexdigest()!=entry['sha256']:
        raise ValueError('Le script conservé a changé. Retire l’option puis importe la nouvelle version.')
    return path

def run_in_terminal(path, name):
    """Called inside App.suspend; catch interruption here so Textual can resume."""
    require_allowed_module({'name':name,'entry':str(path)})
    process=None
    path = Path(path)
    try:
        print('\n◆ CROWN VIP / '+name+'\n',flush=True)
        env=dict(os.environ,PYTHONUTF8='1',CROWN_INPUT_DIR=str(INPUT_DIR),CROWN_OUTPUT_DIR=str(OUTPUT_DIR))
        process=subprocess.Popen([sys.executable,'-u',str(path)],cwd=str(path.parent),env=env)
        code=process.wait()
        lang = os.environ.get('CROWN_LANG', 'fr')
        end_msgs = {
            'fr': f'\nFin de l’option · code {code}',
            'en': f'\nOption finished · code {code}',
            'es': f'\nOpción finalizada · código {code}',
            'de': f'\nOption beendet · Code {code}',
            'zh': f'\n选项已结束 · 代码 {code}',
            'ar': f'\nانتهى الخيار · الرمز {code}',
        }
        print(end_msgs.get(lang, end_msgs['en']), flush=True)
    except KeyboardInterrupt:
        lang = os.environ.get('CROWN_LANG', 'fr')
        int_msgs = {
            'fr': '\nOption interrompue.',
            'en': '\nOption interrupted.',
            'es': '\nOpción interrumpida.',
            'de': '\nOption unterbrochen.',
            'zh': '\n选项已中断。',
            'ar': '\nتمت مقاطعة الخيار.',
        }
        print(int_msgs.get(lang, int_msgs['en']), flush=True)
    except OSError as error:
        lang = os.environ.get('CROWN_LANG', 'fr')
        err_prefix = 'Lancement impossible : ' if lang == 'fr' else 'Launch impossible : '
        print('\n' + err_prefix + str(error), flush=True)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
        lang = os.environ.get('CROWN_LANG', 'fr')
        prompts = {
            'fr': '\nEntrée pour revenir à Crown… ',
            'en': '\nPress Enter to return to Crown… ',
            'es': '\nPresiona Enter para volver a Crown… ',
            'de': '\nDrücke Enter, um zu Crown zurückzukehren… ',
            'zh': '\n按回车键返回 Crown… ',
            'ar': '\nاضغط Enter للعودة إلى Crown… ',
        }
        prompt = prompts.get(lang, prompts['en'])
        try:input(prompt)
        except (EOFError,KeyboardInterrupt,OSError):pass

class PythonTree(DirectoryTree):
    def filter_paths(self,paths):
        for path in paths:
            try:
                if path.is_dir() or path.suffix.lower()=='.py':yield path
            except OSError:continue

class PythonPicker(ModalScreen):
    BINDINGS=[Binding('escape','cancel',show=False)]
    DEFAULT_CSS='''
    PythonPicker {align:center middle;background:$crown-bg 95%;}
    #python-picker {width:84;max-width:96%;height:90%;border:round $crown-accent;background:$crown-bg-alt;padding:1;}
    #python-picker Static {height:auto;}
    #python-location {height:3;}
    #python-tree {height:1fr;min-height:3;background:$crown-bg;}
    #python-picker-actions {height:3;}
    #python-picker-actions Button {width:1fr;min-width:0;}
    #python-picker-error {height:auto;color:$crown-error;}
    '''
    def __init__(self,start):
        super().__init__();self.start=Path(start)
    def compose(self):
        with Vertical(id='python-picker'):
            yield Static('CHOISIR UN FICHIER PYTHON',classes='eyebrow')
            yield Input(str(self.start),placeholder='Dossier ou chemin du .py · Entrée pour ouvrir',id='python-location')
            yield PythonTree(self.start,id='python-tree')
            yield Static('',id='python-picker-error')
            with Horizontal(id='python-picker-actions'):
                yield Button('Ouvrir ce chemin',id='python-go')
                yield Button('Annuler',id='python-cancel')
    def on_mount(self):self.query_one('#python-tree').focus()
    def open_location(self):
        path=resolve_input_path(self.query_one('#python-location',Input).value)
        try:
            if path.is_dir():
                self.query_one('#python-tree',PythonTree).path=path
                self.query_one('#python-picker-error',Static).update('')
            elif path.is_file() and path.suffix.lower()=='.py':self.dismiss(str(path.resolve()))
            else:raise ValueError('Choisis un dossier ou un fichier .py existant.')
        except (OSError,ValueError) as error:self.query_one('#python-picker-error',Static).update(Text(str(error)))
    def on_directory_tree_file_selected(self,event):
        event.stop()
        if event.path.suffix.lower()=='.py':self.dismiss(str(event.path.resolve()))
    def on_input_submitted(self,event):event.stop();self.open_location()
    def on_button_pressed(self,event):
        event.stop()
        if event.button.id=='python-go':self.open_location()
        else:self.action_cancel()
    def action_cancel(self):self.dismiss(None)

class VipImportScreen(ModalScreen):
    BINDINGS=[Binding('escape','cancel',show=False)]
    DEFAULT_CSS='''
    VipImportScreen {align:center middle;background:$crown-bg 95%;}
    #vip-import-shell {width:78;max-width:96%;height:auto;max-height:96%;border:round $crown-accent;background:$crown-bg-alt;padding:1 2;}
    #vip-import-form {height:auto;max-height:28;}
    #vip-import-form Static {height:auto;margin-top:1;}
    #vip-import-form Input, #vip-import-form Select {height:3;}
    #vip-import-file-row {height:3;}
    #vip-import-file {width:1fr;}
    #vip-browse {width:14;min-width:0;}
    #vip-import-actions {height:3;margin-top:1;}
    #vip-import-actions Button {width:1fr;min-width:0;}
    #vip-import-save {background:$crown-accent-2;color:$crown-text;}
    #vip-import-error {height:auto;color:$crown-error;}
    #vip-import-note {color:$crown-text-dim;}
    '''
    def compose(self):
        categories=list(self.app.categories)
        with Vertical(id='vip-import-shell'):
            with VerticalScroll(id='vip-import-form'):
                yield Static('＋  AJOUTER UNE OPTION VIP',classes='eyebrow')
                yield Static('Fichier Python')
                with Horizontal(id='vip-import-file-row'):
                    yield Input(placeholder='Colle le chemin de ton fichier .py',id='vip-import-file')
                    yield Button('Parcourir',id='vip-browse')
                yield Static('Nom affiché dans le menu')
                yield Input(placeholder='Ex. Mon outil',max_length=60,id='vip-import-name')
                yield Static('Catégorie')
                selected=categories.index(self.app.category) if self.app.category in categories else 0
                yield Select([(c,i) for i,c in enumerate(categories)]+[('＋ Nouvelle catégorie',-1)],value=selected if categories else -1,allow_blank=False,id='vip-import-category')
                yield Input(placeholder='Nom de la nouvelle catégorie',max_length=40,id='vip-import-new-category')
                yield Static('Le .py sera copié et ajouté au menu, sans être exécuté. Lance uniquement tes scripts de confiance : ils utilisent les droits de ta session.',id='vip-import-note')
            yield Static('',id='vip-import-error')
            with Horizontal(id='vip-import-actions'):
                yield Button('Annuler',id='vip-import-cancel')
                yield Button('Ajouter au VIP',id='vip-import-save')
    def on_mount(self):
        self.query_one('#vip-import-new-category').display=self.query_one('#vip-import-category',Select).value==-1
        self.query_one('#vip-import-file').focus()
    def on_select_changed(self,event):
        if event.select.id=='vip-import-category':self.query_one('#vip-import-new-category').display=event.value==-1
    def selected_file(self,path):
        if path:
            self.query_one('#vip-import-file',Input).value=path
            if not self.query_one('#vip-import-name',Input).value:
                self.query_one('#vip-import-name',Input).value=Path(path).stem.replace('_',' ')[:60]
            self.query_one('#vip-import-name').focus()
    def save(self):
        try:
            category=self.query_one('#vip-import-category',Select).value
            category=self.query_one('#vip-import-new-category',Input).value if category==-1 else self.app.categories[category]
            entry=import_script(self.app.profile_path,self.query_one('#vip-import-file',Input).value,
                                self.query_one('#vip-import-name',Input).value,category,self.app.descriptions)
        except (OSError,ValueError) as error:
            self.query_one('#vip-import-error',Static).update(Text(str(error)));return
        self.dismiss(entry)
    def on_button_pressed(self,event):
        event.stop()
        if event.button.id=='vip-import-cancel':self.action_cancel()
        elif event.button.id=='vip-import-save':self.save()
        elif event.button.id=='vip-browse':
            value=self.query_one('#vip-import-file',Input).value.strip().strip('"')
            start=resolve_input_path(value) if value else INPUT_DIR
            if not start.is_dir():start=start.parent
            if not start.is_dir():start=Path.home()
            self.app.push_screen(PythonPicker(start),self.selected_file)
    def action_cancel(self):self.dismiss(None)

class ImportedScriptScreen(ModalScreen):
    BINDINGS=[Binding('escape','back',show=False)]
    DEFAULT_CSS='''
    ImportedScriptScreen {align:center middle;background:$crown-bg;}
    #imported-script {width:76;max-width:96%;height:auto;max-height:96%;padding:1 2;border:round $crown-border;background:$crown-bg-alt;overflow-y:auto;}
    #imported-script Static {height:auto;margin-bottom:1;}
    #imported-script Button {width:100%;height:3;}
    #imported-script-error {color:$crown-error;}
    #imported-run {background:$crown-accent-2;color:$crown-text;}
    '''
    def __init__(self,entry):super().__init__();self.entry=entry
    def compose(self):
        with Vertical(id='imported-script'):
            yield Static(Text('◆ VIP ON / '+self.entry['name']),classes='eyebrow')
            yield Static(Text(self.entry['category']))
            yield Static('Script Python local. Il s’ouvre dans ce terminal avec ses propres menus et champs de saisie. À sa fermeture, Entrée ramène au VIP.')
            yield Static('Exécute uniquement un script de confiance. Il possède les mêmes droits que Crown ; ce mode n’est pas un bac à sable.')
            yield Static('',id='imported-script-error')
            yield Button('Lancer dans le terminal  ↗',id='imported-run')
            yield Button('Retirer cette option du menu',id='imported-remove')
            yield Button('← Retour au VIP',id='imported-back')
    def on_mount(self):self.query_one('#imported-run').focus()
    def launch(self):
        try:
            path=checked_script(self.app.profile_path,self.entry)
            with self.app.suspend():run_in_terminal(path,self.entry['name'])
        except (OSError,ValueError,SuspendNotSupported) as error:
            self.query_one('#imported-script-error',Static).update(Text(str(error)))
    def on_button_pressed(self,event):
        event.stop()
        if event.button.id=='imported-run':self.launch()
        elif event.button.id=='imported-remove':
            try:forget_script(self.app.profile_path,self.entry['id'])
            except (OSError,ValueError) as error:
                self.query_one('#imported-script-error',Static).update(Text(str(error)));return
            self.dismiss(True)
        else:self.action_back()
    def action_back(self):self.dismiss(False)
