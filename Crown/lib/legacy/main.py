"""
Crown-Tools — TUI Dashboard (édition esthétique/animations)
Lancement : pip install textual rich pyfiglet requests pillow numpy psutil qrcode dnspython
            python main.py
"""

import sys
import random
import socket
import ssl
import platform
import subprocess
import ipaddress
import time
import asyncio
import hashlib
import secrets
import string
import base64
import html
import codecs
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pyfiglet
import qrcode
import dns.resolver

try:
    import psutil
    _HAS_PSUTIL = True
    psutil.cpu_percent(interval=None)  # amorce : le 1er relevé n'a pas de sens, on le "brûle" ici
except Exception:
    _HAS_PSUTIL = False

from rich.console import Console, Group
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.live import Live
from rich.markup import escape as _mkup_escape
from rich import box

from intro_valider import play_neon_intro
from settings import (
    load_config, save_config, t, THEMES, THEME_NAMES, LANGUAGES, LANGUAGE_NAMES,
    DEFAULT_CONFIG,
)

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, ListView, ListItem, Label, Input, Button, Select, Switch
from textual.binding import Binding
from textual.screen import Screen, ModalScreen


# ============================================================
#  CONSTANTES
# ============================================================

PORTS_COMMUNS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
    443: "HTTPS", 445: "SMB", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-alt",
    8443: "HTTPS-alt", 27017: "MongoDB",
}

# MENU_ARCHIVED : catégories/outils existants, retirés du menu actif "pour
# l'instant" (demande explicite du 2026-08-27) le temps de redéfinir la vraie
# structure de catégories de l'app. Le code des outils (TOOL_SCREENS,
# fonctions execute()...) N'EST PAS supprimé -> rien de perdu, juste masqué.
MENU_ARCHIVED = {
    "IP & Network": [
        ("01", "Web Lookup"),
        ("02", "IP Localisation"),
        ("03", "IP Opérateur"),
        ("04", "Open Ports"),
        ("05", "IP Pinger"),
        ("06", "IP Generator"),
    ],
    "OSINT & Research": [
        ("01", "Link Hub"), ("02", "OSINT Framework"), ("03", "Name Finder"),
        ("04", "Email Info"), ("05", "Number Info"), ("06", "Profile Builder"),
        ("07", "Simple Report"), ("08", "Search DB"), ("09", "Username Hunter"),
        ("10", "Domain Intel"), ("11", "Social Scraper"), ("12", "VPN Detector"),
    ],
    "Utilities": [
        ("01", "Hash Tools"), ("02", "Password Generator"), ("03", "QR Code"),
        ("04", "Text Encoder"), ("05", "Base64 Tools"),
    ],
}

MENU = {
    "IP & Network": [
        ("01", "Web Lookup"),
        ("02", "IP Localisation"),
        ("03", "IP Opérateur"),
        ("04", "Open Ports"),
        ("05", "IP Pinger"),
        ("06", "IP Generator"),
    ],
    "Domains & Infrastructure": [
        ("01", "WHOIS Lookup"), ("02", "DNS Records"),
        ("03", "Subdomain Finder"), ("04", "SSL Certificate Info"),
    ],
    "Utilities": [
        ("01", "Hash Tools"), ("02", "Password Generator"), ("03", "QR Code"),
        ("04", "Text Encoder"), ("05", "Base64 Tools"),
    ],
    "Settings": [
        ("01", "Configuration"),
    ],
}

CATEGORY_ICONS = {
    "IP & Network": "▸",
    "OSINT & Research": "●",
    "Domains & Infrastructure": "◆",
    "Utilities": "▪",
    "Settings": "▸",
}

TOOL_DESCRIPTIONS = {
    "Web Lookup": "Résolution DNS, statut HTTP, géolocalisation et scan de ports en un seul rapport.",
    "IP Localisation": "Pays, ville, coordonnées GPS et fuseau horaire d'une adresse IP.",
    "IP Opérateur": "FAI, organisation, numéro AS, détection proxy / VPN / hébergeur.",
    "Open Ports": "Scan des ports communs (FTP, SSH, HTTP, RDP, bases de données...).",
    "IP Pinger": "Ping ICMP vers une IP ou un domaine, 4 paquets.",
    "IP Generator": "Génère des adresses IPv4 publiques aléatoires.",
    "Configuration": "Langue, thème, pseudo, son, vitesse de boot, sidebar, confirmation de sortie.",
    "Hash Tools": "Calcule MD5, SHA-1, SHA-256 et SHA-512 d'un texte.",
    "Password Generator": "Génère un mot de passe aléatoire sécurisé de la longueur voulue.",
    "QR Code": "Génère un QR code à partir d'un texte ou d'une URL, affiché en ASCII.",
    "Text Encoder": "Encode un texte en URL, HTML, ROT13 et hexadécimal.",
    "Base64 Tools": "Encode un texte en Base64, ou le décode si c'est déjà du Base64.",
    "WHOIS Lookup": "Registrar, dates de création/expiration, serveurs DNS d'un nom de domaine.",
    "DNS Records": "Enregistrements A, AAAA, MX, NS, TXT et CNAME d'un domaine.",
    "Subdomain Finder": "Recherche de sous-domaines courants (www, mail, api, dev...) par résolution DNS.",
    "SSL Certificate Info": "Émetteur, validité et noms alternatifs du certificat TLS d'un domaine.",
}


def _tool_description(tool_name: str) -> str:
    return TOOL_DESCRIPTIONS.get(tool_name, "Module du dashboard Crown-Tools.")


# Clés internes STABLES (MENU, TOOL_SCREENS, CATEGORY_ICONS...) -> clé de
# traduction. On ne traduit jamais les clés elles-mêmes, seulement l'affichage —
# ça évite de casser tout le dispatch (palette de commandes, démo F1, etc.)
# quand on change de langue.
CATEGORY_TKEY = {
    "IP & Network": "cat_ip_network",
    "OSINT & Research": "cat_osint",
    "Domains & Infrastructure": "cat_domains",
    "Utilities": "cat_utilities",
    "Settings": "cat_settings",
}

TOOL_TKEY = {
    "Web Lookup": "tool_web_lookup", "IP Localisation": "tool_ip_localisation",
    "IP Opérateur": "tool_ip_operateur", "Open Ports": "tool_open_ports",
    "IP Pinger": "tool_ip_pinger", "IP Generator": "tool_ip_generator",
    "Link Hub": "tool_link_hub", "OSINT Framework": "tool_osint_framework",
    "Name Finder": "tool_name_finder", "Email Info": "tool_email_info",
    "Number Info": "tool_number_info", "Profile Builder": "tool_profile_builder",
    "Simple Report": "tool_simple_report", "Search DB": "tool_search_db",
    "Username Hunter": "tool_username_hunter", "Domain Intel": "tool_domain_intel",
    "Social Scraper": "tool_social_scraper", "VPN Detector": "tool_vpn_detector",
    "Hash Tools": "tool_hash_tools", "Password Generator": "tool_password_generator",
    "QR Code": "tool_qr_code", "Text Encoder": "tool_text_encoder",
    "Base64 Tools": "tool_base64_tools",
    "Configuration": "tool_configuration",
    "WHOIS Lookup": "tool_whois_lookup", "DNS Records": "tool_dns_records",
    "Subdomain Finder": "tool_subdomain_finder", "SSL Certificate Info": "tool_ssl_cert_info",
}


def category_label(cat: str, lang: str) -> str:
    tk = CATEGORY_TKEY.get(cat)
    return t(tk, lang) if tk else cat


def tool_label(name: str, lang: str) -> str:
    tk = TOOL_TKEY.get(name)
    return t(tk, lang) if tk else name


# Index plat {catégorie, outil} -> utilisé par la palette de commandes (Ctrl+K)
ALL_TOOLS = [(cat, tool_name) for cat, tools in MENU.items() for _, tool_name in tools]

# Palette -> voir settings.THEMES (plusieurs thèmes, choisis dans l'assistant
# de config), exposée comme variables CSS Textual ($crown-xxx) par l'App.

GLITCH_GLYPHS = "!<>-_\\/[]{}=+*^?#@%&"
MATRIX_CHARS = "アイウエオカキクケコサシスセソ0123456789ABCDEF"
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


# ============================================================
#  BOOT SEQUENCE — intro cinématique avant le lancement de Textual
# ============================================================

def _enable_windows_ansi() -> None:
    """Active le VT processing sur la console Windows (cmd.exe classique ne l'a pas
    toujours activé par défaut). Sans ça, Rich détecte un terminal 'legacy' et
    dégrade le rendu (pas de couleurs vraies, barres en tirets ASCII, pas de
    rafraîchissement en place). Ne fait rien sur les autres OS, jamais fatal."""
    if platform.system().lower() != "windows":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        for handle_id in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        pass


_enable_windows_ansi()
# La console Windows retombe parfois sur l'encodage OEM/ANSI (cp1252, cp850...) au
# lieu de l'UTF-8, ce qui plante sur les caractères demi-bloc/box-drawing utilisés
# par les animations. On force l'UTF-8 en écriture, jamais fatal si indisponible.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# On force le mode capable plutôt que de laisser Rich deviner : sur un cmd.exe mal
# détecté, l'auto-détection retombe en mode 'legacy' (barres ASCII, pas de vraies
# couleurs). On vient d'activer le VT processing nous-mêmes juste au-dessus, donc
# on peut forcer sans risque.
console = Console(force_terminal=True, color_system="truecolor", legacy_windows=False)


_sound_enabled = True


