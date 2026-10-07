"""
intro_valider.py — Animation d'intro VALIDÉE de Crown-Tools.

Contenu : le reveal néon complet du wordmark "CROWN-TOOLS" — champ d'étoiles,
mise au point progressive avec aberration chromatique, lock-in (impact sonore +
secousse caméra + gerbe de braises), balayage lumineux et onde de choc sur le
MÊME rendu néon, puis l'attente "[ PRESS ENTER ]" (vrai texte terminal, jamais
flou) jusqu'à ce que la touche soit pressée. Isolé de main.py à la demande
explicite : c'est la version jugée bonne, on ne la retouche plus au fil des
itérations sur le reste de l'app — sauf demande explicite ponctuelle (ex: la
touche Entrée qui interrompt l'animation à tout moment, pas seulement à
l'écran final, ajoutée sans modifier le rendu lui-même).

Point d'entrée unique : play_neon_intro(console). Ne connaît rien de main.py —
on lui passe juste le Console Rich déjà configuré (VT processing / UTF-8 /
color_system forcés côté appelant pour la compat cmd.exe).
"""

import os
import math
import random
import time
import platform

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from rich.text import Text
from rich.style import Style
from rich.live import Live

BOOT_FPS = 24
FRAME_DELAY = 1 / BOOT_FPS


def _beep(freq: int = 880, dur: int = 90) -> None:
    """Petit bip synthétique (Windows uniquement). Ne fait jamais planter le boot
    si le module n'est pas disponible ou si le son est indisponible."""
    try:
        import winsound
        winsound.Beep(freq, dur)
    except Exception:
        pass


def _console_size(console) -> tuple:
    size = console.size
    width = max(60, min(size.width, 200))
    height = max(20, min(size.height, 55))
    return width, height


def _load_logo_font(size: int) -> "ImageFont.FreeTypeFont":
    """Police bien grasse pour le wordmark. Cherche d'abord dans Fonts/ Windows,
    retombe sur une police par défaut si rien n'est trouvé (autre OS)."""
    fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    candidates = []
    for name in ("ariblk.ttf", "impact.ttf", "arialbd.ttf"):
        candidates.append(os.path.join(fonts_dir, name))
        candidates.append(name)
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _rgb_array_to_lines(arr: "np.ndarray") -> list:
    """Convertit un tableau RGB (H*2, W, 3) en liste de Text Rich (une par ligne de
    terminal), demi-bloc (▀) true-color, 2 'pixels' verticaux par cellule. Regroupe
    les couleurs identiques consécutives en un seul style pour rester rapide."""
    h2, w, _ = arr.shape
    h = h2 // 2
    lines = []
    for row in range(h):
        top = arr[row * 2]
        bot = arr[row * 2 + 1]
        line = Text()
        run_start = 0
        prev_key = None
        for col in range(w):
            key = (top[col, 0], top[col, 1], top[col, 2], bot[col, 0], bot[col, 1], bot[col, 2])
            if prev_key is not None and key != prev_key:
                tr, tg, tb, br, bg, bb = prev_key
                line.append(
                    "▀" * (col - run_start),
                    style=Style(color=f"#{tr:02x}{tg:02x}{tb:02x}", bgcolor=f"#{br:02x}{bg:02x}{bb:02x}"),
                )
                run_start = col
            prev_key = key
        if prev_key is not None:
            tr, tg, tb, br, bg, bb = prev_key
            line.append(
                "▀" * (w - run_start),
                style=Style(color=f"#{tr:02x}{tg:02x}{tb:02x}", bgcolor=f"#{br:02x}{bg:02x}{bb:02x}"),
            )
        lines.append(line)
    return lines


def _lines_to_text(lines: list) -> Text:
    """Rassemble une liste de Text (une par ligne) en un seul Text multi-lignes."""
    result = Text()
    for i, line in enumerate(lines):
        if i:
            result.append("\n")
        result.append_text(line)
    return result


def _rgb_array_to_text(arr: "np.ndarray") -> Text:
    """Passe par Rich (Live) plutôt que des séquences ANSI écrites à la main ->
    compatible cmd.exe / consoles Windows qui n'ont pas le VT processing activé
    (Rich gère cette compat lui-même)."""
    return _lines_to_text(_rgb_array_to_lines(arr))


