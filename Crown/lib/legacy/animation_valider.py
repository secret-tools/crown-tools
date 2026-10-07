"""
animation_valider.py — Animations VALIDÉES du boot Crown-Tools.

Contenu : le balayage lumineux (surbrillance gauche -> droite sur le logo) et
l'onde de choc finale ("explosion" qui part du centre). Isolées de main.py à la
demande explicite : ce sont les deux effets jugés bons, on ne les retouche plus
au fil des itérations sur le reste du boot.

Ces fonctions ne connaissent rien de main.py : on leur passe le `live` (rich.live.Live)
déjà ouvert, le `mask` du logo ({(x, y): "char"}), et les dimensions. Elles ne font
qu'écrire dedans via live.update(..., refresh=True).
"""

import time

from rich.text import Text


def sweep_reveal(live, mask: dict, off_x: int, art_w: int, width: int, height: int,
                  step: int = 2, delay: float = 0.018) -> None:
    """Balayage lumineux qui traverse le logo de gauche à droite."""
    for sweep in range(-8, art_w + 8, step):
        text = Text()
        for y in range(height):
            for x in range(width):
                cell = mask.get((x, y))
                if cell is None:
                    text.append(" ")
                    continue
                dist = abs((x - off_x) - sweep)
                style = "bold white" if dist < 3 else "bold bright_red" if dist < 7 else "bold red"
                text.append(cell, style=style)
            text.append("\n")
        live.update(text, refresh=True)
        time.sleep(delay)


def shockwave_pulse(live, mask: dict, width: int, height: int,
                     step: float = 3.2, delay: float = 0.016) -> None:
    """Onde de choc ('explosion') qui part du centre du logo et balaie tout l'écran."""
    cx, cy = width / 2, height / 2
    max_r = ((width / 2) ** 2 + (height * 1.1) ** 2) ** 0.5 + 6
    r = 0.0
    while r < max_r:
        text = Text()
        for y in range(height):
            for x in range(width):
                dist = ((x - cx) ** 2 + ((y - cy) * 2.2) ** 2) ** 0.5
                band = abs(dist - r)
                cell = mask.get((x, y))
                if cell is not None:
                    style = "bold white" if band < 4 else "bold red"
                    text.append(cell, style=style)
                elif band < 1.6:
                    text.append("·", style="bright_red")
                else:
                    text.append(" ")
            text.append("\n")
        live.update(text, refresh=True)
        r += step
        time.sleep(delay)


def hold_final(live, mask: dict, width: int, height: int, duration: float = 0.4) -> None:
    """État final stable : le logo seul, tout le reste éteint."""
    final = Text()
    for y in range(height):
        for x in range(width):
            cell = mask.get((x, y))
            final.append(cell if cell else " ", style="bold red" if cell else "")
        final.append("\n")
    live.update(final, refresh=True)
    time.sleep(duration)