def _beep(freq: int = 880, dur: int = 90) -> None:
    """Petit bip synthétique (Windows uniquement). Respecte le réglage son de la
    config, et ne fait jamais planter l'app si le module est indisponible."""
    if not _sound_enabled:
        return
    try:
        import winsound
        winsound.Beep(freq, dur)
    except Exception:
        pass


METRIC_SPECS = [("CPU", "%", 44.0), ("MEM", "%", 61.0), ("NET", " Mb/s", 28.0)]


def _step_metric(value: float, jitter: float = 5.5, lo: float = 4.0, hi: float = 96.0) -> float:
    """Marche aléatoire bornée — utilisée UNIQUEMENT en repli si psutil n'est pas
    installé, pour que le panneau ne casse jamais. Sinon, voir _read_live_metrics."""
    return max(lo, min(hi, value + random.uniform(-jitter, jitter)))


_NET_STATE = {"bytes": None, "time": None}
_METRIC_CACHE = {"t": 0.0, **{label: seed for label, _unit, seed in METRIC_SPECS}}


def _net_rate_mbps() -> float:
    """Débit réseau instantané réel (Mb/s), calculé à partir du delta de
    compteurs cumulés de psutil entre deux relevés."""
    now = time.monotonic()
    counters = psutil.net_io_counters()
    total = counters.bytes_sent + counters.bytes_recv
    if _NET_STATE["bytes"] is None:
        rate = 0.0
    else:
        dt = max(now - _NET_STATE["time"], 0.001)
        rate = (total - _NET_STATE["bytes"]) * 8 / 1_000_000 / dt
    _NET_STATE["bytes"] = total
    _NET_STATE["time"] = now
    return max(rate, 0.0)


def _read_live_metrics(min_interval: float = 0.2) -> dict:
    """Vraies stats système (CPU%, RAM%, débit réseau Mb/s réels de la machine)
    via psutil, avec un throttle pour ne pas solliciter l'OS à chaque frame de
    l'animation. Retombe sur une marche aléatoire si psutil est indisponible,
    pour ne jamais faire planter le boot — mais chez toi (psutil installé),
    ce sont bien tes vraies stats, pas une simulation."""
    if not _HAS_PSUTIL:
        return {label: _step_metric(_METRIC_CACHE[label]) for label, _u, _s in METRIC_SPECS}
    now = time.monotonic()
    if now - _METRIC_CACHE["t"] >= min_interval:
        _METRIC_CACHE["CPU"] = psutil.cpu_percent(interval=None)
        _METRIC_CACHE["MEM"] = psutil.virtual_memory().percent
        _METRIC_CACHE["NET"] = _net_rate_mbps()
        _METRIC_CACHE["t"] = now
    return {label: _METRIC_CACHE[label] for label, _u, _s in METRIC_SPECS}


def _metric_style(value: float) -> str:
    if value < 55:
        return "green"
    if value < 80:
        return "yellow"
    return "red"


_METRIC_BASE_RGB = {
    "green": (74, 222, 128),
    "yellow": (250, 204, 21),
    "red": (248, 113, 113),
    "cyan": (34, 211, 238),
}


def _dim_hex(base_style: str, intensity: int) -> str:
    """Couleur hex pré-calculée (jamais de syntaxe 'couleur X%' -> celle-ci
    n'existe qu'en TCSS, pas dans les Style Rich inline ; testé, ça plante
    avec MissingStyle). Un hex est toujours valide, aucune ambiguïté de parsing."""
    r, g, b = _METRIC_BASE_RGB.get(base_style, (200, 200, 200))
    factor = max(0.25, min(1.0, intensity / 100))
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


_SPARK_SHAPES = ".▪●█"  # 4 paliers, chacun DÉJÀ confirmé lisible sur cette police
# (tous des glyphes VISIBLES, pas d'espace comme palier bas -> CPU/NET qui
# passent le plus clair de leur temps sous 15% auraient sinon une sparkline
# quasi invisible en permanence, ce qui a été signalé comme "plus de courbe").
# "." = ASCII pur, "▪"/"●" = mêmes glyphes que les puces de catégorie déjà
# nettes à l'écran, "█" = bloc plein déjà confirmé net -> jamais les huitièmes
# de bloc ▁▂▃▄▅▆▇ qui, eux, ne rendent pas du tout sur cmd.exe.


def _sparkline_append(text: Text, history: list, base_style: str, width: int) -> None:
    padding = max(0, width - len(history))
    text.append(" " * padding)
    top = len(_SPARK_SHAPES) - 1
    for v in history[-width:]:
        level = min(int(v / 100 * (top + 1)), top)
        intensity = max(35, min(100, int(v)))
        text.append(_SPARK_SHAPES[level], style=_dim_hex(base_style, intensity))


def _load_panel_text(metrics: dict, width: int = 22) -> Text:
    """Mini dashboard de charge système (façon htop/btop) : des métriques qui
    dérivent lentement, une sparkline par ligne. Look 'vrai outil de monitoring'
    plutôt qu'un gadget façon film de hackers — plus impressionnant en restant
    crédible."""
    text = Text()
    for i, (label, unit, _seed) in enumerate(METRIC_SPECS):
        history = metrics[label][-width:]
        value = history[-1] if history else 0.0
        style = _metric_style(value) if unit == "%" else "cyan"
        text.append(f"{label:<4}", style="dim")
        _sparkline_append(text, history, style, width)
        text.append(f" {value:>3.0f}{unit:<5}", style=style)
        if i < len(METRIC_SPECS) - 1:
            text.append("\n")
    return text


def run_boot_sequence(cfg: dict) -> None:
    """Intro complète, tourne dans la console brute AVANT que Textual ne prenne
    le contrôle du terminal. Purement cosmétique — aucun impact sur les outils.
    L'écran de diagnostics d'avant a été retiré : la configuration initiale
    (langue/thème/pseudo/etc.) se fait maintenant dans un vrai écran Textual
    interactif juste après (SettingsWizardScreen), plus robuste qu'un menu
    bricolé au clavier en mode console brute."""
    speed = cfg.get("boot_speed", "normal")
    try:
        if speed != "off":
            play_neon_intro(console, speed_multiplier=0.45 if speed == "fast" else 1.0)
        console.clear()
    except KeyboardInterrupt:
        console.clear()


# ============================================================
#  WIDGETS D'EFFETS (FX) RÉUTILISABLES
# ============================================================

class GlitchText(Static):
    """Révèle un texte (ex: bannière ASCII) en le stabilisant depuis du bruit."""

    def __init__(self, target: str, frames: int = 16, speed: float = 0.035,
                 style: str = "bold red", **kw):
        super().__init__(**kw)
        self._target = target
        self._frames = frames
        self._speed = speed
        self._text_style = style
        self._frame = 0
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(self._speed, self._tick)

    def _tick(self) -> None:
        self._frame += 1
        if self._frame >= self._frames and self._timer is not None:
            self._timer.stop()
        self.refresh()

    def render(self) -> Text:
        progress = min(self._frame / self._frames, 1.0)
        lines = []
        for line in self._target.splitlines():
            chars = [
                ch if ch == " " or random.random() < progress else random.choice(GLITCH_GLYPHS)
                for ch in line
            ]
            lines.append("".join(chars))
        # no_wrap + crop : un art ASCII multi-lignes ne doit JAMAIS se refaire
        # re-wrapper par Rich si le conteneur est plus étroit que prévu (ça
        # casse complètement la forme des lettres) -> on préfère un rognage
        # propre à droite, toujours lisible, plutôt qu'un fouillis.
        return Text("\n".join(lines), style=self._text_style, no_wrap=True, overflow="crop")


class MatrixRain(Static):
    """Widget d'ambiance décoratif : pluie de caractères façon Matrix."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._drops = []

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self.refresh)

    def render(self) -> Text:
        width = max(self.size.width, 1)
        height = max(self.size.height, 1)
        if len(self._drops) != width:
            self._drops = [random.randint(0, height) for _ in range(width)]

        grid = [[" "] * width for _ in range(height)]
        for x in range(width):
            y = self._drops[x] % height
            grid[y][x] = random.choice(MATRIX_CHARS)
            self._drops[x] += 1

        content = "\n".join("".join(row) for row in grid)
        return Text(content, style="dim green")


class Typewriter(Static):
    """Révèle un résultat d'outil ligne par ligne (évite de couper une balise markup en deux)."""

    def __init__(self, full_text: str, line_delay: float = 0.03, **kw):
        super().__init__(**kw)
        self._lines = full_text.split("\n")
        self._shown = 0
        self._line_delay = line_delay
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(self._line_delay, self._advance)

    def _advance(self) -> None:
        if self._shown < len(self._lines):
            self._shown += 1
            self.update("\n".join(self._lines[: self._shown]))
        elif self._timer is not None:
            self._timer.stop()


class Spinner(Static):
    """Spinner animé affiché pendant l'exécution d'un outil en arrière-plan."""

    def __init__(self, label: str = "Chargement", **kw):
        super().__init__(**kw)
        self._label = label
        self._i = 0
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.08, self._tick)
        self._tick()

    def _tick(self) -> None:
        frame = SPINNER_FRAMES[self._i % len(SPINNER_FRAMES)]
        self._i += 1
        self.update(f"[bold cyan]{frame}[/bold cyan] [dim]{self._label}...[/dim]")

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()


