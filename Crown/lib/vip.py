"""VIP packs: v1 built-in data actions; v2 external Python code, not sandboxed."""
import hashlib
import asyncio
import base64
import os
import subprocess
from textual import work
from .constants import INPUT_DIR, resolve_relocated_input, resolve_input_path
import json
from pathlib import Path
import uuid
import zipfile
import time

_VIP_CACHE_FILE = Path(os.path.expandvars(r"%LOCALAPPDATA%\CrownTools\vip_cache.json"))

def _save_vip_path(path: str):
    """Persist the last successfully loaded VIP pack path."""
    try:
        _VIP_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _VIP_CACHE_FILE.write_text(
            json.dumps({"last_pack": str(path)}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass

def _load_vip_path() -> str | None:
    """Return the last saved VIP pack path, or None if not found / invalid."""
    try:
        data = json.loads(_VIP_CACHE_FILE.read_text(encoding="utf-8"))
        p = data.get("last_pack", "")
        if p and resolve_relocated_input(p).is_file():
            return str(resolve_relocated_input(p))
    except Exception:
        pass
    return None


from rich.text import Text
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Select, Static

VIP_COLORS = {
    'crown-bg':'#080609','crown-bg-alt':'#160b10','crown-border':'#49202a',
    'crown-accent':'#ff3452','crown-accent-2':'#a62039','crown-cyan':'#ff9aab',
    'crown-text':'#f6e9ed','crown-text-dim':'#ad8b95',
    'crown-success':'#91c7a9','crown-warning':'#ffb58d','crown-error':'#ff657c',
}

class VipCipher(Static):
    """Decorative terminal reveal, without simulated attacks or network activity."""
    def on_mount(self):
        import pyfiglet
        self.logo=pyfiglet.figlet_format('CROWN',font='ansi_shadow').rstrip().splitlines()
        self.started=time.monotonic();self.phase=0.
        self.styles.content_align=("center", "middle")
        self.set_interval(1/24,self.tick)
    def tick(self):
        if not self.is_mounted or self.app.screen is not self.screen:return
        phase=time.monotonic()-self.started if self.app.motion else 3.2
        if phase==self.phase:return
        self.phase=phase
        self.refresh()
    def render(self):
        width=min(140,max(1,self.content_size.width));height=min(40,max(1,self.content_size.height))
        phase=getattr(self,'phase',0.);logo=getattr(self,'logo',['CROWN'])
        if max(map(len,logo))>width-8 or height<17:logo=['C R O W N']
        center=max(2,(height-len(logo)-6)//2)
        overlays={}
        def line(y,text,ink):
            if not 0<=y<height:return
            text=text[:max(1,width-4)];start=max(0,(width-len(text))//2)
            for i,ch in enumerate(text):overlays.setdefault(y,{})[start+i]=(ch,ink)
        line(max(0,center-3),'[ CROWN / PRIVATE TERMINAL ]','#99616e')
        for row,text in enumerate(logo):
            revealed=max(0,min(len(text),int((phase-.25-row*.06)*len(text)/1.35)))
            tail=''.join('01ABCDEF'[(i+int(phase*15))%8] if c!=' ' else ' ' for i,c in enumerate(text[revealed:]))
            line(center+row,text[:revealed]+tail,'#ff3452' if row>1 else '#ffacbb')
        ready=phase>1.8
        line(center+len(logo)+1,'◆  VIP ON  /  ACCESS GRANTED  ◆' if ready else ':: INITIALISATION DE L’ESPACE VIP ::','#ffe3e9' if ready else '#a95569')
        line(center+len(logo)+3,self.app.username if ready else 'CHARGEMENT DU CATALOGUE PRIVÉ','#dca3b0')
        radius=int(min(1,phase/2.3)*min(width-6,64)/2)
        line(center+len(logo)+5,'━'*max(1,2*radius),'#8f243c')
        line(height-2,'ENTRÉE / PASSER','#79535d')
        out=Text(no_wrap=True,overflow='crop');glyphs='01ABCDEF:.'
        # Compute falling columns once per frame, not for every cell.
        columns=[]
        for x in range(width):
            if (x*37+11)%17<3:
                columns.append((x,(phase*(7+(x%5))+x*13)%(height+12)))
        frame=int(phase*5)
        for y in range(height):
            chars=[' ']*width
            inks=[None]*width
            for x,head in columns:
                age=head-y
                if 0<=age<9:
                    chars[x]=glyphs[(x*11+y*7+frame)%len(glyphs)]
                    inks[x]='#b63c53' if age<1 else '#582131' if age<4 else '#261018'
            for x,(ch,ink) in overlays.get(y,{}).items():
                chars[x]=ch;inks[x]=ink
            # A single span for each adjacent run; blank areas need no style.
            start=0
            for x in range(1,width+1):
                if x==width or inks[x]!=inks[start]:
                    out.append(''.join(chars[start:x]),style=inks[start])
                    start=x
            if y<height-1:out.append('\n')
        return out

class VipArrival(ModalScreen):
    BINDINGS=[Binding('enter','continue',show=False),Binding('escape','continue',show=False)]
    DEFAULT_CSS="""
    VipArrival {background:#080609;}
    #vip-cipher {width:100%;height:100%;background:#080609;}
    """
    def compose(self):yield VipCipher(id='vip-cipher')
    def on_mount(self):
        self.finished=False
        self.set_timer(3.2 if self.app.motion else .01,self.action_continue)
    def action_continue(self):
        if not self.finished:
            self.finished=True;self.dismiss()

ACTIONS = {'text_stats', 'sha512', 'uuid'}

def load_pack(path):
    path = resolve_input_path(path)
    if path.stat().st_size <= 200_000_000:
        with zipfile.ZipFile(path) as probe:
            if 'vip.json' in probe.namelist() and probe.getinfo('vip.json').file_size <= 1_000_000:
                manifest = json.loads(probe.read('vip.json'))
                if isinstance(manifest, dict) and manifest.get('version') == 2:
                    from .vip_bundle import load_bundle
                    return load_bundle(path)
    if path.stat().st_size > 5_000_000:
        raise ValueError('Archive trop volumineuse (5 Mo maximum).')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != 'vip.json':
            raise ValueError('Le ZIP doit contenir uniquement vip.json à sa racine.')
        entry = entries[0]
        if entry.file_size > 64_000 or entry.flag_bits & 1:
            raise ValueError('Manifeste trop volumineux ou archive chiffrée.')
        with archive.open(entry) as source:
            raw = source.read(64_001)
        if len(raw) > 64_000:
            raise ValueError('Manifeste trop volumineux.')
        pack = json.loads(raw)
    if not isinstance(pack, dict) or pack.get('version') != 1:
        raise ValueError('Format VIP non reconnu.')
    def label(value, limit):
        return isinstance(value, str) and 0 < len(value) <= limit and all(c.isprintable() for c in value)
    if not label(pack.get('name'), 60):
        raise ValueError('Nom du pack invalide.')
    modules = pack.get('modules')
    if not isinstance(modules, list) or not 1 <= len(modules) <= 100:
        raise ValueError('Le pack doit contenir entre 1 et 100 options.')
    for module in modules:
        if not isinstance(module, dict) or not label(module.get('name'), 60) or not label(module.get('description'), 200):
            raise ValueError('Description de module invalide.')
        if module.get('action') not in ACTIONS:
            raise ValueError('Action VIP non prise en charge.')
        if not label(module.get('category', 'VIP'), 40) or '|' in module['name'] or '|' in module.get('category', 'VIP'):
            raise ValueError('Catégorie VIP invalide.')
    identities = [(m.get('category', 'VIP'), m['name']) for m in modules]
    if len(set(identities)) != len(identities) or len({m['name'] for m in modules}) != len(modules):
        raise ValueError('Les noms des options VIP doivent être uniques.')
    pack['_archive_path']=str(path.resolve())
    return pack

def execute(action, value):
    if len(value) > 100_000:
        raise ValueError('Entrée trop longue.')
    if action == 'text_stats':
        return json.dumps({'caractères': len(value), 'mots': len(value.split()), 'octets_utf8': len(value.encode())}, ensure_ascii=False, indent=2)
    if action == 'sha512':
        return hashlib.sha512(value.encode()).hexdigest()
    if action == 'uuid':
        count = int(value.strip() or '1')
        if not 1 <= count <= 50:
            raise ValueError('Choisis un nombre entre 1 et 50.')
        return '\n'.join(str(uuid.uuid4()) for _ in range(count))
    raise ValueError('Action non prise en charge.')

class VipPicker(ModalScreen):
    BINDINGS = [Binding('escape', 'cancel', show=False)]
    DEFAULT_CSS = '''
    VipPicker {align:center middle;background:$crown-bg 95%;}
    #vip-picker {width:76;max-width:96%;height:auto;max-height:96%;padding:1 2;border:round #b99451;background:#121009;overflow-y:auto;}
    #vip-picker Static {height:auto;margin-bottom:1;}
    #vip-picker Input, #vip-picker Select {width:100%;}
    #vip-picker Button {width:100%;margin-top:1;}
    #vip-error {color:#ff718b;}
    '''
    def compose(self):
        with Vertical(id='vip-picker'):
            yield Static('◇  VIP ZONE / IMPORTER UN PACK', classes='dark-kicker')
            yield Static('Choisis ton fichier ZIP dans la fenêtre de sélection.')
            yield Button('Choisir un fichier ZIP…', id='vip-browse')
            yield Input(placeholder='C:\\chemin\\vers\\le\\dossier', id='vip-directory')
            yield Button('Afficher les fichiers ZIP', id='vip-list')
            yield Select([], prompt='Sélectionner un pack VIP', id='vip-files')
            yield Static('', id='vip-error')
            yield Button('Activer le pack VIP', id='vip-activate', disabled=True)
            yield Button('Annuler', id='vip-cancel')
    def on_mount(self):
        self.query_one('#vip-browse').focus()
        if os.name == 'nt':
            self.call_after_refresh(self.browse_zip)

    @work(exclusive=True, group='vip-file-dialog')
    async def browse_zip(self):
        if os.name != 'nt':
            self.query_one('#vip-error', Static).update('Indique le dossier ci-dessous pour choisir ton ZIP.')
            return
        self.query_one('#vip-browse', Button).disabled = True
        script = r"""
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Choisir le pack VIP'
$dialog.Filter = 'Pack VIP (*.zip)|*.zip'
$dialog.CheckFileExists = $true
$dialog.Multiselect = $false
$dialog.InitialDirectory = $env:CROWN_INPUT_DIR
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
try {
    if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
        [Console]::Write($dialog.FileName)
    }
} finally {
    $dialog.Dispose()
    $owner.Dispose()
}
"""
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                'powershell.exe', '-NoProfile', '-STA', '-EncodedCommand', encoded,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW, env={**os.environ,'CROWN_INPUT_DIR':str(INPUT_DIR)})
            stdout, stderr = await process.communicate()
            if process.returncode:
                raise OSError('La fenêtre de sélection ne peut pas s’ouvrir. Utilise le dossier ci-dessous.')
            selected = stdout.decode('utf-8-sig').strip()
            if not self.query('#vip-browse'):
                return
            if selected:
                self.activate_path(selected)
            else:
                self.action_cancel()
        except (OSError, UnicodeError) as error:
            matches = self.query('#vip-error')
            if matches:
                matches.first().update(Text(str(error)))
        finally:
            if process is not None and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass
            buttons = self.query('#vip-browse')
            if buttons:
                buttons.first().disabled = False

    def activate_path(self, selected):
        try:
            pack = load_pack(selected)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
            self.query_one('#vip-error', Static).update(Text('Pack refusé : ' + str(error)))
            return
        _save_vip_path(selected)
        self.dismiss(pack)
    def on_input_changed(self, event):
        self.query_one('#vip-activate', Button).disabled = True
        self.query_one('#vip-files', Select).set_options([])
    def list_files(self):
        try:
            directory = resolve_input_path(self.query_one('#vip-directory', Input).value)
            if not directory.is_dir():
                raise ValueError('Répertoire introuvable.')
            paths = sorted((p for p in directory.iterdir() if p.suffix.lower() == '.zip' and p.is_file()), key=lambda p:p.name.casefold())
            if not paths:
                raise ValueError('Aucun fichier ZIP dans ce dossier.')
            if len(paths) > 200:
                raise ValueError('Choisis un dossier contenant au maximum 200 ZIP.')
            self.query_one('#vip-files', Select).set_options([(p.name, str(p.resolve())) for p in paths])
            self.query_one('#vip-error', Static).update('')
        except (OSError, ValueError) as error:
            matches = self.query('#vip-error')
            if matches:
                matches.first().update(Text(str(error)))
    def on_select_changed(self, event):
        self.query_one('#vip-activate', Button).disabled = event.value is Select.BLANK
    def on_input_submitted(self, event):
        event.stop(); self.list_files()
    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == 'vip-browse':
            self.browse_zip()
        elif event.button.id == 'vip-list':
            self.list_files()
        elif event.button.id == 'vip-cancel':
            self.action_cancel()
        elif event.button.id == 'vip-activate':
            selected = self.query_one('#vip-files', Select).value
            if selected is Select.BLANK:
                return
            self.activate_path(selected)
    def action_cancel(self):
        self.dismiss(None)