def _compose_frame(sharp: "np.ndarray", glow: "np.ndarray", bloom: "np.ndarray",
                    star_layer=None, brightness: float = 1.0) -> "np.ndarray":
    """Recompose l'image (texte tout en rouge + halo + bloom [+ étoiles]) — même
    formule que la boucle de reveal, réutilisée par le balayage/l'explosion/l'attente
    pour rester visuellement cohérente avec l'état final du texte néon."""
    # le cœur net (sharp) domine largement -> le texte doit rester lisible et net,
    # glow/bloom ne sont qu'un léger liseré autour des lettres, pas un flou qui les
    # recouvre. Tout est tiré vers le rouge (peu de vert/bleu), pas de cœur blanc.
    star = star_layer if star_layer is not None else 0.0
    r = np.clip(sharp * 1.0 + glow * 0.55 + bloom * 0.22 + star * 0.7, 0, 1)
    g = np.clip(sharp * 0.10 + glow * 0.08 + bloom * 0.03 + star * 0.75, 0, 1)
    b = np.clip(sharp * 0.08 + glow * 0.05 + bloom * 0.02 + star * 0.9, 0, 1)
    return np.stack([r, g, b], axis=-1) * brightness


def _pulse_red_hex(phase: float) -> str:
    """Rouge pur dont l'intensité pulse (0.55..1.0), jamais trop sombre."""
    intensity = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(phase))
    v = int(255 * intensity)
    return f"#{v:02x}0000"


def _wait_enter_pressed() -> bool:
    """Sondage NON bloquant du clavier : True si Entrée vient d'être pressée.
    Windows uniquement (msvcrt) ; ne casse jamais rien ailleurs."""
    try:
        import msvcrt
    except ImportError:
        return False
    if msvcrt.kbhit():
        ch = msvcrt.getch()
        if ch in (b"\r", b"\n"):
            return True
    return False