class Toast(Static):
    """Notification flottante qui apparaît/disparaît en fondu, ancrée en bas de l'écran."""

    def __init__(self, message: str, kind: str = "success", **kw):
        super().__init__(message, **kw)
        self._kind = kind

    def on_mount(self) -> None:
        self.add_class(f"toast-{self._kind}")
        self.styles.opacity = 0.0
        self.styles.animate("opacity", value=1.0, duration=0.2, easing="out_cubic")
        self.set_timer(2.4, self._fade_out)

    def _fade_out(self) -> None:
        self.styles.animate("opacity", value=0.0, duration=0.25, easing="in_cubic", on_complete=self.remove)


# ============================================================
#  BANNIÈRE / HEADER
# ============================================================

class Banner(Vertical):
    def compose(self) -> ComposeResult:
        art = pyfiglet.figlet_format("CROWN-TOOLS", font="small", width=1000)
        lang = getattr(self.app, "lang", "fr")
        theme = getattr(self.app, "active_theme", "void_red")
        accent = THEMES.get(theme, THEMES["void_red"]).get("crown-accent", "#f87171")
        yield GlitchText(art, id="banner-art", style=f"bold {accent}")
        yield Static(f"[dim]v2 · {t('app_subtitle', lang)}[/dim]", id="banner-sub")


