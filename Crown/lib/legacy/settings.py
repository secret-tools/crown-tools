"""
settings.py — Configuration, thèmes et traductions de Crown-Tools.

Contient : la persistance de config (JSON local), les 4 palettes de couleur,
et le système de traduction (FR/EN/ES/DE). Séparé de main.py pour ne pas noyer
l'app dans des dictionnaires de traduction — main.py importe juste `t()`,
`load_config`, `save_config`, `THEMES`, `LANGUAGES`, `THEME_NAMES`.
"""

import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crown_config.json")

DEFAULT_CONFIG = {
    "configured": False,
    "language": "fr",
    "theme": "void_red",
    "pseudo": "Opérateur",
    "sound": True,
    "boot_speed": "normal",   # "normal" | "fast" | "off"
    "show_sidebar_dashboard": True,
    "confirm_quit": False,
}


def load_config() -> dict:
    """Charge la config locale, robuste à un fichier absent/corrompu/incomplet —
    ne fait jamais planter l'app, retombe sur les valeurs par défaut."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
#  THÈMES DE COULEUR
# ============================================================

THEMES = {
    "void_red": {
        "crown-bg": "#0d1119", "crown-bg-alt": "#141a26", "crown-border": "#1e293b",
        "crown-accent": "#f87171", "crown-accent-2": "#7f1d1d", "crown-cyan": "#22d3ee",
        "crown-text": "#e2e8f0", "crown-text-dim": "#64748b",
        "crown-success": "#4ade80", "crown-warning": "#facc15", "crown-error": "#f87171",
    },
    "matrix_green": {
        "crown-bg": "#050f05", "crown-bg-alt": "#0d1a0d", "crown-border": "#1a3a1a",
        "crown-accent": "#4ade80", "crown-accent-2": "#14532d", "crown-cyan": "#86efac",
        "crown-text": "#d1fae5", "crown-text-dim": "#4b6b4b",
        "crown-success": "#4ade80", "crown-warning": "#facc15", "crown-error": "#f87171",
    },
    "cyber_purple": {
        "crown-bg": "#0f0a1a", "crown-bg-alt": "#170f28", "crown-border": "#2e1f4d",
        "crown-accent": "#a78bfa", "crown-accent-2": "#4c1d95", "crown-cyan": "#22d3ee",
        "crown-text": "#ede9fe", "crown-text-dim": "#6b5b95",
        "crown-success": "#4ade80", "crown-warning": "#facc15", "crown-error": "#f87171",
    },
    "amber_terminal": {
        "crown-bg": "#140f05", "crown-bg-alt": "#201808", "crown-border": "#3d2e10",
        "crown-accent": "#fbbf24", "crown-accent-2": "#78350f", "crown-cyan": "#22d3ee",
        "crown-text": "#fef3c7", "crown-text-dim": "#8a6d3b",
        "crown-success": "#4ade80", "crown-warning": "#facc15", "crown-error": "#f87171",
    },
}

THEME_NAMES = {
    "void_red": "Void Red",
    "matrix_green": "Matrix Green",
    "cyber_purple": "Cyber Purple",
    "amber_terminal": "Amber Terminal",
}

LANGUAGES = ["fr", "en", "es", "de"]
LANGUAGE_NAMES = {"fr": "Français", "en": "English", "es": "Español", "de": "Deutsch"}


# ============================================================
#  TRADUCTIONS
# ============================================================

TRANSLATIONS = {
    "app_subtitle": {
        "fr": "TUI Dashboard — mode void", "en": "TUI Dashboard — void mode",
        "es": "Panel TUI — modo void", "de": "TUI-Dashboard — Void-Modus",
    },
    "categories_title": {"fr": "CATÉGORIES", "en": "CATEGORIES", "es": "CATEGORÍAS", "de": "KATEGORIEN"},
    "select_category": {
        "fr": "SÉLECTIONNE UNE CATÉGORIE", "en": "SELECT A CATEGORY",
        "es": "SELECCIONA UNA CATEGORÍA", "de": "KATEGORIE AUSWÄHLEN",
    },
    "system_load": {"fr": "SYSTEM LOAD", "en": "SYSTEM LOAD", "es": "CARGA DEL SISTEMA", "de": "SYSTEMLAST"},
    "results_title": {"fr": "RÉSULTATS", "en": "RESULTS", "es": "RESULTADOS", "de": "ERGEBNISSE"},
    "search_hint": {
        "fr": "Ctrl+K pour chercher un outil dans toutes les catégories.",
        "en": "Ctrl+K to search a tool across all categories.",
        "es": "Ctrl+K para buscar una herramienta en todas las categorías.",
        "de": "Strg+K, um ein Tool in allen Kategorien zu suchen.",
    },
    # ---- status bar ----
    "quit": {"fr": "Quitter", "en": "Quit", "es": "Salir", "de": "Beenden"},
    "back": {"fr": "Retour", "en": "Back", "es": "Volver", "de": "Zurück"},
    "navigate": {"fr": "Naviguer", "en": "Navigate", "es": "Navegar", "de": "Navigieren"},
    "search": {"fr": "Recherche", "en": "Search", "es": "Buscar", "de": "Suche"},
    "demo": {"fr": "Démo", "en": "Demo", "es": "Demo", "de": "Demo"},
    # ---- boutons / champs communs ----
    "back_button": {"fr": "← Retour", "en": "← Back", "es": "← Volver", "de": "← Zurück"},
    "run_button": {"fr": "Exécuter", "en": "Run", "es": "Ejecutar", "de": "Ausführen"},
    "loading": {"fr": "Analyse en cours", "en": "Analyzing", "es": "Analizando", "de": "Analysiere"},
    "analysis_done": {
        "fr": "Analyse terminée ✓", "en": "Analysis complete ✓",
        "es": "Análisis completo ✓", "de": "Analyse abgeschlossen ✓",
    },
    "analysis_error": {
        "fr": "Erreur pendant l'analyse", "en": "Error during analysis",
        "es": "Error durante el análisis", "de": "Fehler bei der Analyse",
    },
    "not_implemented": {
        "fr": "Non implémenté.", "en": "Not implemented.",
        "es": "No implementado.", "de": "Nicht implementiert.",
    },
    # ---- messages d'erreur génériques réutilisés par les outils ----
    "enter_domain_or_ip": {
        "fr": "Entre un domaine ou une IP.", "en": "Enter a domain or an IP.",
        "es": "Introduce un dominio o una IP.", "de": "Gib eine Domain oder eine IP ein.",
    },
    "enter_ip": {
        "fr": "Entre une adresse IP.", "en": "Enter an IP address.",
        "es": "Introduce una dirección IP.", "de": "Gib eine IP-Adresse ein.",
    },
    "enter_valid_number": {
        "fr": "Entre un nombre valide.", "en": "Enter a valid number.",
        "es": "Introduce un número válido.", "de": "Gib eine gültige Zahl ein.",
    },
    "network_error": {"fr": "Erreur réseau", "en": "Network error", "es": "Error de red", "de": "Netzwerkfehler"},
    "cannot_resolve": {
        "fr": "Impossible de résoudre", "en": "Unable to resolve",
        "es": "No se puede resolver", "de": "Konnte nicht auflösen",
    },
    "timeout_no_response": {
        "fr": "Timeout — aucune réponse.", "en": "Timeout — no response.",
        "es": "Tiempo agotado — sin respuesta.", "de": "Zeitüberschreitung — keine Antwort.",
    },
    "error_label": {"fr": "Erreur", "en": "Error", "es": "Error", "de": "Fehler"},
    "unknown": {"fr": "inconnue", "en": "unknown", "es": "desconocido", "de": "unbekannt"},
    # ---- Web Lookup / résultats réseau ----
    "target": {"fr": "Cible", "en": "Target", "es": "Objetivo", "de": "Ziel"},
    "dns_resolution": {
        "fr": "Résolution DNS", "en": "DNS resolution", "es": "Resolución DNS", "de": "DNS-Auflösung",
    },
    "dns_failed": {
        "fr": "échec (traitement direct de la valeur)", "en": "failed (using raw value)",
        "es": "fallo (usando el valor directo)", "de": "fehlgeschlagen (Rohwert verwendet)",
    },
    "http_status": {"fr": "Statut HTTP", "en": "HTTP status", "es": "Estado HTTP", "de": "HTTP-Status"},
    "no_http_response": {
        "fr": "pas de réponse (HTTPS uniquement ?)", "en": "no response (HTTPS only?)",
        "es": "sin respuesta (¿solo HTTPS?)", "de": "keine Antwort (nur HTTPS?)",
    },
    "geolocation": {"fr": "Géolocalisation", "en": "Geolocation", "es": "Geolocalización", "de": "Geolokalisierung"},
    "geolocation_unavailable": {
        "fr": "Géolocalisation indisponible.", "en": "Geolocation unavailable.",
        "es": "Geolocalización no disponible.", "de": "Geolokalisierung nicht verfügbar.",
    },
    "country": {"fr": "Pays", "en": "Country", "es": "País", "de": "Land"},
    "city": {"fr": "Ville", "en": "City", "es": "Ciudad", "de": "Stadt"},
    "region": {"fr": "Région", "en": "Region", "es": "Región", "de": "Region"},
    "postal_code": {"fr": "Code postal", "en": "Postal code", "es": "Código postal", "de": "Postleitzahl"},
    "coordinates": {"fr": "Coordonnées", "en": "Coordinates", "es": "Coordenadas", "de": "Koordinaten"},
    "timezone": {"fr": "Fuseau horaire", "en": "Timezone", "es": "Zona horaria", "de": "Zeitzone"},
    "isp": {"fr": "ISP", "en": "ISP", "es": "ISP", "de": "ISP"},
    "org": {"fr": "Org", "en": "Org", "es": "Org", "de": "Org"},
    "as_number": {"fr": "AS", "en": "AS", "es": "AS", "de": "AS"},
    "common_ports": {"fr": "Ports communs", "en": "Common ports", "es": "Puertos comunes", "de": "Häufige Ports"},
    "cannot_locate": {
        "fr": "Impossible de localiser", "en": "Unable to locate",
        "es": "No se puede localizar", "de": "Konnte nicht lokalisieren",
    },
    "ip_label": {"fr": "IP", "en": "IP", "es": "IP", "de": "IP"},
    "isp_full": {"fr": "FAI", "en": "ISP", "es": "ISP", "de": "ISP"},
    "organization": {"fr": "Organisation", "en": "Organization", "es": "Organización", "de": "Organisation"},
    "mobile": {"fr": "Mobile", "en": "Mobile", "es": "Móvil", "de": "Mobil"},
    "proxy_vpn": {"fr": "Proxy/VPN", "en": "Proxy/VPN", "es": "Proxy/VPN", "de": "Proxy/VPN"},
    "hosting": {"fr": "Hosting", "en": "Hosting", "es": "Hosting", "de": "Hosting"},
    "yes_flag": {"fr": "oui", "en": "yes", "es": "sí", "de": "ja"},
    "no_flag": {"fr": "non", "en": "no", "es": "no", "de": "nein"},
    "port": {"fr": "Port", "en": "Port", "es": "Puerto", "de": "Port"},
    "service": {"fr": "Service", "en": "Service", "es": "Servicio", "de": "Dienst"},
    "state": {"fr": "État", "en": "State", "es": "Estado", "de": "Status"},
    "open_state": {"fr": "ouvert", "en": "open", "es": "abierto", "de": "offen"},
    "no_open_ports": {
        "fr": "Aucun port commun ouvert détecté.", "en": "No common open ports detected.",
        "es": "No se detectaron puertos comunes abiertos.", "de": "Keine offenen Standardports erkannt.",
    },
    "ports_open_of": {
        "fr": "ports ouverts", "en": "ports open", "es": "puertos abiertos", "de": "offene Ports",
    },
    "generated_ips": {
        "fr": "IP(s) générées", "en": "IP(s) generated", "es": "IP(s) generadas", "de": "generierte IP(s)",
    },
    # ---- placeholders des 6 outils ----
    "ph_web_lookup": {
        "fr": "ex: google.com ou 8.8.8.8", "en": "e.g. google.com or 8.8.8.8",
        "es": "ej: google.com u 8.8.8.8", "de": "z.B. google.com oder 8.8.8.8",
    },
    "ph_ip": {"fr": "ex: 8.8.8.8", "en": "e.g. 8.8.8.8", "es": "ej: 8.8.8.8", "de": "z.B. 8.8.8.8"},
    "ph_ip_or_domain": {
        "fr": "ex: 8.8.8.8 ou google.com", "en": "e.g. 8.8.8.8 or google.com",
        "es": "ej: 8.8.8.8 o google.com", "de": "z.B. 8.8.8.8 oder google.com",
    },
    "ph_count": {
        "fr": "Nombre d'IPs à générer (ex: 5)", "en": "Number of IPs to generate (e.g. 5)",
        "es": "Número de IPs a generar (ej: 5)", "de": "Anzahl zu generierender IPs (z.B. 5)",
    },
    # ---- boîte à outils ----
    "enter_text": {
        "fr": "Entre du texte.", "en": "Enter some text.",
        "es": "Introduce un texto.", "de": "Gib einen Text ein.",
    },
    "ph_hash_input": {
        "fr": "Texte à hacher", "en": "Text to hash",
        "es": "Texto a hashear", "de": "Zu hashender Text",
    },
    "ph_password_length": {
        "fr": "Longueur du mot de passe (ex: 16)", "en": "Password length (e.g. 16)",
        "es": "Longitud de la contraseña (ej: 16)", "de": "Passwortlänge (z.B. 16)",
    },
    "password_label": {"fr": "Mot de passe", "en": "Password", "es": "Contraseña", "de": "Passwort"},
    "length_label": {"fr": "Longueur", "en": "Length", "es": "Longitud", "de": "Länge"},
    "ph_qr_text": {
        "fr": "Texte ou URL à encoder", "en": "Text or URL to encode",
        "es": "Texto o URL a codificar", "de": "Text oder URL zum Codieren",
    },
    "enter_qr_text": {
        "fr": "Entre un texte ou une URL.", "en": "Enter a text or a URL.",
        "es": "Introduce un texto o una URL.", "de": "Gib einen Text oder eine URL ein.",
    },
    "qr_content_label": {"fr": "Contenu", "en": "Content", "es": "Contenido", "de": "Inhalt"},
    "ph_text_encode": {
        "fr": "Texte à encoder", "en": "Text to encode",
        "es": "Texto a codificar", "de": "Zu codierender Text",
    },
    "ph_base64_input": {
        "fr": "Texte à encoder/décoder en Base64", "en": "Text to encode/decode as Base64",
        "es": "Texto a codificar/decodificar en Base64", "de": "Text zum Base64-Codieren/Decodieren",
    },
    "not_valid_base64": {
        "fr": "pas du Base64 valide", "en": "not valid Base64",
        "es": "no es Base64 válido", "de": "kein gültiges Base64",
    },
    "encoded_label": {"fr": "Encodé", "en": "Encoded", "es": "Codificado", "de": "Codiert"},
    "decoded_label": {"fr": "Décodé", "en": "Decoded", "es": "Decodificado", "de": "Decodiert"},
    # ---- domaines & infrastructure ----
    "ph_domain": {
        "fr": "ex: google.com", "en": "e.g. google.com",
        "es": "ej: google.com", "de": "z.B. google.com",
    },
    "enter_domain": {
        "fr": "Entre un nom de domaine.", "en": "Enter a domain name.",
        "es": "Introduce un nombre de dominio.", "de": "Gib einen Domainnamen ein.",
    },
    "no_whois_data": {
        "fr": "Aucune donnée WHOIS trouvée.", "en": "No WHOIS data found.",
        "es": "No se encontraron datos WHOIS.", "de": "Keine WHOIS-Daten gefunden.",
    },
    "no_dns_records": {
        "fr": "Aucun enregistrement DNS trouvé pour", "en": "No DNS records found for",
        "es": "No se encontraron registros DNS para", "de": "Keine DNS-Einträge gefunden für",
    },
    "dns_error": {"fr": "erreur de résolution", "en": "resolution error", "es": "error de resolución", "de": "Auflösungsfehler"},
    "no_subdomains_found": {
        "fr": "Aucun sous-domaine courant trouvé pour", "en": "No common subdomain found for",
        "es": "No se encontró ningún subdominio común para", "de": "Kein gängiges Subdomain gefunden für",
    },
    "subdomains_found": {
        "fr": "sous-domaine(s) trouvé(s)", "en": "subdomain(s) found",
        "es": "subdominio(s) encontrado(s)", "de": "Subdomain(s) gefunden",
    },
    "subdomain_label": {"fr": "Sous-domaine", "en": "Subdomain", "es": "Subdominio", "de": "Subdomain"},
    "subject_label": {"fr": "Sujet", "en": "Subject", "es": "Sujeto", "de": "Betreff"},
    "issuer_label": {"fr": "Émetteur", "en": "Issuer", "es": "Emisor", "de": "Aussteller"},
    "valid_from_label": {"fr": "Valide depuis", "en": "Valid from", "es": "Válido desde", "de": "Gültig ab"},
    "valid_until_label": {"fr": "Valide jusqu'au", "en": "Valid until", "es": "Válido hasta", "de": "Gültig bis"},
    "sans_label": {
        "fr": "Noms alternatifs", "en": "Alternative names",
        "es": "Nombres alternativos", "de": "Alternative Namen",
    },
    # ---- Coming soon / dev panel ----
    "module_construction": {
        "fr": "MODULE EN CONSTRUCTION", "en": "MODULE UNDER CONSTRUCTION",
        "es": "MÓDULO EN CONSTRUCCIÓN", "de": "MODUL IM AUFBAU",
    },
    "in_development": {
        "fr": "En développement", "en": "In development", "es": "En desarrollo", "de": "In Entwicklung",
    },
    # ---- palette de commandes ----
    "palette_placeholder": {
        "fr": "Rechercher un outil (nom ou catégorie)...", "en": "Search a tool (name or category)...",
        "es": "Buscar una herramienta (nombre o categoría)...", "de": "Tool suchen (Name oder Kategorie)...",
    },
    "close": {"fr": "Fermer", "en": "Close", "es": "Cerrar", "de": "Schließen"},
    # ---- session stats ----
    "scans": {"fr": "scans", "en": "scans", "es": "análisis", "de": "Scans"},
    # ---- assistant de configuration ----
    "wizard_title": {
        "fr": "CONFIGURATION INITIALE", "en": "INITIAL SETUP",
        "es": "CONFIGURACIÓN INICIAL", "de": "ERSTEINRICHTUNG",
    },
    "wizard_title_edit": {
        "fr": "PARAMÈTRES", "en": "SETTINGS",
        "es": "AJUSTES", "de": "EINSTELLUNGEN",
    },
    "wizard_language": {"fr": "Langue", "en": "Language", "es": "Idioma", "de": "Sprache"},
    "wizard_theme": {"fr": "Thème de couleur", "en": "Color theme", "es": "Tema de color", "de": "Farbschema"},
    "wizard_pseudo": {
        "fr": "Nom d'opérateur", "en": "Operator name", "es": "Nombre de operador", "de": "Bedienername",
    },
    "wizard_sound": {"fr": "Son (bips)", "en": "Sound (beeps)", "es": "Sonido (pitidos)", "de": "Ton (Signale)"},
    "wizard_boot_speed": {
        "fr": "Vitesse du boot", "en": "Boot speed", "es": "Velocidad de arranque", "de": "Boot-Geschwindigkeit",
    },
    "wizard_sidebar": {
        "fr": "Dashboard système dans la sidebar", "en": "System dashboard in sidebar",
        "es": "Panel del sistema en la barra lateral", "de": "System-Dashboard in der Seitenleiste",
    },
    "wizard_confirm_quit": {
        "fr": "Confirmer avant de quitter", "en": "Confirm before quitting",
        "es": "Confirmar antes de salir", "de": "Vor dem Beenden bestätigen",
    },
    "wizard_start": {"fr": "Commencer", "en": "Start", "es": "Comenzar", "de": "Starten"},
    "wizard_save": {"fr": "Enregistrer", "en": "Save", "es": "Guardar", "de": "Speichern"},
    "wizard_skip_boot": {
        "fr": "Passer l'animation de démarrage", "en": "Skip startup animation",
        "es": "Omitir animación de inicio", "de": "Startanimation überspringen",
    },
    "boot_speed_normal": {"fr": "Normal", "en": "Normal", "es": "Normal", "de": "Normal"},
    "boot_speed_fast": {"fr": "Rapide", "en": "Fast", "es": "Rápido", "de": "Schnell"},
    "boot_speed_off": {"fr": "Désactivé", "en": "Off", "es": "Desactivado", "de": "Aus"},
    "welcome_back": {
        "fr": "Bienvenue, {pseudo}", "en": "Welcome back, {pseudo}",
        "es": "Bienvenido de nuevo, {pseudo}", "de": "Willkommen zurück, {pseudo}",
    },
    "confirm_quit_message": {
        "fr": "Quitter Crown-Tools ?", "en": "Quit Crown-Tools?",
        "es": "¿Salir de Crown-Tools?", "de": "Crown-Tools beenden?",
    },
    "yes": {"fr": "Oui", "en": "Yes", "es": "Sí", "de": "Ja"},
    "no": {"fr": "Non", "en": "No", "es": "No", "de": "Nein"},
    # ---- noms de catégories ----
    "cat_ip_network": {
        "fr": "Réseau & Ports", "en": "Network & Ports", "es": "Red y Puertos", "de": "Netzwerk & Ports",
    },
    "cat_osint": {
        "fr": "OSINT & Recherche", "en": "OSINT & Research",
        "es": "OSINT e Investigación", "de": "OSINT & Recherche",
    },
    "cat_utilities": {"fr": "Boîte à outils", "en": "Toolbox", "es": "Caja de herramientas", "de": "Werkzeugkasten"},
    "cat_settings": {"fr": "Paramètres", "en": "Settings", "es": "Ajustes", "de": "Einstellungen"},
    "cat_domains": {
        "fr": "Domaines & Infrastructure", "en": "Domains & Infrastructure",
        "es": "Dominios e Infraestructura", "de": "Domains & Infrastruktur",
    },
    # ---- noms d'outils ----
    "tool_configuration": {"fr": "Configuration", "en": "Configuration", "es": "Configuración", "de": "Konfiguration"},
    "tool_whois_lookup": {"fr": "WHOIS Lookup", "en": "WHOIS Lookup", "es": "Consulta WHOIS", "de": "WHOIS-Abfrage"},
    "tool_dns_records": {
        "fr": "Enregistrements DNS", "en": "DNS Records", "es": "Registros DNS", "de": "DNS-Einträge",
    },
    "tool_subdomain_finder": {
        "fr": "Recherche de sous-domaines", "en": "Subdomain Finder",
        "es": "Buscador de subdominios", "de": "Subdomain-Suche",
    },
    "tool_ssl_cert_info": {
        "fr": "Certificat SSL", "en": "SSL Certificate Info",
        "es": "Información del certificado SSL", "de": "SSL-Zertifikatsinfo",
    },
    "tool_web_lookup": {"fr": "Web Lookup", "en": "Web Lookup", "es": "Búsqueda Web", "de": "Web-Abfrage"},
    "tool_ip_localisation": {
        "fr": "IP Localisation", "en": "IP Location", "es": "Localización IP", "de": "IP-Standort",
    },
    "tool_ip_operateur": {
        "fr": "IP Opérateur", "en": "IP Carrier", "es": "Operador IP", "de": "IP-Anbieter",
    },
    "tool_open_ports": {"fr": "Open Ports", "en": "Open Ports", "es": "Puertos Abiertos", "de": "Offene Ports"},
    "tool_ip_pinger": {"fr": "IP Pinger", "en": "IP Pinger", "es": "Ping IP", "de": "IP-Ping"},
    "tool_ip_generator": {
        "fr": "IP Generator", "en": "IP Generator", "es": "Generador IP", "de": "IP-Generator",
    },
    "tool_link_hub": {"fr": "Link Hub", "en": "Link Hub", "es": "Centro de Enlaces", "de": "Link-Hub"},
    "tool_osint_framework": {
        "fr": "OSINT Framework", "en": "OSINT Framework", "es": "Framework OSINT", "de": "OSINT-Framework",
    },
    "tool_name_finder": {
        "fr": "Name Finder", "en": "Name Finder", "es": "Buscador de Nombres", "de": "Namensfinder",
    },
    "tool_email_info": {"fr": "Email Info", "en": "Email Info", "es": "Info de Email", "de": "E-Mail-Info"},
    "tool_number_info": {
        "fr": "Number Info", "en": "Number Info", "es": "Info de Número", "de": "Nummer-Info",
    },
    "tool_profile_builder": {
        "fr": "Profile Builder", "en": "Profile Builder", "es": "Constructor de Perfil", "de": "Profil-Builder",
    },
    "tool_simple_report": {
        "fr": "Simple Report", "en": "Simple Report", "es": "Informe Simple", "de": "Einfacher Bericht",
    },
    "tool_search_db": {
        "fr": "Search DB", "en": "Search DB", "es": "Buscar BD", "de": "DB-Suche",
    },
    "tool_username_hunter": {
        "fr": "Username Hunter", "en": "Username Hunter", "es": "Cazador de Usuarios", "de": "Benutzername-Suche",
    },
    "tool_domain_intel": {
        "fr": "Domain Intel", "en": "Domain Intel", "es": "Inteligencia de Dominio", "de": "Domain-Info",
    },
    "tool_social_scraper": {
        "fr": "Social Scraper", "en": "Social Scraper", "es": "Extractor Social", "de": "Social Scraper",
    },
    "tool_vpn_detector": {
        "fr": "VPN Detector", "en": "VPN Detector", "es": "Detector de VPN", "de": "VPN-Erkennung",
    },
    "tool_hash_tools": {"fr": "Hash Tools", "en": "Hash Tools", "es": "Herramientas Hash", "de": "Hash-Tools"},
    "tool_password_generator": {
        "fr": "Password Generator", "en": "Password Generator",
        "es": "Generador de Contraseñas", "de": "Passwort-Generator",
    },
    "tool_qr_code": {"fr": "QR Code", "en": "QR Code", "es": "Código QR", "de": "QR-Code"},
    "tool_text_encoder": {
        "fr": "Text Encoder", "en": "Text Encoder", "es": "Codificador de Texto", "de": "Text-Encoder",
    },
    "tool_base64_tools": {
        "fr": "Base64 Tools", "en": "Base64 Tools", "es": "Herramientas Base64", "de": "Base64-Tools",
    },
}


def t(key: str, lang: str = "fr", **kwargs) -> str:
    """Traduction robuste : retombe sur le français puis sur la clé brute si la
    traduction est manquante — ne casse jamais l'affichage."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get("fr") or next(iter(entry.values()), key)
    return text.format(**kwargs) if kwargs else text
