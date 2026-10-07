import webbrowser

from .config import read_settings, write_profile
from .update_check import DISCORD_URL, TELEGRAM_URL


def open_welcome_links_once(profile_path):
    settings = read_settings(profile_path)
    if settings.get('welcome_links_attempted') is True:
        return
    try:
        write_profile(profile_path, {'welcome_links_attempted': True})
    except OSError:
        return
    for url in (DISCORD_URL, TELEGRAM_URL):
        try:
            webbrowser.open(url, new=2)
        except (OSError, webbrowser.Error):
            continue