class Clock(Static):
    def on_mount(self) -> None:
        self.set_interval(1, self.refresh_time)
        self.refresh_time()

    def refresh_time(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.update(f"[bold cyan]{now}[/bold cyan]")


class SessionStats(Static):
    """Compteur d'outils exécutés + temps de session, façon dashboard vivant."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._start = time.monotonic()
        self.scans = 0

    def on_mount(self) -> None:
        self.set_interval(1, self._tick)
        self._tick()

    def _tick(self) -> None:
        elapsed = int(time.monotonic() - self._start)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        lang = getattr(self.app, "lang", "fr")
        pseudo = getattr(self.app, "config", {}).get("pseudo", "") if hasattr(self.app, "config") else ""
        pseudo_part = f"[bold cyan]▸ {_mkup_escape(pseudo)}[/bold cyan]   " if pseudo else ""
        self.update(
            f"{pseudo_part}[bold]{self.scans}[/bold] [dim]{t('scans', lang)}[/dim]   "
            f"[dim cyan]{h:02d}:{m:02d}:{s:02d}[/dim cyan]"
        )

    def bump(self) -> None:
        self.scans += 1
        self._tick()


class MiniLoad(Static):
    """Mini dashboard de charge système (sparklines CPU/MEM/NET) qui tourne en
    permanence dans la sidebar — l'app reste vivante même à l'arrêt complet,
    mais avec un visuel crédible (façon htop) plutôt qu'un gadget."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._metrics = {label: [seed] for label, _unit, seed in METRIC_SPECS}

    def on_mount(self) -> None:
        self.set_interval(1 / 4, self._tick)

    def _tick(self) -> None:
        live_vals = _read_live_metrics()
        for label, _unit, _seed in METRIC_SPECS:
            self._metrics[label].append(live_vals[label])
            self._metrics[label] = self._metrics[label][-14:]
        self.update(_load_panel_text(self._metrics, width=14))


class StatusBar(Static):
    def on_mount(self) -> None:
        self.retranslate(getattr(self.app, "lang", "fr"))

    def retranslate(self, lang: str) -> None:
        self.update(
            f"[dim] q [/dim] {t('quit', lang)}   [dim] Echap [/dim] {t('back', lang)}   "
            f"[dim] ↑↓ [/dim] {t('navigate', lang)}   [dim] Ctrl+K [/dim] {t('search', lang)}   "
            f"[dim] F1 [/dim] {t('demo', lang)}"
        )


# ============================================================
#  LISTE DES CATÉGORIES (gauche)
# ============================================================

class CategoryList(Vertical):
    def compose(self) -> ComposeResult:
        lang = getattr(self.app, "lang", "fr")
        self.border_title = f"▸ {t('categories_title', lang)}"
        items = [
            ListItem(
                Label(f"{CATEGORY_ICONS.get(cat, '•')}  {category_label(cat, lang)}  [dim]({len(MENU[cat])})[/dim]"),
                name=cat,
            )
            for cat in MENU.keys()
        ]
        yield ListView(*items, id="category-list")
        yield Label(f"[dim]{t('system_load', lang)}[/dim]", id="radar-title")
        yield MiniLoad(id="mini-radar")

    def retranslate(self, lang: str) -> None:
        self.border_title = f"▸ {t('categories_title', lang)}"
        self.query_one("#radar-title", Label).update(f"[dim]{t('system_load', lang)}[/dim]")
        cat_list = self.query_one("#category-list", ListView)
        for item in cat_list.children:
            if isinstance(item, ListItem) and item.name in MENU:
                label = item.query_one(Label)
                cat = item.name
                label.update(f"{CATEGORY_ICONS.get(cat, '•')}  {category_label(cat, lang)}  [dim]({len(MENU[cat])})[/dim]")


# ============================================================
#  PANEL DES OUTILS (droite)
# ============================================================

class ToolPanel(Vertical):
    """NOTE : le ListView de CategoryList peut déclencher son propre highlight
    (index 0) au montage, EN PARALLÈLE de l'appel explicite show_empty() fait
    par on_mount() -> deux coroutines concurrentes sur le même widget. Sans
    garde, l'une peut écrire le titre pendant que l'autre écrit la
    description juste après -> état visuel incohérent (titre "vide" + texte
    d'un outil). Même parade que CommandPalette._refresh_results : un numéro
    de génération, et on abandonne après l'await si une génération plus
    récente a démarré entre-temps."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._refresh_seq = 0

    def compose(self) -> ComposeResult:
        lang = getattr(self.app, "lang", "fr")
        self.border_title = f"▸ {t('select_category', lang)}"
        yield ListView(id="tool-list")
        yield Static("", id="tool-description")

    async def show_empty(self) -> None:
        self._refresh_seq += 1
        my_seq = self._refresh_seq
        lang = getattr(self.app, "lang", "fr")
        await self.query_one("#tool-list", ListView).clear()
        if my_seq != self._refresh_seq:
            return
        self.border_title = f"▸ {t('select_category', lang)}"
        self.query_one("#tool-description", Static).update(f"[dim]{t('search_hint', lang)}[/dim]")

    async def show_category(self, category: str) -> None:
        self._refresh_seq += 1
        my_seq = self._refresh_seq
        lang = getattr(self.app, "lang", "fr")
        lv = self.query_one("#tool-list", ListView)
        await lv.clear()
        if my_seq != self._refresh_seq:
            return
        icon = CATEGORY_ICONS.get(category, "•")
        self.border_title = f"{icon}  {category_label(category, lang).upper()}"
        tools = MENU.get(category, [])
        for num, tool_name in tools:
            lv.append(ListItem(Label(f"{num}  {tool_label(tool_name, lang)}"), name=f"{category}|{tool_name}"))
        if tools:
            self.show_description(tools[0][1])

    def show_description(self, tool_name: str) -> None:
        self.query_one("#tool-description", Static).update(f"[dim]{_tool_description(tool_name)}[/dim]")


# ============================================================
#  ÉCRAN ANIMÉ DE BASE (fade-in / fade-out)
# ============================================================

class AnimatedScreen(Screen):
    BINDINGS = [Binding("escape", "close_screen", "Retour")]

    def on_mount(self) -> None:
        self.styles.opacity = 0.0
        self.styles.animate("opacity", value=1.0, duration=0.22, easing="out_cubic")
        self._slide_in()

    def _slide_in(self) -> None:
        """Petit 'settle' vertical en plus du fondu -> l'écran arrive avec un peu
        de punch au lieu d'un simple fade plat. Offset animate() n'étant pas fiable
        sur ScalarOffset, on step manuellement (même technique que _shake)."""
        steps = [3, 2, 2, 1, 1, 0]
        self.styles.offset = (0, steps[0])

        def step(i: int = 1) -> None:
            if i < len(steps):
                self.styles.offset = (0, steps[i])
                self.set_timer(0.02, lambda: step(i + 1))

        step()

    def action_close_screen(self) -> None:
        self.styles.animate(
            "opacity", value=0.0, duration=0.15, easing="in_cubic",
            on_complete=self._pop,
        )

    def _pop(self) -> None:
        if self.app.screen is self:
            self.app.pop_screen()


# ============================================================
#  ÉCRAN "EN CONSTRUCTION"
# ============================================================

class DevelopmentPanel(Static):
    """Panneau 'module en construction' vivant : barre qui progresse vers un
    palier aléatoire puis stagne avec des points animés — même langage visuel
    que le panneau de diagnostics du boot (bordure rouge, barre en blocs)."""

    def __init__(self, tool_name: str, **kw):
        super().__init__(**kw)
        self.tool_name = tool_name
        self._target = random.randint(35, 82)
        self._pct = 0.0
        self._frame = 0

    def on_mount(self) -> None:
        self.set_interval(1 / 20, self._tick)

    def _tick(self) -> None:
        lang = getattr(self.app, "lang", "fr")
        self._frame += 1
        if self._pct < self._target:
            self._pct = min(self._pct + 1.1, self._target)
        dots = "." * (1 + (self._frame // 12) % 3)
        bar_w = 30
        filled = int(bar_w * self._pct / 100)
        bar = "█" * filled + "░" * (bar_w - filled)
        body = Group(
            Text(tool_label(self.tool_name, lang), style="bold white", justify="center"),
            Text(""),
            Text.from_markup(f"[bold red]{bar}[/bold red]  [bold]{int(self._pct)}%[/bold]", justify="center"),
            Text(f"{t('in_development', lang)}{dots}", style="dim", justify="center"),
        )
        self.update(Panel(
            body,
            title=f"[bold red]{t('module_construction', lang)}[/bold red]",
            border_style="red",
            padding=(1, 3),
        ))


class ComingSoonScreen(AnimatedScreen):
    def __init__(self, tool_name: str):
        super().__init__()
        self.tool_name = tool_name

    def compose(self) -> ComposeResult:
        lang = getattr(self.app, "lang", "fr")
        with Horizontal(id="title-row"):
            yield Button(t("back_button", lang), id="back-btn", variant="default")
            yield Static(f"[bold red]{tool_label(self.tool_name, lang)}[/bold red]", id="screen-title")
        yield MatrixRain(id="coming-soon-rain")
        with Vertical(id="coming-soon-msg"):
            yield DevelopmentPanel(self.tool_name, id="dev-panel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.action_close_screen()


# ============================================================
#  ÉCRAN GÉNÉRIQUE D'OUTIL
# ============================================================

class ToolScreen(AnimatedScreen):
    TITLE_TOOL = "Outil"
    PLACEHOLDER = "Entrée..."

    def compose(self) -> ComposeResult:
        lang = getattr(self.app, "lang", "fr")
        with Vertical(id="tool-toolbar"):
            with Horizontal(id="title-row"):
                yield Button(t("back_button", lang), id="back-btn", variant="default")
                yield Static(f"[bold red]{tool_label(self.TITLE_TOOL, lang)}[/bold red]", id="screen-title")
            with Horizontal(id="input-row"):
                yield Input(placeholder=t(self.PLACEHOLDER, lang), id="tool-input")
                yield Button(f"▸ {t('run_button', lang)}", id="run-btn", variant="error")
        with VerticalScroll(id="result-scroll") as scroll:
            scroll.border_title = f"▸ {t('results_title', lang)}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            self.run_tool()
        elif event.button.id == "back-btn":
            self.action_close_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.run_tool()

    def run_tool(self) -> None:
        lang = getattr(self.app, "lang", "fr")
        value = self.query_one("#tool-input", Input).value.strip()
        scroll = self.query_one("#result-scroll", VerticalScroll)
        scroll.remove_children()
        spinner = Spinner(t("loading", lang))
        scroll.mount(spinner)
        self._execute_worker(value, spinner, scroll)

    @work(thread=True, exclusive=True)
    def _execute_worker(self, value: str, spinner: Spinner, scroll: VerticalScroll) -> None:
        try:
            output = self.execute(value)
            ok = True
        except Exception as e:
            output = f"[bold red]{t('error_label', getattr(self.app, 'lang', 'fr'))}:[/bold red] {e}"
            ok = False
        self.app.call_from_thread(self._finish, spinner, scroll, output, ok)

    def _finish(self, spinner: Spinner, scroll: VerticalScroll, output, ok: bool) -> None:
        lang = getattr(self.app, "lang", "fr")
        spinner.stop()
        spinner.remove()
        if isinstance(output, str):
            # message simple (erreur, placeholder...) -> effet machine à écrire
            scroll.mount(Typewriter(output, line_delay=0.03, classes="result-text"))
        else:
            # résultat structuré (Table/Panel/Group Rich) -> fondu, pas de typing
            # ligne par ligne qui n'aurait pas de sens sur un tableau.
            result_widget = Static(output, classes="result-text")
            scroll.mount(result_widget)
            result_widget.styles.opacity = 0.0
            result_widget.styles.animate("opacity", value=1.0, duration=0.35, easing="out_cubic")
        self.mount(Toast(
            t("analysis_done", lang) if ok else t("analysis_error", lang),
            kind="success" if ok else "error",
        ))
        if ok:
            stats = self.app.query(SessionStats)
            if stats:
                stats.first().bump()
        else:
            self._shake(scroll)

    def _shake(self, widget) -> None:
        offsets = [(2, 0), (-2, 0), (1, 0), (-1, 0), (0, 0)]

        def step(i: int = 0) -> None:
            if i < len(offsets):
                widget.styles.offset = offsets[i]
                self.set_timer(0.03, lambda: step(i + 1))

        step()

    def execute(self, value: str):
        """Retourne soit une str (message simple, markup Rich -> tapé à l'écran),
        soit un renderable Rich (Table/Panel/Group -> affiché avec un fondu)."""
        return t("not_implemented", getattr(self.app, "lang", "fr"))


# ============================================================
#  OUTILS IP & NETWORK
# ============================================================

def _kv_table(rows: list) -> Table:
    """Table clé/valeur sans bordure, alignée — remplace les f-strings empilées."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")
    for k, v in rows:
        table.add_row(k, str(v) if v is not None else "[dim]—[/dim]")
    return table


def _ports_table(ports: list, lang: str = "fr"):
    """Table Port/Service/État pour un résultat de scan_ports()."""
    if not ports:
        return Text(t("no_open_ports", lang), style="dim")
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column(t("port", lang), justify="right")
    table.add_column(t("service", lang))
    table.add_column(t("state", lang))
    for port, name in ports:
        table.add_row(str(port), name, f"[green]● {t('open_state', lang)}[/green]")
    return table


def _risk_gauge(open_count: int, total: int, lang: str = "fr") -> Text:
    """Jauge ASCII colorée : proportion de ports ouverts / scannés."""
    total = max(total, 1)
    ratio = open_count / total
    filled = int(round(ratio * 24))
    bar = "█" * filled + "░" * (24 - filled)
    color = "green" if ratio < 0.15 else "yellow" if ratio < 0.4 else "red"
    return Text(f"{bar}  {open_count}/{total} {t('ports_open_of', lang)}", style=color)


class WebLookupScreen(ToolScreen):
    TITLE_TOOL = "Web Lookup"
    PLACEHOLDER = "ph_web_lookup"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain_or_ip', lang)}.[/yellow]"

        try:
            ip = socket.gethostbyname(value)
            dns_status = f"[green]OK[/green] -> {ip}"
        except socket.gaierror:
            ip = value
            dns_status = f"[yellow]{t('dns_failed', lang)}[/yellow]"

        try:
            r = requests.get(f"http://{value}", timeout=4)
            http_status = f"[green]{r.status_code}[/green]"
        except Exception:
            http_status = f"[dim]{t('no_http_response', lang)}[/dim]"

        summary = _kv_table([
            (t("target", lang), value),
            (t("dns_resolution", lang), dns_status),
            (t("http_status", lang), http_status),
        ])

        geo_rows = []
        try:
            geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
            if geo.get("status") == "success":
                geo_rows = [
                    (t("country", lang), geo.get("country")),
                    (t("city", lang), geo.get("city")),
                    (t("isp", lang), geo.get("isp")),
                    (t("org", lang), geo.get("org")),
                    (t("as_number", lang), geo.get("as")),
                ]
        except Exception:
            pass
        geo_block = _kv_table(geo_rows) if geo_rows else Text(t("geolocation_unavailable", lang), style="dim")

        open_ports = scan_ports(ip)

        body = Group(
            summary,
            Text(""),
            Text(f"▸ {t('geolocation', lang)}", style="bold cyan"),
            geo_block,
            Text(""),
            Text(f"▸ {t('common_ports', lang)}", style="bold cyan"),
            _ports_table(open_ports, lang),
        )
        return Panel(body, title=f"▸ {tool_label('Web Lookup', lang)}", border_style="red", padding=(1, 2))


class IPLocalisationScreen(ToolScreen):
    TITLE_TOOL = "IP Localisation"
    PLACEHOLDER = "ph_ip"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_ip', lang)}[/yellow]"
        try:
            geo = requests.get(f"http://ip-api.com/json/{value}", timeout=5).json()
        except Exception as e:
            return f"[red]{t('network_error', lang)}: {e}[/red]"

        if geo.get("status") != "success":
            return f"[red]{t('cannot_locate', lang)}: {geo.get('message', t('unknown', lang))}[/red]"

        table = _kv_table([
            (t("ip_label", lang), geo.get("query")),
            (t("country", lang), f"{geo.get('country')} ({geo.get('countryCode')})"),
            (t("region", lang), geo.get("regionName")),
            (t("city", lang), geo.get("city")),
            (t("postal_code", lang), geo.get("zip")),
            (t("coordinates", lang), f"{geo.get('lat')}, {geo.get('lon')}"),
            (t("timezone", lang), geo.get("timezone")),
        ])
        return Panel(table, title=f"▸ {tool_label('IP Localisation', lang)}", border_style="red", padding=(1, 2))


class IPOperateurScreen(ToolScreen):
    TITLE_TOOL = "IP Opérateur"
    PLACEHOLDER = "ph_ip"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_ip', lang)}[/yellow]"
        try:
            geo = requests.get(f"http://ip-api.com/json/{value}?fields=status,message,query,isp,org,as,mobile,proxy,hosting", timeout=5).json()
        except Exception as e:
            return f"[red]{t('network_error', lang)}: {e}[/red]"

        if geo.get("status") != "success":
            return f"[red]{t('error_label', lang)}: {geo.get('message', t('unknown', lang))}[/red]"

        def _flag(b) -> str:
            return f"[red]● {t('yes_flag', lang)}[/red]" if b else f"[green]○ {t('no_flag', lang)}[/green]"

        table = _kv_table([
            (t("isp_full", lang), geo.get("isp")),
            (t("organization", lang), geo.get("org")),
            (t("as_number", lang), geo.get("as")),
            (t("mobile", lang), _flag(geo["mobile"]) if "mobile" in geo else "—"),
            (t("proxy_vpn", lang), _flag(geo["proxy"]) if "proxy" in geo else "—"),
            (t("hosting", lang), _flag(geo["hosting"]) if "hosting" in geo else "—"),
        ])
        return Panel(table, title=f"▸ {tool_label('IP Opérateur', lang)}", border_style="red", padding=(1, 2))


def scan_ports(ip: str, timeout: float = 0.5):
    open_ports = []

    def check(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex((ip, port)) == 0:
                    return port
        except Exception:
            return None
        return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check, p): p for p in PORTS_COMMUNS}
        for future in as_completed(futures):
            port = future.result()
            if port:
                open_ports.append((port, PORTS_COMMUNS[port]))

    return sorted(open_ports)