def play_neon_intro(console, speed_multiplier: float = 1.0) -> None:
    """Reveal néon complet : le wordmark 'CROWN-TOOLS' émerge d'un champ d'étoiles,
    aberration chromatique qui se stabilise pendant que la mise au point se fait,
    gerbe de braises + secousse caméra au lock-in, balayage lumineux + onde de choc
    sur le même texte, puis attente de la touche Entrée ("[ PRESS ENTER ]" en vrai
    texte terminal, jamais flou). Rendu true-color demi-bloc (PIL + numpy) via Live.
    `console` doit déjà être configuré côté appelant (VT processing / UTF-8 /
    color_system) pour un rendu correct sous cmd.exe. `speed_multiplier` < 1.0
    accélère toute la séquence (ex: 0.5 = deux fois plus vite) sans rien changer
    à l'animation elle-même."""

    def _sleep(seconds: float) -> None:
        time.sleep(seconds * speed_multiplier)

    width, height = _console_size(console)
    canvas_w, canvas_h = width, height * 2

    # rendu haute résolution du texte, une seule fois (supersampling + downscale net)
    scale = 4
    hi_w, hi_h = canvas_w * scale, canvas_h * scale
    text = "CROWN-TOOLS"
    font_size = int(hi_h * 0.62)
    font = _load_logo_font(font_size)

    hi_img = Image.new("L", (hi_w, hi_h), 0)
    draw = ImageDraw.Draw(hi_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    while tw > hi_w * 0.94 and font_size > 8:
        font_size -= max(1, font_size // 40)
        font = _load_logo_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (hi_w - tw) // 2 - bbox[0]
    ty = (hi_h - th) // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=255)

    core_mask = np.asarray(hi_img.resize((canvas_w, canvas_h), Image.LANCZOS), dtype=np.float32) / 255.0
    core_mask = np.clip((core_mask - 0.5) * 2.2 + 0.5, 0.0, 1.0)  # contraste fort : arêtes dures, pas de gris délavé
    base_u8 = (core_mask * 255).astype(np.uint8)
    bright_ys, bright_xs = np.where(core_mask > 0.55)  # pixels du texte = points d'ancrage des braises

    # rayons de flou PROPORTIONNELS au canvas : des valeurs fixes (ex: 14px) sont
    # énormes sur un canvas qui ne fait souvent que 40-80px de haut, et noient le
    # texte dans le flou au lieu de ne faire qu'un léger halo autour des lettres.
    glow_radius = max(0.5, canvas_h * 0.010)
    bloom_radius = max(1.0, canvas_h * 0.024)

    # --- champ d'étoiles : dérive lentement vers le haut, en arrière-plan ---
    stars = [
        {
            "x": random.uniform(0, canvas_w),
            "y": random.uniform(0, canvas_h),
            "speed": random.uniform(1.5, 6.0),
            "bright": random.uniform(0.12, 0.5),
        }
        for _ in range(70)
    ]

    def _draw_stars() -> np.ndarray:
        layer = np.zeros((canvas_h, canvas_w), dtype=np.float32)
        for s in stars:
            s["y"] -= s["speed"] * 0.05
            if s["y"] < 0:
                s["y"] = canvas_h - 1
                s["x"] = random.uniform(0, canvas_w)
            xi, yi = int(s["x"]), int(s["y"])
            if 0 <= xi < canvas_w and 0 <= yi < canvas_h:
                layer[yi, xi] = max(layer[yi, xi], s["bright"])
        return layer

    total_frames = 56
    _beep(300, 60)

    with Live(console=console, screen=True, auto_refresh=False) as live:
        for frame in range(total_frames):
            if _wait_enter_pressed():
                return
            t = frame / (total_frames - 1)
            ease = t * t * (3 - 2 * t)  # smoothstep : accélère puis ralentit

            blur_radius = max(0.0, 16 * (1 - ease) ** 2)
            aberration = max(0.0, 7 * (1 - ease))
            if ease < 0.55:
                aberration += random.uniform(-1, 1) * (1 - ease) * 2
            brightness = 0.25 + 0.75 * min(ease * 1.4, 1.0)

            core_img = Image.fromarray(base_u8, mode="L")
            if blur_radius > 0.3:
                core_img = core_img.filter(ImageFilter.GaussianBlur(blur_radius))
            sharp = np.asarray(core_img, dtype=np.float32) / 255.0

            glow_img = Image.fromarray(base_u8, mode="L").filter(ImageFilter.GaussianBlur(glow_radius))
            glow = np.asarray(glow_img, dtype=np.float32) / 255.0
            bloom_img = Image.fromarray(base_u8, mode="L").filter(ImageFilter.GaussianBlur(bloom_radius))
            bloom = np.asarray(bloom_img, dtype=np.float32) / 255.0

            stars_layer = _draw_stars() * (1.0 - ease * 0.6)
            frame_rgb = _compose_frame(sharp, glow, bloom, star_layer=stars_layer, brightness=brightness)

            shift = int(round(aberration))
            if shift != 0:
                frame_rgb[:, :, 0] = np.roll(frame_rgb[:, :, 0], shift, axis=1)
                frame_rgb[:, :, 2] = np.roll(frame_rgb[:, :, 2], -shift, axis=1)

            arr = np.clip(frame_rgb * 255, 0, 255).astype(np.uint8)
            live.update(_rgb_array_to_text(arr), refresh=True)
            _sleep(FRAME_DELAY)

        # --- lock-in : impact sonore + secousse caméra + gerbe de braises ---
        _beep(140, 70)
        _beep(1200, 90)

        n_bright = len(bright_xs)
        embers = []
        if n_bright > 0:
            for _ in range(50):
                i = random.randrange(n_bright)
                embers.append({
                    "x": float(bright_xs[i]), "y": float(bright_ys[i]),
                    "vx": random.uniform(-1.4, 1.4), "vy": random.uniform(-2.6, -0.4),
                    "life": random.uniform(0.6, 1.0),
                })

        shake_frames = 6
        burst_frames = 20
        for f in range(burst_frames):
            if _wait_enter_pressed():
                return
            base_rgb = _compose_frame(sharp, glow, bloom)

            for e in embers:
                e["x"] += e["vx"]
                e["y"] += e["vy"]
                e["vy"] += 0.12  # gravité légère
                e["life"] -= 1.0 / burst_frames
                xi, yi = int(e["x"]), int(e["y"])
                if e["life"] > 0 and 0 <= xi < canvas_w and 0 <= yi < canvas_h:
                    intensity = max(e["life"], 0.0)
                    base_rgb[yi, xi, 0] = min(base_rgb[yi, xi, 0] + intensity, 1.0)
                    base_rgb[yi, xi, 1] = min(base_rgb[yi, xi, 1] + intensity * 0.55, 1.0)
                    base_rgb[yi, xi, 2] = min(base_rgb[yi, xi, 2] + intensity * 0.15, 1.0)

            frame_arr = np.clip(base_rgb * 255, 0, 255).astype(np.uint8)
            if f < shake_frames:
                mag = shake_frames - f
                frame_arr = np.roll(frame_arr, random.randint(-mag, mag), axis=0)
                frame_arr = np.roll(frame_arr, random.randint(-mag, mag), axis=1)

            live.update(_rgb_array_to_text(frame_arr), refresh=True)
            _sleep(FRAME_DELAY)

        _sleep(0.25)

        # --- balayage lumineux gauche -> droite, SUR LE MÊME texte néon (pas de
        # bascule vers un autre rendu) ---
        text_alpha = np.clip(sharp + glow * 0.5, 0, 1)
        settled_base = _compose_frame(sharp, glow, bloom)
        band_width = max(3.0, canvas_w * 0.03)
        for sx in range(-int(canvas_w * 0.15), canvas_w + int(canvas_w * 0.15), max(2, canvas_w // 45)):
            if _wait_enter_pressed():
                return
            xs = np.arange(canvas_w)
            band = np.exp(-((xs - sx) ** 2) / (2 * band_width ** 2))
            band2d = np.tile(band, (canvas_h, 1)) * text_alpha
            frame_rgb = settled_base.copy()
            for c in range(3):
                frame_rgb[:, :, c] = np.clip(frame_rgb[:, :, c] + band2d, 0, 1)
            arr = np.clip(frame_rgb * 255, 0, 255).astype(np.uint8)
            live.update(_rgb_array_to_text(arr), refresh=True)
            _sleep(0.014)

        _sleep(0.1)
        _beep(700, 70)

        # --- onde de choc ("explosion") qui balaie tout l'écran depuis le centre ---
        yy, xx = np.mgrid[0:canvas_h, 0:canvas_w]
        cy, cx = canvas_h / 2, canvas_w / 2
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        max_r = float(dist.max()) + 8
        ring_width = canvas_h * 0.035
        r = 0.0
        while r < max_r:
            if _wait_enter_pressed():
                return
            band = np.exp(-((dist - r) ** 2) / (2 * ring_width ** 2))
            ring = band * (text_alpha * 0.9 + 0.12)
            frame_rgb = settled_base.copy()
            for c in range(3):
                frame_rgb[:, :, c] = np.clip(frame_rgb[:, :, c] + ring, 0, 1)
            arr = np.clip(frame_rgb * 255, 0, 255).astype(np.uint8)
            live.update(_rgb_array_to_text(arr), refresh=True)
            r += canvas_h * 0.05
            _sleep(0.014)

        _sleep(0.2)

        # --- attente : "PRESS ENTER" en VRAI TEXTE terminal (pas du pixel art ->
        # ne peut pas être flou, c'est un glyphe natif du terminal). On l'insère à
        # une ligne précise (bas-milieu de l'écran, pas collé au tout dernier rang)
        # sans retirer ni ajouter de ligne au canvas -> jamais de débordement.
        prompt_text = "[ PRESS ENTER ]"
        if len(prompt_text) > canvas_w:
            prompt_text = prompt_text[:canvas_w]
        prompt = prompt_text.center(canvas_w)
        prompt_row = min(height - 1, max(0, int(height * 0.80)))

        def _frame_with_prompt(arr: "np.ndarray", color: str) -> Text:
            lines = _rgb_array_to_lines(arr)
            lines[prompt_row] = Text(prompt, style=Style(color=color, bold=True, bgcolor="#000000"))
            return _lines_to_text(lines)

        if platform.system().lower() == "windows":
            frame = 0
            while not _wait_enter_pressed():
                stars_layer = _draw_stars() * 0.35
                base = _compose_frame(sharp, glow, bloom, star_layer=stars_layer)
                arr = np.clip(base * 255, 0, 255).astype(np.uint8)
                live.update(_frame_with_prompt(arr, _pulse_red_hex(frame * 0.15)), refresh=True)
                frame += 1
                _sleep(FRAME_DELAY)
        else:
            # pas de lecture clavier non bloquante portable ici : on affiche l'état
            # final avec le prompt puis on enchaîne après une courte pause.
            base = _compose_frame(sharp, glow, bloom)
            arr = np.clip(base * 255, 0, 255).astype(np.uint8)
            live.update(_frame_with_prompt(arr, "#c81414"), refresh=True)
            _sleep(1.2)
