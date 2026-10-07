"""French / English presentation strings. User content is never translated."""
EN = {'PROFIL  ↗': 'PROFILE  ↗', 'IP LOCALISATION': 'IP LOCATION', 'IP OPÉRATEUR': 'IP PROVIDER', 'ACCUEIL': 'HOME', 'IP & RÉSEAU': 'NETWORK', 'DOMAINES': 'DOMAINS', 'UTILITAIRES': 'UTILITIES', 'ESPACE PERSONNEL': 'PERSONAL WORKSPACE', 'PROFIL LOCAL': 'LOCAL PROFILE', 'MODIFIER  ↗': 'EDIT PROFILE  ↗', '⌕  RECHERCHER': '⌕  SEARCH', '◐  APPARENCE': '◐  APPEARANCE', 'PROFIL / LANGUE / COULEUR': 'PROFILE / LANGUAGE / COLOR', 'Molette pour explorer · Entrée pour ouvrir': 'Scroll to explore · Enter to open', '↕  MOLETTE / DÉFILEMENT CONTINU': '↕  SCROLL TO EXPLORE', 'OUVRIR LE MODULE  ↗': 'OPEN MODULE  ↗', 'MODULE D’ORIGINE': 'ORIGINAL MODULE', 'ATELIER / APPARENCE': 'STUDIO / APPEARANCE', 'Une identité. Quatre atmosphères.': 'Your identity. Four atmospheres.', 'ANIMATIONS  /  ACTIVES': 'ANIMATIONS  /  ON', 'ANIMATIONS  /  PAUSE': 'ANIMATIONS  /  PAUSED', 'REJOUER L’INTRODUCTION': 'REPLAY INTRODUCTION', 'RETOUR  /  ÉCHAP': 'BACK  /  ESC', 'ENTRÉE  /  PASSER L’INTRODUCTION': 'ENTER  /  SKIP INTRODUCTION', 'ACCÈS RAPIDE  /  CTRL K': 'QUICK ACCESS  /  CTRL K', 'Un outil, une idée…': 'Find a tool…', '↑ ↓  NAVIGUER     ENTRÉE  OUVRIR     ÉCHAP  FERMER': '↑ ↓  NAVIGATE     ENTER  OPEN     ESC  CLOSE', '← RETOUR': '← BACK', 'EXÉCUTER  ↗': 'RUN  ↗', ' SORTIE / RÉSULTATS ': ' OUTPUT / RESULTS ', '◇\n\nPRÊT POUR VOTRE PROCHAINE EXPLORATION\n\nRenseignez une entrée puis appuyez sur Entrée.': '◇\n\nREADY WHEN YOU ARE\n\nType an input and press Enter.', '  ÉCHAP  Retour au tableau de bord    /    ENTRÉE  Exécuter': '  ESC  Back to dashboard    /    ENTER  Run', 'recherche': 'search', 'apparence': 'appearance', 'mouvement': 'motion', 'quitter': 'quit', 'Sauvegarde impossible.': 'Unable to save preferences.', 'DNS, HTTP et réseau': 'DNS, HTTP & network', 'Coordonnées & région': 'Coordinates & region', 'FAI & infrastructure': 'ISP & infrastructure', 'Services TCP accessibles': 'Accessible TCP services', 'Connectivité & latence': 'Connectivity & latency', 'Adresses IPv4 aléatoires': 'Random IPv4 addresses', 'Identité du domaine': 'Domain identity', 'Cartographie des enregistrements': 'DNS record mapping', 'Explorer les sous-domaines': 'Explore subdomains', 'Certificats & expiration': 'Certificates & expiry', 'Empreintes & intégrité': 'Digests & integrity', 'Aléatoire cryptographique': 'Cryptographic randomness', 'Texte vers code matriciel': 'Text to QR code', 'Encodage & décodage': 'Encoding & decoding', 'Résolution DNS, statut HTTP, géolocalisation et scan de ports en un seul rapport.': 'DNS resolution, HTTP status, geolocation and port scan in one report.', "Pays, ville, coordonnées GPS et fuseau horaire d'une adresse IP.": 'Country, city, GPS coordinates and time zone of an IP address.', 'FAI, organisation, numéro AS, détection proxy / VPN / hébergeur.': 'ISP, organization, AS number, proxy / VPN / hosting detection.', 'Scan des ports communs (FTP, SSH, HTTP, RDP, bases de données...).': 'Scan common ports (FTP, SSH, HTTP, RDP, databases…).', 'Ping ICMP vers une IP ou un domaine, 4 paquets.': 'ICMP ping to an IP or domain, 4 packets.', 'Génère des adresses IPv4 publiques aléatoires.': 'Generate random public IPv4 addresses.', "Calcule MD5, SHA-1, SHA-256 et SHA-512 d'un texte.": 'Compute MD5, SHA-1, SHA-256 and SHA-512 digests of text.', 'Génère un mot de passe aléatoire sécurisé de la longueur voulue.': 'Generate a secure random password of the requested length.', "Génère un QR code à partir d'un texte ou d'une URL, affiché en ASCII.": 'Generate a terminal QR code from text or a URL.', 'Encode un texte en URL, HTML, ROT13 et hexadécimal.': 'Encode text as URL, HTML, ROT13 and hexadecimal.', "Encode un texte en Base64, ou le décode si c'est déjà du Base64.": 'Encode text as Base64, or decode existing Base64.', "Registrar, dates de création/expiration, serveurs DNS d'un nom de domaine.": 'Domain registrar, registration / expiry dates and DNS servers.', "Enregistrements A, AAAA, MX, NS, TXT et CNAME d'un domaine.": 'A, AAAA, MX, NS, TXT and CNAME records of a domain.', 'Recherche de sous-domaines courants (www, mail, api, dev...) par résolution DNS.': 'Find common subdomains (www, mail, api, dev…) using DNS.', "Émetteur, validité et noms alternatifs du certificat TLS d'un domaine.": 'Issuer, validity and alternative names of a domain TLS certificate.'}
import json
import re
from pathlib import Path
from functools import lru_cache
LANGUAGES = {'fr': 'Français', 'en': 'English', 'es': 'Español', 'de': 'Deutsch', 'zh': '中文', 'ar': 'العربية'}
LOCALES = {lang: json.loads((Path(__file__).resolve().parents[1] / 'locales' / (lang + '.json')).read_text(encoding='utf-8')) for lang in ('es', 'de', 'zh', 'ar')}
EN.update({'Choisis ton atmosphère.': 'Choose your atmosphere.', 'BIENVENUE': 'WELCOME', 'Ton espace. Ton style.': 'Your space. Your style.', 'Enregistré sur ce compte Windows.': 'Saved on this Windows account.', 'Pseudo': 'Username', 'Langue': 'Language', 'Palette de couleurs': 'Color palette', 'Couleur personnalisée #RRGGBB (facultatif)': 'Custom color #RRGGBB (optional)', 'ENREGISTRER ET CONTINUER  →': 'SAVE & CONTINUE  →', 'Annuler': 'Cancel', 'Entre un pseudo de 1 à 24 caractères.': 'Enter a username (1–24 characters).', 'Format attendu : #RRGGBB.': 'Expected format: #RRGGBB.', 'Sauvegarde impossible. Réessaie.': 'Unable to save. Please try again.', 'ENTRÉE  /  CONTINUER': 'ENTER  /  CONTINUE', 'PRÊT POUR VOTRE PROCHAINE EXPLORATION': 'READY WHEN YOU ARE', 'Renseignez une entrée puis appuyez sur Entrée.': 'Type an input and press Enter.', 'SORTIE / RÉSULTATS': 'OUTPUT / RESULTS'})