class OpenPortsScreen(ToolScreen):
    TITLE_TOOL = "Open Ports"
    PLACEHOLDER = "ph_ip_or_domain"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain_or_ip', lang)}[/yellow]"
        try:
            ip = socket.gethostbyname(value)
        except socket.gaierror:
            return f"[red]{t('cannot_resolve', lang)}: {value}[/red]"

        result = scan_ports(ip)
        body = Group(
            Text(f"{value}  ->  {ip}", style="bold"),
            Text(""),
            _risk_gauge(len(result), len(PORTS_COMMUNS), lang),
            Text(""),
            _ports_table(result, lang),
        )
        return Panel(body, title=f"▸ {tool_label('Open Ports', lang)}", border_style="red", padding=(1, 2))


class IPPingerScreen(ToolScreen):
    TITLE_TOOL = "IP Pinger"
    PLACEHOLDER = "ph_ip_or_domain"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain_or_ip', lang)}[/yellow]"

        is_windows = platform.system().lower() == "windows"
        param = "-n" if is_windows else "-c"
        try:
            result = subprocess.run(
                ["ping", param, "4", value],
                capture_output=True, timeout=10
            )
            raw = result.stdout or result.stderr
            if is_windows:
                # la console Windows sort le texte de "ping" dans le codepage OEM
                # (souvent cp850/cp437), pas l'ANSI (cp1252) que Python décoderait
                # par défaut -> accents illisibles sinon.
                try:
                    import ctypes
                    oem_cp = ctypes.windll.kernel32.GetOEMCP()
                    output = raw.decode(f"cp{oem_cp}", errors="replace")
                except Exception:
                    output = raw.decode(errors="replace")
            else:
                output = raw.decode(errors="replace")
            output = output.strip()
            return Panel(Text(output), title=f"▸ {tool_label('IP Pinger', lang)} — {value}",
                         border_style="red", padding=(1, 2))
        except subprocess.TimeoutExpired:
            return f"[red]{t('timeout_no_response', lang)}[/red]"
        except Exception as e:
            return f"[red]{t('error_label', lang)}: {e}[/red]"


class IPGeneratorScreen(ToolScreen):
    TITLE_TOOL = "IP Generator"
    PLACEHOLDER = "ph_count"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        try:
            count = int(value) if value else 5
            count = max(1, min(count, 50))
        except ValueError:
            return f"[red]{t('enter_valid_number', lang)}[/red]"

        ips = []
        while len(ips) < count:
            ip = ipaddress.IPv4Address(random.randint(1, 2**32 - 1))
            if ip.is_global:
                ips.append(str(ip))

        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        table.add_column("#", justify="right", style="dim")
        table.add_column(t("ip_label", lang))
        for i, ip in enumerate(ips, 1):
            table.add_row(str(i), f"[green]{ip}[/green]")
        return Panel(table, title=f"▸ {count} {t('generated_ips', lang)}", border_style="red", padding=(1, 2))


# ============================================================
#  OUTILS — BOÎTE À OUTILS (utilitaires, aucune dépendance réseau)
# ============================================================

class HashToolsScreen(ToolScreen):
    TITLE_TOOL = "Hash Tools"
    PLACEHOLDER = "ph_hash_input"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_text', lang)}[/yellow]"
        data = value.encode("utf-8")
        rows = [
            ("MD5", hashlib.md5(data).hexdigest()),
            ("SHA-1", hashlib.sha1(data).hexdigest()),
            ("SHA-256", hashlib.sha256(data).hexdigest()),
            ("SHA-512", hashlib.sha512(data).hexdigest()),
        ]
        table = _kv_table(rows)
        return Panel(table, title=f"▸ {tool_label('Hash Tools', lang)}", border_style="red", padding=(1, 2))


class PasswordGeneratorScreen(ToolScreen):
    TITLE_TOOL = "Password Generator"
    PLACEHOLDER = "ph_password_length"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        try:
            length = int(value) if value.strip() else 16
        except ValueError:
            return f"[red]{t('enter_valid_number', lang)}[/red]"
        length = max(6, min(length, 128))
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        rows = [
            (t("password_label", lang), password),
            (t("length_label", lang), str(length)),
        ]
        table = _kv_table(rows)
        return Panel(table, title=f"▸ {tool_label('Password Generator', lang)}", border_style="red", padding=(1, 2))


def _qr_to_text(matrix) -> Text:
    """Rendu QR en blocs pleins UNIQUEMENT ("█"/" ", déjà confirmés fiables sur
    cmd.exe) — chaque module est doublé en LARGEUR (au lieu d'un demi-bloc
    vertical ▀/▄, non vérifié sur cette police) pour corriger le ratio
    hauteur/largeur des cellules du terminal, sans risquer un glyphe cassé."""
    lines = ["".join("██" if cell else "  " for cell in row) for row in matrix]
    return Text("\n".join(lines), style="white", no_wrap=True, overflow="crop")


class QRCodeScreen(ToolScreen):
    TITLE_TOOL = "QR Code"
    PLACEHOLDER = "ph_qr_text"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_qr_text', lang)}[/yellow]"
        qr = qrcode.QRCode(border=1, box_size=1)
        qr.add_data(value)
        qr.make(fit=True)
        art = _qr_to_text(qr.get_matrix())
        return Group(
            Text(f"{t('qr_content_label', lang)}: {value}", style="dim"),
            Text(""),
            art,
        )


class TextEncoderScreen(ToolScreen):
    TITLE_TOOL = "Text Encoder"
    PLACEHOLDER = "ph_text_encode"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_text', lang)}[/yellow]"
        rows = [
            ("URL", urllib.parse.quote(value)),
            ("HTML", html.escape(value)),
            ("ROT13", codecs.encode(value, "rot_13")),
            ("Hex", value.encode("utf-8").hex()),
        ]
        table = _kv_table(rows)
        return Panel(table, title=f"▸ {tool_label('Text Encoder', lang)}", border_style="red", padding=(1, 2))


class Base64ToolsScreen(ToolScreen):
    TITLE_TOOL = "Base64 Tools"
    PLACEHOLDER = "ph_base64_input"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_text', lang)}[/yellow]"
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
        except Exception:
            decoded = f"[dim]{t('not_valid_base64', lang)}[/dim]"
        rows = [
            (t("encoded_label", lang), encoded),
            (t("decoded_label", lang), decoded),
        ]
        table = _kv_table(rows)
        return Panel(table, title=f"▸ {tool_label('Base64 Tools', lang)}", border_style="red", padding=(1, 2))


# ============================================================
#  OUTILS — DOMAINES & INFRASTRUCTURE
# ============================================================

def _raw_whois_request(server: str, query: str, timeout: float = 5.0) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((server, 43))
        s.sendall((query + "\r\n").encode())
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks).decode(errors="replace")


def _whois_query(domain: str, timeout: float = 5.0) -> str:
    """Pas de dépendance externe (python-whois a des parsers peu fiables selon
    les TLD) : on interroge whois.iana.org pour trouver le serveur autoritaire
    du TLD, puis ce serveur directement — protocole WHOIS brut (RFC 3912),
    juste des sockets stdlib."""
    tld = domain.rsplit(".", 1)[-1].lower()
    iana_resp = _raw_whois_request("whois.iana.org", tld, timeout)
    server = None
    for line in iana_resp.splitlines():
        if line.lower().startswith("whois:"):
            server = line.split(":", 1)[1].strip()
            break
    if not server:
        return iana_resp
    result = _raw_whois_request(server, domain, timeout)
    for line in result.splitlines():
        if line.lower().startswith("registrar whois server:"):
            deeper = line.split(":", 1)[1].strip()
            if deeper and deeper != server:
                try:
                    deeper_result = _raw_whois_request(deeper, domain, timeout)
                    if deeper_result.strip():
                        return deeper_result
                except Exception:
                    pass
            break
    return result


class WhoisLookupScreen(ToolScreen):
    TITLE_TOOL = "WHOIS Lookup"
    PLACEHOLDER = "ph_domain"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain', lang)}[/yellow]"
        try:
            raw = _whois_query(value.strip())
        except Exception as e:
            return f"[red]{t('network_error', lang)}: {e}[/red]"
        if not raw.strip():
            return f"[yellow]{t('no_whois_data', lang)}[/yellow]"
        return Panel(Text(raw.strip()), title=f"▸ {tool_label('WHOIS Lookup', lang)} — {value}",
                     border_style="red", padding=(1, 2))


class DnsRecordsScreen(ToolScreen):
    TITLE_TOOL = "DNS Records"
    PLACEHOLDER = "ph_domain"
    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain', lang)}[/yellow]"
        domain = value.strip()
        resolver = dns.resolver.Resolver()
        resolver.timeout = 4
        resolver.lifetime = 4
        rows = []
        for rtype in self.RECORD_TYPES:
            try:
                answers = resolver.resolve(domain, rtype)
                rows.append((rtype, ", ".join(str(a) for a in answers)))
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                continue
            except Exception:
                rows.append((rtype, f"[dim]{t('dns_error', lang)}[/dim]"))
        if not rows:
            return f"[red]{t('no_dns_records', lang)}: {domain}[/red]"
        table = _kv_table(rows)
        return Panel(table, title=f"▸ {tool_label('DNS Records', lang)} — {domain}",
                     border_style="red", padding=(1, 2))


COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "webmail", "smtp", "pop", "ns1", "ns2", "cpanel",
    "api", "dev", "staging", "test", "admin", "portal", "vpn", "blog",
    "shop", "app", "cdn", "static", "m", "mobile", "support", "help",
    "docs", "status", "beta", "secure", "git",
]


class SubdomainFinderScreen(ToolScreen):
    TITLE_TOOL = "Subdomain Finder"
    PLACEHOLDER = "ph_domain"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain', lang)}[/yellow]"
        domain = value.strip()
        found = []

        def check(sub):
            fqdn = f"{sub}.{domain}"
            try:
                ip = socket.gethostbyname(fqdn)
                return (fqdn, ip)
            except socket.gaierror:
                return None

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check, sub) for sub in COMMON_SUBDOMAINS]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)
        found.sort()

        if not found:
            return f"[yellow]{t('no_subdomains_found', lang)}: {domain}[/yellow]"
        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        table.add_column(t("subdomain_label", lang))
        table.add_column(t("ip_label", lang))
        for fqdn, ip in found:
            table.add_row(fqdn, f"[green]{ip}[/green]")
        return Panel(table, title=f"▸ {len(found)} {t('subdomains_found', lang)} — {domain}",
                     border_style="red", padding=(1, 2))


class SslCertInfoScreen(ToolScreen):
    TITLE_TOOL = "SSL Certificate Info"
    PLACEHOLDER = "ph_domain"

    def execute(self, value: str):
        lang = getattr(self.app, "lang", "fr")
        if not value:
            return f"[yellow]{t('enter_domain', lang)}[/yellow]"
        domain = value.strip()
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
        except Exception as e:
            return f"[red]{t('network_error', lang)}: {e}[/red]"

        def _fmt_name(parts):
            flat = {k: v for tup in parts for k, v in tup}
            return flat.get("commonName") or flat.get("organizationName") or "-"

        sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
        san_text = ", ".join(sans[:8]) + (" ..." if len(sans) > 8 else "")
        rows = [
            (t("subject_label", lang), _fmt_name(cert.get("subject", ()))),
            (t("issuer_label", lang), _fmt_name(cert.get("issuer", ()))),
            (t("valid_from_label", lang), cert.get("notBefore", "-")),
            (t("valid_until_label", lang), cert.get("notAfter", "-")),
            (t("sans_label", lang), san_text or "-"),
        ]
        table = _kv_table(rows)
        return Panel(table, title=f"▸ {tool_label('SSL Certificate Info', lang)} — {domain}",
                     border_style="red", padding=(1, 2))


TOOL_SCREENS = {
    ("IP & Network", "Web Lookup"): WebLookupScreen,
    ("IP & Network", "IP Localisation"): IPLocalisationScreen,
    ("IP & Network", "IP Opérateur"): IPOperateurScreen,
    ("IP & Network", "Open Ports"): OpenPortsScreen,
    ("IP & Network", "IP Pinger"): IPPingerScreen,
    ("IP & Network", "IP Generator"): IPGeneratorScreen,
    ("Utilities", "Hash Tools"): HashToolsScreen,
    ("Utilities", "Password Generator"): PasswordGeneratorScreen,
    ("Utilities", "QR Code"): QRCodeScreen,
    ("Utilities", "Text Encoder"): TextEncoderScreen,
    ("Utilities", "Base64 Tools"): Base64ToolsScreen,
    ("Domains & Infrastructure", "WHOIS Lookup"): WhoisLookupScreen,
    ("Domains & Infrastructure", "DNS Records"): DnsRecordsScreen,
    ("Domains & Infrastructure", "Subdomain Finder"): SubdomainFinderScreen,
    ("Domains & Infrastructure", "SSL Certificate Info"): SslCertInfoScreen,
}


# ============================================================
#  PALETTE DE COMMANDES (Ctrl+K) — recherche floue sur tous les outils
# ============================================================

