"""
Crown Cyberpunk AAA VFX Animation Engine ($20,000 Grade Terminal Intro).
Features:
- Matrix Glitch Decryption Particle Stream
- Chromatic Aberration & Liquid Neon Wave (Crimson -> Violet -> Gold -> Ruby)
- Kinetic Laser Scanner Beam with Motion Blur
- Audio Spectrum Visualizer HUD & Telemetry Status
- 60 FPS TrueColor Buffer Streaming
"""
import os
import sys
import time
import math
import random

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

GLYPHS = "0123456789ABCDEF!@#$%^&*()_+-=[]{}|;:,.<>?/░▒▓█▀▄▌▐~`§∆λ⚡✦"

DEFAULT_CROWN_LOGO = ' ██████╗██████╗  ██████╗ ██╗    ██╗███╗   ██╗\n██╔════╝██╔══██╗██╔═══██╗██║    ██║████╗  ██║\n██║     ██████╔╝██║   ██║██║ █╗ ██║██╔██╗ ██║\n██║     ██╔══██╗██║   ██║██║███╗██║██║╚██╗██║\n╚██████╗██║  ██║╚██████╔╝╚███╔███╔╝██║ ╚████║\n ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═══╝\n                                             \n'

def _term_size():
    try:
        cols, rows = os.get_terminal_size()
        return max(50, cols), max(18, rows)
    except Exception:
        return 80, 24

def _rgb(r, g, b, text):
    return f"\033[38;2;{int(r)};{int(g)};{int(b)}m{text}\033[0m"

def play_boot_animation(title="CROWN VIP", subtitle="CYBER TELEMETRY & OSINT CORE", ascii_art=None, duration=1.05):
    """Play the cinematic cyberpunk boot animation in 60 FPS."""
    # Check if animations are disabled
    if os.environ.get("CROWN_NO_ANIM") == "1":
        os.system("cls" if os.name == "nt" else "clear")
        return

    art = (ascii_art or DEFAULT_CROWN_LOGO).strip("\n").split("\n")
    max_w = max(len(line) for line in art)
    cols, rows = _term_size()
    indent = max(1, (cols - max_w) // 2)

    # Hide cursor and clear
    sys.stdout.write("\033[?25l\033[2J")
    
    start_t = time.time()
    wave_bars = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"]
    
    clean_sub = subtitle.replace(" ", "")
    spaced_sub = "  ".join(clean_sub.upper()) if len(clean_sub) <= 24 else subtitle.upper()
    sub_indent = max(1, (cols - len(spaced_sub)) // 2)

    try:
        while True:
            now = time.time()
            elapsed = now - start_t
            if elapsed >= duration:
                break

            progress = min(1.0, elapsed / duration)
            
            # Soundwave
            sw_idx = int(elapsed * 30)
            sw_left = "".join(wave_bars[(sw_idx + i) % len(wave_bars)] for i in range(6))
            sw_right = "".join(wave_bars[(sw_idx - i) % len(wave_bars)] for i in range(6))
            
            # Top Cyber HUD
            pct = int(progress * 100)
            hud = (
                f"\033[H\n"
                f"  {_rgb(110, 110, 150, '▲ CROWN-VIP')} "
                f"{_rgb(255, 30, 80, '//')} "
                f"{_rgb(240, 240, 255, title.upper())} "
                f"{_rgb(90, 90, 110, '·')} "
                f"{_rgb(255, 60, 120, sw_left)} "
                f"{_rgb(255, 215, 0, f'[{pct:02d}%]')} "
                f"{_rgb(255, 60, 120, sw_right)} "
                f"{_rgb(110, 110, 150, '// SEC-NODE 0x9F')}\n\n"
            )
            
            buf = [hud]
            reveal_thresh = progress / 0.52 if progress < 0.52 else 1.0

            # Render ASCII Art with Glitch & Chromatic Waves
            for r_idx, line in enumerate(art):
                buf.append(" " * indent)
                for c_idx, ch in enumerate(line):
                    if ch == " ":
                        buf.append(" ")
                        continue

                    char_prog = c_idx / max_w
                    if char_prog > reveal_thresh:
                        # Pre-reveal: Matrix glitch characters
                        if random.random() < 0.65:
                            g_ch = random.choice(GLYPHS)
                            buf.append(f"\033[38;2;{random.randint(70, 140)};0;{random.randint(50, 110)}m{g_ch}\033[0m")
                        else:
                            buf.append(" ")
                    else:
                        # Revealed: Chromatic plasma wave
                        age = reveal_thresh - char_prog
                        if age < 0.10 and progress < 0.58:
                            # White hot impact spark
                            buf.append(f"\033[38;2;255;255;255m{ch}\033[0m")
                        else:
                            wave = math.sin(elapsed * 14 - (c_idx * 0.14 + r_idx * 0.22))
                            cr = int(195 + 60 * wave)
                            cg = int(25 + 45 * math.sin(elapsed * 9 + c_idx * 0.08))
                            cb = int(70 + 75 * math.cos(elapsed * 11 - r_idx * 0.28))
                            buf.append(f"\033[38;2;{cr};{cg};{cb}m{ch}\033[0m")
                buf.append("\n")

            # Kinetic Laser Underline Beam
            laser_pos = int(((math.sin(elapsed * 11) + 1) / 2) * max_w)
            laser_bar = []
            for i in range(max_w):
                d = abs(i - laser_pos)
                if d == 0:
                    laser_bar.append(_rgb(255, 255, 255, "█"))
                elif d == 1:
                    laser_bar.append(_rgb(255, 60, 110, "━"))
                elif d < 4:
                    laser_bar.append(_rgb(190, 30, 80, "─"))
                else:
                    laser_bar.append(_rgb(65, 20, 45, "─"))
            buf.append(" " * indent + "".join(laser_bar) + "\n\n")

            # Subtitle with breathing neon glow
            sub_glow = int(150 + 105 * math.sin(elapsed * 15))
            buf.append(" " * sub_indent + f"\033[38;2;{sub_glow};{int(sub_glow*0.18)};{int(sub_glow*0.38)}m{spaced_sub}\033[0m\n")

            # Cyber telemetry lock
            stat_msg = "[ SYSTEM ARMED ] // PROTOCOL: ENCRYPTED // NODE ONLINE"
            s_indent = max(1, (cols - len(stat_msg)) // 2)
            buf.append("\n" + " " * s_indent + _rgb(130, 130, 160, stat_msg) + "\n")

            # Stream buffer
            sys.stdout.write("".join(buf))
            sys.stdout.flush()
            time.sleep(0.016)

    finally:
        sys.stdout.write("\033[?25h\033[0m\033[2J\033[H")
        sys.stdout.flush()
