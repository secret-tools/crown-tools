"""First-run and profile configuration screen."""
import re
from textual.screen import ModalScreen
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.widgets import Static, Input, Button, Select, Switch
from .config import write_profile
from .themes import PALETTES
from .localization import LANGUAGES, translate, display_arabic

class ProfileScreen(ModalScreen):
    def __init__(self,first=False):
        super().__init__();self.first=first
    def compose(self):
        with Vertical(id='profile-shell'):
            with VerticalScroll(id='profile-box'):
                yield Static('C R O W N  /  BIENVENUE',id='profile-kicker')
                yield Static('Ton espace. Ton style.',id='profile-title')
                yield Static('Enregistré sur ce compte Windows.',id='profile-intro')
                yield Static('01  /  Pseudo',classes='profile-label')
                yield Input(value=self.app.username if self.app.profile else '',placeholder='Ex. Alex',max_length=24,id='profile-name')
                yield Static('02  /  Langue',classes='profile-label')
                yield Select([(display_arabic(name),key) for key,name in LANGUAGES.items()],value=self.app.lang,allow_blank=False,id='profile-language')
                yield Static('03  /  Palette de couleurs',classes='profile-label')
                yield Select([(name,key) for key,(name,*_) in PALETTES.items()],value=self.app.active_theme,allow_blank=False,id='profile-theme')
                yield Input(value=self.app.accent or '',placeholder='Couleur personnalisée #RRGGBB (facultatif)',id='profile-accent')
                with Horizontal(id='profile-motion-row'):
                    yield Static('Animations',id='profile-motion-label')
                    yield Switch(value=self.app.motion,id='profile-motion')
            yield Static('',id='profile-error')
            with Horizontal(id='profile-actions'):
                yield Button('ENREGISTRER ET CONTINUER  →',id='profile-save',variant='primary')
                if not self.first:yield Button('Annuler',id='profile-cancel')
    def on_mount(self):
        self.app.localize(self);self.query_one('#profile-name',Input).focus()
    def on_select_changed(self,event):
        if event.select.id=='profile-theme' and self.is_mounted:
            custom=self.query_one('#profile-accent',Input)
            custom.disabled=event.value=='rainbow'
            if custom.disabled:custom.value=''
        if event.select.id=='profile-language' and self.is_mounted and event.value in LANGUAGES:
            self.app.localize(self,language=event.value)
    async def on_button_pressed(self,event):
        event.stop()
        if event.button.id=='profile-cancel':self.dismiss();return
        if event.button.id!='profile-save':return
        name=self.query_one('#profile-name',Input).value.strip()
        accent=self.query_one('#profile-accent',Input).value.strip()
        error=self.query_one('#profile-error',Static)
        lang=self.query_one('#profile-language',Select).value
        if not name or len(name)>24 or any(not c.isprintable() for c in name):
            error.update(translate('Entre un pseudo de 1 à 24 caractères.',lang));return
        if accent and not re.fullmatch(r'#[0-9a-fA-F]{6}',accent):
            error.update(translate('Format attendu : #RRGGBB.',lang));return
        data=dict(username=name,language=self.query_one('#profile-language',Select).value,theme=self.query_one('#profile-theme',Select).value,accent=accent,motion=self.query_one('#profile-motion',Switch).value)
        try:write_profile(self.app.profile_path,data)
        except OSError:
            error.update(translate('Sauvegarde impossible. Réessaie.',lang));return
        self.app.profile=data
        self.app.load_preferences()
        self.dismiss()
        self.app.call_after_refresh(self.app.profile_updated)