class CommandPalette(ModalScreen):
    BINDINGS = [Binding("escape", "close_palette", "Fermer")]

    def __init__(self, **kw):
        super().__init__(**kw)
        self._refresh_seq = 0

    def compose(self) -> ComposeResult:
        lang = getattr(self.app, "lang", "fr")
        with Vertical(id="palette-box") as box:
            box.border_title = f"▸ {t('palette_placeholder', lang)}"
            yield Input(placeholder=t("palette_placeholder", lang), id="palette-input")
            yield ListView(id="palette-results")

    async def on_mount(self) -> None:
        self.styles.opacity = 0.0
        self.styles.animate("opacity", value=1.0, duration=0.15, easing="out_cubic")
        await self._refresh_results("")
        self.query_one("#palette-input", Input).focus()

    def action_close_palette(self) -> None:
        self.dismiss()

    async def _refresh_results(self, query: str) -> None:
        # clear() est asynchrone (AwaitRemove) -> il FAUT l'attendre. Et comme
        # deux appels peuvent se chevaucher (ex: assigner .value déclenche déjà
        # un Changed, puis on appelle la méthode nous-mêmes juste après), on se
        # protège avec un numéro de génération : si un appel plus récent a
        # démarré pendant notre await, on abandonne au lieu d'ajouter en double.
        self._refresh_seq += 1
        my_seq = self._refresh_seq

        lang = getattr(self.app, "lang", "fr")
        lv = self.query_one("#palette-results", ListView)
        await lv.clear()
        if my_seq != self._refresh_seq:
            return

        q = query.strip().lower()
        for category, tool_name in ALL_TOOLS:
            cat_disp = category_label(category, lang)
            tool_disp = tool_label(tool_name, lang)
            haystack = f"{tool_name} {category} {tool_disp} {cat_disp}".lower()
            if q and q not in haystack:
                continue
            icon = CATEGORY_ICONS.get(category, "•")
            lv.append(ListItem(
                Label(f"{icon}  {tool_disp}   [dim]{cat_disp}[/dim]"),
                name=f"{category}|{tool_name}",
            ))
        if my_seq == self._refresh_seq and len(lv) > 0:
            lv.index = 0

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "palette-input":
            await self._refresh_results(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._open_highlighted()

    def on_list_view_selected(self, event) -> None:
        self._open_item(getattr(event, "item", None))

    def _open_highlighted(self) -> None:
        lv = self.query_one("#palette-results", ListView)
        if lv.index is not None and 0 <= lv.index < len(lv.children):
            self._open_item(lv.children[lv.index])

    def _open_item(self, item) -> None:
        if item is None or item.name is None:
            return
        category, tool_name = item.name.split("|", 1)
        screen_cls = TOOL_SCREENS.get((category, tool_name))
        self.dismiss()
        if screen_cls:
            self.app.push_screen(screen_cls())
        else:
            self.app.push_screen(ComingSoonScreen(tool_name))


# ============================================================
#  MODE DÉMO (F1) — pour filmer sans jouer au clavier à l'écran
# ============================================================

DEMO_SCRIPT = [
    ("IP & Network", "Web Lookup", "8.8.8.8"),
    ("IP & Network", "IP Localisation", "1.1.1.1"),
    ("IP & Network", "IP Generator", "6"),
]


# ============================================================
#  ASSISTANT DE CONFIGURATION (premier lancement)
# ============================================================

class ConfirmQuitScreen(ModalScreen):
    """Petite boîte de dialogue Oui/Non — n'apparaît que si le réglage
    'confirmer avant de quitter' est activé dans l'assistant de config."""

    def __init__(self, lang: str, **kw):
        super().__init__(**kw)
        self.lang = lang

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(t("confirm_quit_message", self.lang), id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button(t("yes", self.lang), id="confirm-yes", variant="error")
                yield Button(t("no", self.lang), id="confirm-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")


class SettingsWizardScreen(ModalScreen):
    """Écran de config initiale : langue, thème, pseudo, son, vitesse de boot,
    dashboard sidebar, confirmation de sortie. Un vrai formulaire Textual
    (Select/Input/Switch) plutôt qu'un menu bricolé au clavier en mode console —
    remplace l'ancien panneau SYSTEM DIAGNOSTICS, jugé inutile et 'fake'."""

    def __init__(self, cfg: dict, reopened: bool = False, **kw):
        super().__init__(**kw)
        self.cfg = dict(cfg)
        self.reopened = reopened
        self._prev_speed = self.cfg.get("boot_speed", "normal")
        if self._prev_speed == "off":
            self._prev_speed = "normal"

    def compose(self) -> ComposeResult:
        lang = self.cfg["language"]
        skip_boot = self.cfg["boot_speed"] == "off"
        title_key = "wizard_title_edit" if self.reopened else "wizard_title"
        with Vertical(id="wizard-box") as box:
            box.border_title = f"▸ {t(title_key, lang)}"
            with VerticalScroll(id="wizard-form"):
                with Vertical(classes="wizard-field"):
                    yield Label(f"▸ {t('wizard_language', lang)}", classes="wizard-label")
                    yield Select(
                        [(LANGUAGE_NAMES[code], code) for code in LANGUAGES],
                        value=self.cfg["language"], id="w-language", allow_blank=False,
                    )
                with Vertical(classes="wizard-field"):
                    yield Label(f"▸ {t('wizard_theme', lang)}", classes="wizard-label", id="wizard-theme-label")
                    yield Select(
                        [(THEME_NAMES[k], k) for k in THEMES],
                        value=self.cfg["theme"], id="w-theme", allow_blank=False,
                    )
                with Vertical(classes="wizard-field"):
                    yield Label(f"▸ {t('wizard_pseudo', lang)}", classes="wizard-label", id="wizard-pseudo-label")
                    yield Input(value=self.cfg["pseudo"], id="w-pseudo")

                with Vertical(classes="wizard-field"):
                    with Horizontal(classes="wizard-switch-row"):
                        yield Switch(value=self.cfg["sound"], id="w-sound")
                        yield Label(f"▸ {t('wizard_sound', lang)}", id="wizard-sound-label")

                with Vertical(classes="wizard-field"):
                    yield Label(f"▸ {t('wizard_boot_speed', lang)}", classes="wizard-label", id="wizard-speed-label")
                    yield Select(
                        [
                            (t("boot_speed_normal", lang), "normal"),
                            (t("boot_speed_fast", lang), "fast"),
                        ],
                        value=self._prev_speed, id="w-speed", allow_blank=False,
                        disabled=skip_boot,
                    )
                    with Horizontal(classes="wizard-switch-row"):
                        yield Switch(value=skip_boot, id="w-skip-boot")
                        yield Label(f"▸ {t('wizard_skip_boot', lang)}", id="wizard-skipboot-label")

                with Vertical(classes="wizard-field"):
                    with Horizontal(classes="wizard-switch-row"):
                        yield Switch(value=self.cfg["show_sidebar_dashboard"], id="w-sidebar")
                        yield Label(f"▸ {t('wizard_sidebar', lang)}", id="wizard-sidebar-label")

                with Vertical(classes="wizard-field"):
                    with Horizontal(classes="wizard-switch-row"):
                        yield Switch(value=self.cfg["confirm_quit"], id="w-confirm-quit")
                        yield Label(f"▸ {t('wizard_confirm_quit', lang)}", id="wizard-confirmquit-label")

            start_key = "wizard_save" if self.reopened else "wizard_start"
            yield Button(f"▸ {t(start_key, lang)}", id="w-start", variant="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "w-language":
            self.cfg["language"] = event.value
            self._retranslate()
        elif event.select.id == "w-theme":
            self.cfg["theme"] = event.value
            self.app.active_theme = event.value
            self.app.refresh_css()
        elif event.select.id == "w-speed":
            self._prev_speed = event.value
            self.cfg["boot_speed"] = event.value

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "w-sound":
            self.cfg["sound"] = event.value
        elif event.switch.id == "w-sidebar":
            self.cfg["show_sidebar_dashboard"] = event.value
        elif event.switch.id == "w-confirm-quit":
            self.cfg["confirm_quit"] = event.value
        elif event.switch.id == "w-skip-boot":
            speed_select = self.query_one("#w-speed", Select)
            if event.value:
                self.cfg["boot_speed"] = "off"
                speed_select.disabled = True
            else:
                self.cfg["boot_speed"] = self._prev_speed
                speed_select.value = self._prev_speed
                speed_select.disabled = False

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "w-pseudo":
            self.cfg["pseudo"] = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "w-start":
            self._finish()

    def _retranslate(self) -> None:
        """Retraduit l'écran EN DIRECT quand on change la langue -> preview
        immédiat, pas besoin de valider pour voir le résultat."""
        lang = self.cfg["language"]
        title_key = "wizard_title_edit" if self.reopened else "wizard_title"
        self.query_one("#wizard-box", Vertical).border_title = f"▸ {t(title_key, lang)}"
        self.query_one("#wizard-theme-label", Label).update(f"▸ {t('wizard_theme', lang)}")
        self.query_one("#wizard-pseudo-label", Label).update(f"▸ {t('wizard_pseudo', lang)}")
        self.query_one("#wizard-sound-label", Label).update(f"▸ {t('wizard_sound', lang)}")
        self.query_one("#wizard-speed-label", Label).update(f"▸ {t('wizard_boot_speed', lang)}")
        self.query_one("#wizard-skipboot-label", Label).update(f"▸ {t('wizard_skip_boot', lang)}")
        self.query_one("#wizard-sidebar-label", Label).update(f"▸ {t('wizard_sidebar', lang)}")
        self.query_one("#wizard-confirmquit-label", Label).update(f"▸ {t('wizard_confirm_quit', lang)}")
        start_key = "wizard_save" if self.reopened else "wizard_start"
        self.query_one("#w-start", Button).label = f"▸ {t(start_key, lang)}"
        speed_select = self.query_one("#w-speed", Select)
        speed_select.set_options([
            (t("boot_speed_normal", lang), "normal"),
            (t("boot_speed_fast", lang), "fast"),
        ])
        speed_select.value = self._prev_speed

    def _finish(self) -> None:
        self.cfg["pseudo"] = self.cfg.get("pseudo", "").strip() or DEFAULT_CONFIG["pseudo"]
        self.cfg["configured"] = True
        save_config(self.cfg)
        self.dismiss(self.cfg)


# ============================================================
#  APP PRINCIPALE
# ============================================================

class CrownToolsApp(App):
    CSS = """
    Screen {
        background: $crown-bg;
    }

    /* Textual dessine par défaut un bouton "relief" avec des demi-blocs "tall"
       en haut/bas (border-top/border-bottom) -> même souci de glyphes cassés
       sur la police de cmd.exe que Select/Switch. Bordure pleine "round"
       partout, sur TOUS les boutons de l'app, base + focus + survol. */
    Button {
        border: round $crown-border !important;
    }

    Button:focus, Button:hover {
        border: round $crown-accent !important;
    }

    #header-row {
        height: 9;
        border: round $crown-accent;
        margin: 1 1 0 1;
        padding: 0 2;
    }

    Banner {
        width: 1fr;
        padding: 1 1 0 0;
    }

    #banner-art {
        width: 100%;
    }

    #banner-sub {
        color: $crown-text-dim;
    }

    SessionStats {
        width: auto;
        content-align: center top;
        padding: 2 2 0 0;
    }

    Clock {
        width: auto;
        content-align: right top;
        padding: 1 0 0 0;
    }

    #main-area {
        height: 1fr;
        padding: 1;
    }

    CategoryList {
        width: 34;
        border: round $crown-accent;
        border-title-color: $crown-accent;
        border-title-style: bold;
        padding: 1 2;
        margin-right: 1;
    }

    ToolPanel {
        width: 1fr;
        border: round $crown-accent;
        border-title-color: $crown-accent;
        border-title-style: bold;
        padding: 1 2;
    }

    #radar-title {
        margin-top: 1;
        border-top: solid $crown-border;
        padding-top: 1;
        color: $crown-text-dim;
    }

    #mini-radar {
        height: 3;
        color: $crown-text-dim;
    }

    ListView {
        background: transparent;
        border: none;
    }

    ListItem {
        padding: 0 1;
        color: $crown-text;
        transition: background 120ms, color 120ms;
    }

    ListItem:hover {
        background: $crown-border;
    }

    ListView > ListItem.-highlight {
        background: $crown-accent-2;
        color: white;
        text-style: bold;
    }

    ListView:focus > ListItem.-highlight {
        background: $crown-accent;
        color: $crown-bg;
    }

    #tool-description {
        color: $crown-text-dim;
        padding: 1 1 0 1;
        border-top: solid $crown-border;
        margin-top: 1;
        height: auto;
    }

    CommandPalette {
        align: center middle;
        background: black 70%;
    }

    #palette-box {
        width: 70%;
        max-width: 90;
        height: auto;
        max-height: 24;
        border: round $crown-accent;
        border-title-color: $crown-accent;
        border-title-style: bold;
        background: $crown-bg-alt;
        padding: 1 2;
    }

    #palette-input {
        border: solid $crown-border;
    }

    #palette-input:focus {
        border: solid $crown-accent;
    }

    #palette-results {
        height: auto;
        max-height: 16;
        margin-top: 1;
    }

    SettingsWizardScreen {
        align: center middle;
        background: $crown-bg;
    }

    #wizard-box {
        width: 70;
        height: 90%;
        border: round $crown-accent;
        border-title-color: $crown-accent;
        border-title-style: bold;
        background: $crown-bg-alt;
        padding: 1 3;
    }

    #wizard-form {
        height: 1fr;
        padding-right: 1;
    }

    .wizard-field {
        height: auto;
        margin-bottom: 1;
    }

    .wizard-label {
        color: $crown-text-dim;
    }

    #wizard-form Select, #wizard-form Input {
        border: round $crown-border;
        background: $crown-bg;
    }

    #wizard-form Select:focus, #wizard-form Input:focus {
        border: round $crown-accent;
    }

    /* Textual utilise par défaut un style de bordure "tall" (demi-blocs fins)
       pour SelectCurrent/SelectOverlay -> mal supporté par la police de la
       console cmd.exe historique (glyphes qui s'affichent comme des blocs
       cassés). On force "round", déjà utilisé partout ailleurs dans l'app et
       confirmé lisible dans ce terminal. */
    SelectCurrent, Select > SelectOverlay {
        border: round $crown-border;
    }

    SelectCurrent:focus, Select > SelectOverlay:focus {
        border: round $crown-accent;
    }

    /* Switch utilise "tall" par défaut (base ET focus) dans Textual -> même
       souci de glyphes cassés sur cmd.exe que Select. On force "round"
       partout, y compris en base (pas seulement au focus), sinon le défaut
       Textual reste actif tant que le switch n'a pas le focus. */
    Switch {
        border: round $crown-border;
    }

    Switch:focus {
        border: round $crown-accent;
    }

    Switch > .switch--slider {
        color: $crown-border;
        background: $crown-bg;
    }

    Switch.-on > .switch--slider {
        color: $crown-accent;
    }

    .wizard-switch-row {
        height: 3;
        align: left middle;
    }

    .wizard-switch-row Label {
        padding-left: 2;
        color: $crown-text;
    }

    #w-start {
        margin-top: 1;
        width: 100%;
    }

    ConfirmQuitScreen {
        align: center middle;
        background: black 60%;
    }

    #confirm-box {
        width: 44;
        height: auto;
        border: round $crown-accent;
        border-title-color: $crown-accent;
        background: $crown-bg-alt;
        padding: 1 2;
    }

    #confirm-message {
        content-align: center middle;
        color: $crown-text;
        padding-bottom: 1;
    }

    #confirm-buttons {
        align: center middle;
        height: 3;
    }

    #confirm-buttons Button {
        margin: 0 1;
        width: 12;
    }

    StatusBar {
        height: 1;
        background: $crown-bg;
        border-top: solid $crown-border;
        color: $crown-text-dim;
        padding: 0 2;
    }

    #tool-toolbar {
        height: auto;
        border: round $crown-accent;
        margin: 1 2 0 2;
        padding: 0 1;
    }

    #title-row {
        height: 3;
        padding: 0 1;
        align: left middle;
    }

    #back-btn {
        width: 12;
        margin-right: 2;
    }

    #screen-title {
        color: $crown-accent;
        text-style: bold;
    }

    #input-row {
        height: 3;
        padding: 0 1;
    }

    #tool-input {
        width: 1fr;
        border: solid $crown-border;
    }

    #tool-input:focus {
        border: solid $crown-accent;
    }

    #run-btn {
        width: 16;
        margin-left: 1;
    }

    #result-scroll {
        padding: 1 2;
        margin: 1 2;
        border: round $crown-border;
        border-title-color: $crown-text-dim;
        height: 1fr;
    }

    .result-text {
        color: $crown-text;
    }

    #coming-soon-rain {
        height: 10;
        border-bottom: solid $crown-border;
    }

    #coming-soon-msg {
        padding: 2;
        align: center middle;
        height: 1fr;
    }

    #dev-panel {
        width: 60;
        height: auto;
    }

    Toast {
        dock: bottom;
        width: auto;
        max-width: 60;
        margin: 0 2 2 0;
        padding: 1 2;
        border: round $crown-border;
        background: $crown-bg-alt;
        color: $crown-text;
    }

    .toast-success {
        border: round $crown-success;
        color: $crown-success;
    }

    .toast-error {
        border: round $crown-error;
        color: $crown-error;
    }
    """

    BINDINGS = [
        Binding("q", "request_quit", "Quitter"),
        Binding("d", "toggle_theme", "Thème"),
        Binding("f1", "run_demo", "Démo"),
        Binding("ctrl+k", "open_palette", "Recherche"),
    ]

    def __init__(self, cfg: dict = None):
        # attributs posés AVANT super().__init__() : App.__init__ appelle déjà
        # get_css_variables() en interne pour construire la stylesheet, donc
        # self.active_theme doit exister avant cet appel.
        self.config = cfg or load_config()
        self.lang = self.config.get("language", "fr")
        self.active_theme = self.config.get("theme", "void_red")
        super().__init__()

    def get_css_variables(self) -> dict:
        variables = super().get_css_variables()
        variables.update(THEMES.get(self.active_theme, THEMES["void_red"]))
        return variables

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-row"):
            yield Banner()
            yield SessionStats()
            yield Clock()
        with Horizontal(id="main-area"):
            yield CategoryList()
            yield ToolPanel()
        yield StatusBar()

    async def on_mount(self) -> None:
        await self.query_one(ToolPanel).show_empty()
        if not self.config.get("show_sidebar_dashboard", True):
            self.query_one("#radar-title").display = False
            self.query_one(MiniLoad).display = False
        if self.config.get("configured"):
            self._start_dashboard()
        else:
            self.push_screen(SettingsWizardScreen(self.config), self._on_wizard_done)

    async def _on_wizard_done(self, cfg: dict) -> None:
        global _sound_enabled
        self.config = cfg
        self.lang = cfg.get("language", "fr")
        self.active_theme = cfg.get("theme", "void_red")
        _sound_enabled = cfg.get("sound", True)
        if not cfg.get("show_sidebar_dashboard", True):
            self.query_one("#radar-title").display = False
            self.query_one(MiniLoad).display = False
        self.refresh_css()
        await self._apply_translations()
        self._start_dashboard()
        _beep(880, 60)

    async def _on_settings_reopened(self, cfg: dict) -> None:
        """Ré-ouverture de l'assistant DEPUIS le dashboard (catégorie Settings),
        pas au tout premier lancement -> même application de config que
        _on_wizard_done, mais SANS rappeler _start_dashboard() (qui rajouterait
        un nouveau timer de pulse à chaque réouverture, cumulatif)."""
        global _sound_enabled
        self.config = cfg
        self.lang = cfg.get("language", "fr")
        self.active_theme = cfg.get("theme", "void_red")
        _sound_enabled = cfg.get("sound", True)
        show_sidebar = cfg.get("show_sidebar_dashboard", True)
        self.query_one("#radar-title").display = show_sidebar
        self.query_one(MiniLoad).display = show_sidebar
        self.refresh_css()
        await self._apply_translations()
        _beep(880, 60)

    async def _apply_translations(self) -> None:
        """Retraduit les widgets déjà montés — utile seulement au tout premier
        lancement (l'utilisateur peut changer de langue dans l'assistant après
        que le dashboard soit déjà composé en français par défaut)."""
        lang = self.lang
        self.query_one("#banner-sub", Static).update(f"[dim]v2 · {t('app_subtitle', lang)}[/dim]")
        self.query_one(CategoryList).retranslate(lang)
        self.query_one(StatusBar).retranslate(lang)
        await self.query_one(ToolPanel).show_empty()

    def _start_dashboard(self) -> None:
        self.run_worker(self._dashboard_reveal(), exclusive=True, group="reveal")
        self.set_interval(2.2, self._pulse_category_border)

    async def _dashboard_reveal(self) -> None:
        """Cascade d'entrée juste après le boot : au lieu d'un cut sec vers l'app,
        chaque bloc du dashboard apparaît l'un après l'autre. Enchaîne l'énergie du
        boot cinématique au lieu de retomber à plat sur une interface statique."""
        widgets = [
            self.query_one("#header-row"),
            self.query_one(CategoryList),
            self.query_one(ToolPanel),
            self.query_one(StatusBar),
        ]
        for w in widgets:
            w.styles.opacity = 0.0
        for w in widgets:
            w.styles.animate("opacity", value=1.0, duration=0.3, easing="out_cubic")
            await asyncio.sleep(0.1)

    def _pulse_category_border(self) -> None:
        """Léger battement de couleur sur la bordure de la liste -> l'interface
        reste 'vivante' même sans interaction, pas figée."""
        cat_list = self.query_one(CategoryList)
        current = getattr(cat_list, "_pulse_on", False)
        cat_list.styles.border_right = ("solid", "#f87171" if not current else "#7f1d1d")
        cat_list._pulse_on = not current

    async def on_list_view_highlighted(self, event) -> None:
        item = getattr(event, "item", None)
        if item is None or item.name is None:
            return
        if "|" in item.name:
            _, tool_name = item.name.split("|", 1)
            self.query_one(ToolPanel).show_description(tool_name)
        else:
            await self.query_one(ToolPanel).show_category(item.name)

    async def on_list_view_selected(self, event) -> None:
        item = getattr(event, "item", None)
        if item is None or item.name is None:
            return
        if "|" in item.name:
            category, tool_name = item.name.split("|", 1)
            if category == "Settings" and tool_name == "Configuration":
                self.push_screen(SettingsWizardScreen(self.config, reopened=True), self._on_settings_reopened)
                return
            screen_cls = TOOL_SCREENS.get((category, tool_name))
            if screen_cls:
                self.push_screen(screen_cls())
            else:
                self.push_screen(ComingSoonScreen(tool_name))
        else:
            await self.query_one(ToolPanel).show_category(item.name)

    def action_toggle_theme(self) -> None:
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        if self.config.get("confirm_quit"):
            self.push_screen(ConfirmQuitScreen(self.lang), self._on_quit_confirmed)
        else:
            self.exit()

    def _on_quit_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self.exit()

    def action_open_palette(self) -> None:
        self.push_screen(CommandPalette())

    def action_run_demo(self) -> None:
        self.run_worker(self._demo_sequence(), exclusive=True, group="demo")

    async def _demo_sequence(self) -> None:
        cat_list = self.query_one("#category-list", ListView)
        for idx in range(len(MENU)):
            cat_list.index = idx
            await asyncio.sleep(0.8)

        for category, tool_name, value in DEMO_SCRIPT:
            await self.query_one(ToolPanel).show_category(category)
            await asyncio.sleep(0.4)
            screen_cls = TOOL_SCREENS.get((category, tool_name))
            if not screen_cls:
                continue
            screen = screen_cls()
            self.push_screen(screen)
            await asyncio.sleep(0.35)
            screen.query_one("#tool-input", Input).value = value
            screen.run_tool()
            await asyncio.sleep(2.4)
            screen.action_close_screen()
            await asyncio.sleep(0.4)


if __name__ == "__main__":
    _cfg = load_config()
    _sound_enabled = _cfg["sound"]
    run_boot_sequence(_cfg)
    CrownToolsApp(_cfg).run()
