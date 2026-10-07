"""Secret area presentation: confirmation and a construction placeholder."""
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input


class DarkConfirmation(ModalScreen[bool]):
    BINDINGS=[Binding('escape','cancel',show=False)]

    def compose(self):
        with Vertical(id='dark-confirm'):
            yield Static('◈',classes='dark-emblem')
            yield Static(self.app.tr('ZONE VIP'),classes='dark-kicker')
            yield Static(self.app.tr('Vous êtes sur le point d’entrer dans la zone VIP. Souhaitez-vous continuer ?'),id='dark-question')
            with Horizontal(id='dark-actions'):
                yield Button(self.app.tr('Non, revenir'),id='dark-cancel')
                yield Button(self.app.tr('Oui, entrer'),id='dark-accept')

    def on_mount(self):
        self.query_one('#dark-cancel').focus()

    def on_button_pressed(self,event):
        event.stop()
        self.dismiss(event.button.id=='dark-accept')

    def action_cancel(self):
        self.dismiss(False)


class DarkAccess(ModalScreen[bool]):
    BINDINGS=[Binding('escape','cancel',show=False)]

    def compose(self):
        with Vertical(id='dark-access'):
            yield Static('◇  VIP ZONE',classes='dark-kicker')
            yield Static(self.app.tr('Entrez le code d’accès.'),id='dark-code-label')
            yield Input(password=True,placeholder=self.app.tr('Code d’accès'),id='dark-code')
            yield Static('',id='dark-code-error')
            yield Static(self.app.tr('Pas de clé ? Rejoins le Discord ou le Telegram pour l’obtenir.'),id='dark-key-help')
            with Horizontal(id='dark-key-links'):
                yield Button('Discord  ↗',id='dark-key-discord')
                yield Button('Telegram  ↗',id='dark-key-telegram')
            with Horizontal(id='dark-actions'):
                yield Button(self.app.tr('Annuler'),id='dark-code-cancel')
                yield Button(self.app.tr('Déverrouiller'),id='dark-unlock')

    def on_mount(self):
        self.query_one('#dark-code',Input).focus()

    def unlock(self):
        field=self.query_one('#dark-code',Input)
        if field.value=='2027':
            field.value=''
            self.dismiss(True)
        else:
            self.query_one('#dark-code-error',Static).update(self.app.tr('Code incorrect. Réessayez.'))
            field.value=''
            field.focus()

    def on_input_submitted(self,event):
        event.stop()
        self.unlock()

    def on_button_pressed(self,event):
        event.stop()
        if event.button.id=='dark-key-discord':self.app.open_url('https://discord.gg/kaostools')
        elif event.button.id=='dark-key-telegram':self.app.open_url('https://t.me/v0idtool')
        elif event.button.id=='dark-unlock':self.unlock()
        else:self.action_cancel()

    def action_cancel(self):
        self.query_one('#dark-code',Input).value=''
        self.dismiss(False)


class DarkConstruction(ModalScreen):
    BINDINGS=[Binding('escape','back',show=False)]

    def compose(self):
        with Vertical(id='dark-chamber'):
            yield Static('◈',classes='dark-emblem')
            yield Static(self.app.tr('ZONE VIP'),classes='dark-kicker')
            yield Static('━━━━━━━━━━━━━━━━',id='dark-divider')
            yield Static(self.app.tr('En construction'),id='dark-title')
            yield Button(self.app.tr('← RETOUR'),id='dark-back')

    def on_mount(self):
        self.query_one('#dark-back').focus()
        if self.app.motion:
            chamber=self.query_one('#dark-chamber')
            chamber.styles.opacity=0
            chamber.styles.animate('opacity',1.,duration=.35)

    def on_button_pressed(self,event):
        event.stop()
        self.action_back()

    def action_back(self):
        self.dismiss()