@lru_cache(maxsize=1024)
def display_arabic(text):
    if not re.search('[\u0600-ۿ]', text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return text
    return '\n'.join((get_display(arabic_reshaper.reshape(line)) for line in text.split('\n')))

def translate(text, language):
    if language == 'fr':
        return text
    target = EN.get(text, text)
    if language == 'en':
        if target != text:
            return target
    else:
        catalog = LOCALES.get(language, {})
        if target not in catalog:
            target = DETAIL_KEYS.get(target, target)
        if target in catalog:
            output = catalog[target]
            return display_arabic(output) if language == 'ar' else output
    if '\n' in text:
        return '\n'.join((translate(line, language) for line in text.split('\n')))
    stripped = text.strip()
    if stripped != text and stripped:
        return text[:len(text) - len(text.lstrip())] + translate(stripped, language) + text[len(text.rstrip()):]
    match = re.match('^(\\d+\\s*(?:/\\s*|  ))(.+)$', text)
    if match:
        return match.group(1) + translate(match.group(2), language)
    for suffix in (' MODULES', ' / COLLECTION'):
        if text.endswith(suffix):
            return text[:-len(suffix)] + suffix.replace(suffix.strip(' /'), translate(suffix.strip(' /'), language))
    if text.startswith('C R O W N  /  '):
        return 'C R O W N  /  ' + translate(text[12:], language)
    return target
DETAIL_KEYS = {'DNS resolution, HTTP status, geolocation and port scan in one report.': 'DNS, HTTP & network', 'Country, city, GPS coordinates and time zone of an IP address.': 'Coordinates & region', 'ISP, organization, AS number, proxy / VPN / hosting detection.': 'ISP & infrastructure', 'Scan common ports (FTP, SSH, HTTP, RDP, databases…).': 'Accessible TCP services', 'ICMP ping to an IP or domain, 4 packets.': 'Connectivity & latency', 'Generate random public IPv4 addresses.': 'Random IPv4 addresses', 'Compute MD5, SHA-1, SHA-256 and SHA-512 digests of text.': 'Digests & integrity', 'Generate a secure random password of the requested length.': 'Cryptographic randomness', 'Generate a terminal QR code from text or a URL.': 'Text to QR code', 'Encode text as URL, HTML, ROT13 and hexadecimal.': 'Encoding & decoding', 'Encode text as Base64, or decode existing Base64.': 'Encoding & decoding', 'Domain registrar, registration / expiry dates and DNS servers.': 'Domain identity', 'A, AAAA, MX, NS, TXT and CNAME records of a domain.': 'DNS record mapping', 'Find common subdomains (www, mail, api, dev…) using DNS.': 'Explore subdomains', 'Issuer, validity and alternative names of a domain TLS certificate.': 'Certificates & expiry'}
EN.update({'PARTIE SOMBRE': 'DARK SIDE', 'Vous êtes sur le point d’entrer dans la partie sombre. Êtes-vous sûr ?': 'You are about to enter the dark side. Are you sure?', 'Non, revenir': 'No, go back', 'Oui, entrer': 'Yes, enter', 'En construction': 'Under construction'})
EN.update({'Entrez le code d’accès.': 'Enter the access code.', 'Code d’accès': 'Access code', 'Déverrouiller': 'Unlock', 'Code incorrect. Réessayez.': 'Incorrect code. Try again.'})
EN.update({'Pas de clé ? Rejoins le Discord ou le Telegram pour l’obtenir.': 'No key? Join Discord or Telegram to get one.'})
EN.update({'ZONE VIP': 'VIP ZONE', 'Vous êtes sur le point d’entrer dans la zone VIP. Souhaitez-vous continuer ?': 'You are about to enter the VIP zone. Would you like to continue?'})
EN.update({'← MODE STANDARD': '← STANDARD MODE', 'MODE STANDARD': 'STANDARD MODE', 'ACCUEIL VIP': 'VIP HOME', 'COLLECTION VIP': 'VIP COLLECTION', 'HOME': 'HOME', 'HOME VIP': 'HOME VIP', 'BOUTIQUE PREMIUM': 'PREMIUM SHOP', 'PROFIL & THÈME': 'PROFILE & THEME', 'CHANGELOG': 'CHANGELOG', 'CHANGELOG VIP': 'VIP CHANGELOG', 'CRÉDITS & SYSTÈME': 'CREDITS & SYSTEM', 'TOUS LES MODULES': 'ALL MODULES', 'TOUS LES MODULES VIP': 'ALL VIP MODULES', 'COLLECTION COMPLÈTE': 'FULL COLLECTION', 'CROWN-TOOLS · HOME HUB  (discord.gg/kaostools · t.me/v0idtool)': 'CROWN-TOOLS · HOME HUB  (discord.gg/kaostools · t.me/v0idtool)', 'OPTIONS': 'OPTIONS'})
EN.update({'CHOISIR UN DOSSIER': 'CHOOSE A FOLDER', 'ÉCHAP Retour · F5 Exécuter · ENTRÉE Nouvelle ligne': 'ESC Back · F5 Run · ENTER New line'})
EN['ENREGISTRER'] = 'SAVE'
