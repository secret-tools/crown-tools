import webbrowser

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static, Select

from .update_check import (
    DISCORD_URL, DOWNLOAD_URL, REPOSITORY, TELEGRAM_URL, check_for_update,
)
from .version import VERSION
from .update_locales import preferred_language, render_text
from .localization import LANGUAGES, display_arabic


class UpdateGate(App[bool]):
    CSS = '''
    Screen { background: #090b10; align: center middle; }
    #card { width: 80; max-width: 96%; height: auto; max-height: 95%;
        border: round #e32636; padding: 1 3; background: #11151e; }
    #brand { color: #e32636; text-style: bold; margin-bottom: 1; }
    #heading { text-style: bold; color: #ffffff; margin-bottom: 1; }
    #versions { color: #b3bac9; margin-bottom: 1; }
    #details { color: #d6dbe5; margin-bottom: 1; }
    Horizontal { height: auto; align: center middle; margin-top: 1; }
    Button { margin: 0 1; min-width: 14; }
    #update { background: #e32636; color: white; }
    #footnote { color: #8993a6; margin-top: 1; }
    '''
    BINDINGS = [('escape', 'quit', 'Exit')]

    def __init__(self, language=None, checker=check_for_update):
        super().__init__()
        self.language = preferred_language(language)
        self.checker = checker
        self.status = None
        self.download_opened = False

    def tr(self, key):
        return render_text(self.language, key)

    def compose(self) -> ComposeResult:
        with VerticalScroll(id='card'):
            yield Static(self.tr('brand'), id='brand')
            yield Static(self.tr('checking'), id='heading')
            yield Static(self.tr('installed') + '  ' + VERSION, id='versions')
            yield Static('', id='details', markup=False)
            with Horizontal():
                yield Button(self.tr('update'), id='update')
                yield Button(self.tr('retry'), id='retry', disabled=True)
                yield Button(self.tr('exit'), id='exit')
            with Horizontal():
                yield Button('Discord ↗', id='discord')
                yield Button('Telegram ↗', id='telegram')
                yield Button('GitHub ↗', id='github')
            yield Static(self.tr('files'), id='footnote')
            yield Static(self.tr('language'), id='language-label')
            yield Select([(display_arabic(name) if code == 'ar' else name, code)
                          for code, name in LANGUAGES.items()], value=self.language,
                         allow_blank=False, id='update-language')

    def on_select_changed(self, event: Select.Changed):
        if event.select.id != 'update-language' or event.value == self.language:
            return
        self.language = event.value
        for selector, key in [('#brand', 'brand'), ('#footnote', 'files'),
                              ('#language-label', 'language')]:
            self.query_one(selector, Static).update(self.tr(key))
        for selector, key in [('#update', 'update'), ('#retry', 'retry'), ('#exit', 'exit')]:
            self.query_one(selector, Button).label = self.tr(key)
        if self.status:
            self.show_status(self.status)
        else:
            self.query_one('#heading', Static).update(self.tr('checking'))
            self.query_one('#versions', Static).update(self.tr('installed') + '  ' + VERSION)

    def on_mount(self):
        self.check()

    def check(self):
        self.query_one('#retry', Button).disabled = True
        self.download_opened = False
        self.query_one('#heading', Static).update(self.tr('checking'))
        self.run_worker(self.fetch_status, thread=True, exclusive=True)

    def fetch_status(self):
        status = self.checker()
        self.call_from_thread(self.show_status, status)

    def show_status(self, status):
        self.status = status
        if status.state == 'current':
            self.exit(True)
            return
        self.query_one('#retry', Button).disabled = False
        self.query_one('#update', Button).disabled = False
        if status.state == 'required':
            self.query_one('#heading', Static).update(self.tr('ready'))
            self.query_one('#versions', Static).update(f'{status.current}  →  {status.latest}')
            details = self.tr('required')
            notes = (status.notes_by_language or {}).get(self.language, status.notes)
            if notes:
                details += '\n\n' + self.tr('notes') + '\n' + (display_arabic(notes) if self.language == 'ar' else notes)
        else:
            self.query_one('#heading', Static).update(self.tr('unavailable'))
            self.query_one('#versions', Static).update(self.tr('installed') + '  ' + status.current)
            details = self.tr('offline')
        if self.download_opened:
            details = self.tr('instructions')
        self.query_one('#details', Static).update(details)

    def on_button_pressed(self, event: Button.Pressed):
        key = event.button.id
        if key == 'exit':
            self.exit(False)
        elif key == 'retry':
            self.check()
        else:
            download = (REPOSITORY + '/archive/' + self.status.commit + '.zip'
                        if self.status and self.status.commit else DOWNLOAD_URL)
            links = {'update': download, 'discord': DISCORD_URL,
                     'telegram': TELEGRAM_URL, 'github': REPOSITORY}
            if key in links:
                try:
                    opened = webbrowser.open(links[key])
                except OSError:
                    opened = False
                if key == 'update' and opened:
                    self.download_opened = True
                    self.query_one('#details', Static).update(self.tr('instructions'))
                elif not opened:
                    self.notify(self.tr('open_link') + links[key], severity='warning')

    def action_quit(self):
        self.exit(False)
