"""
Écrans interactifs et intégrés pour les modules VIP de Crown-Tools.
Permet d'exécuter les options VIP directement dans l'interface graphique Textual.
"""
import os
import sys
import re
import shutil
import zipfile
import subprocess
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input
from textual.containers import Vertical, Horizontal, VerticalScroll

from .constants import APP_DIR, INPUT_DIR, OUTPUT_DIR, resolve_input_path
from .tools import legacy
from .ui import ToolPresentation, Topline, color
from .vip_bundle_screen import launch_bundle_module, resolve_entry_path

# ─────────────────────────────────────────────────────────────
#  UI TRANSLATION — 6 langues pour tous les labels statiques
# ─────────────────────────────────────────────────────────────
_VIP_UI = {
    "back":         {"en": "← BACK",    "fr": "← RETOUR",   "es": "← VOLVER",  "de": "← ZURÜCK",  "zh": "← 返回",    "ar": "← رجوع"},
    "execute":      {"en": "RUN  ↗",    "fr": "EXÉCUTER  ↗","es": "EJECUTAR ↗", "de": "AUSFÜHREN ↗","zh": "执行  ↗",   "ar": "تشغيل  ↗"},
    "terminal":     {"en": "TERMINAL ↗","fr": "TERMINAL  ↗", "es": "TERMINAL ↗", "de": "TERMINAL ↗", "zh": "终端  ↗",   "ar": "طرفية  ↗"},
    "launch_term":  {"en": "▶  LAUNCH IN TERMINAL", "fr": "▶  LANCER DANS LE TERMINAL",
                     "es": "▶  LANZAR EN TERMINAL", "de": "▶  IM TERMINAL STARTEN",
                     "zh": "▶  在终端中启动",         "ar": "▶  تشغيل في الطرفية"},
    "result_title": {"en": " OUTPUT / RESULTS ",   "fr": " SORTIE / RÉSULTATS ",
                     "es": " SALIDA / RESULTADOS ", "de": " AUSGABE / ERGEBNISSE ",
                     "zh": " 输出 / 结果 ",           "ar": " الإخراج / النتائج "},
    "info_title":   {"en": " INFORMATION / TERMINAL ", "fr": " INFORMATION / TERMINAL ",
                     "es": " INFORMACIÓN / TERMINAL ", "de": " INFORMATION / TERMINAL ",
                     "zh": " 信息 / 终端 ",             "ar": " معلومات / طرفية "},
    "ready_prompt": {
        "en": "◇\n\nREADY FOR YOUR NEXT QUERY\n\nEnter a target value then press Enter.",
        "fr": "◇\n\nPRÊT POUR VOTRE PROCHAINE EXPLORATION\n\nRenseignez une entrée puis appuyez sur Entrée.",
        "es": "◇\n\nLISTO PARA TU PRÓXIMA CONSULTA\n\nIntroduce un valor objetivo y presiona Enter.",
        "de": "◇\n\nBEREIT FÜR DEINE NÄCHSTE ABFRAGE\n\nGib einen Zielwert ein und drücke Enter.",
        "zh": "◇\n\n准备好你的下一次查询\n\n输入目标值，然后按 Enter。",
        "ar": "◇\n\nجاهز لاستعلامك التالي\n\nأدخل قيمة مستهدفة ثم اضغط Enter.",
    },
    "terminal_msg": {
        "en": ("◈ THIS MODULE REQUIRES AN INTERACTIVE TERMINAL SESSION\n\n"
               "This script listens to background system events or requires multiple interactive prompts.\n"
               "Click 'LAUNCH IN TERMINAL' to open in full console mode."),
        "fr": ("◈ CE MODULE NÉCESSITE UNE SESSION INTERACTIVE DANS LE TERMINAL\n\n"
               "Ce script écoute des événements système continus ou requiert des saisies multiples.\n"
               "Cliquez sur 'LANCER DANS LE TERMINAL' pour ouvrir la session en plein écran."),
        "es": ("◈ ESTE MÓDULO REQUIERE UNA SESIÓN DE TERMINAL INTERACTIVA\n\n"
               "Este script escucha eventos del sistema o requiere entradas múltiples.\n"
               "Haz clic en 'LANZAR EN TERMINAL' para abrirlo en modo consola completa."),
        "de": ("◈ DIESES MODUL ERFORDERT EINE INTERAKTIVE TERMINALSITZUNG\n\n"
               "Dieses Skript horcht auf Systemereignisse oder erfordert mehrere Eingaben.\n"
               "Klicke auf 'IM TERMINAL STARTEN' um es im Vollkonsolenmodus zu öffnen."),
        "zh": ("◈ 此模块需要交互式终端会话\n\n"
               "该脚本监听系统后台事件或需要多步交互输入。\n"
               "点击「在终端中启动」以完整控制台模式打开。"),
        "ar": ("◈ يتطلب هذا الوحدة جلسة طرفية تفاعلية\n\n"
               "يستمع هذا البرنامج النصي لأحداث النظام أو يتطلب إدخالات متعددة.\n"
               "انقر على 'تشغيل في الطرفية' للفتح في وضع وحدة التحكم الكاملة."),
    },
    "footnote_full": {
        "en": "  ESC  Back to dashboard    /    ENTER  Execute    /    TERMINAL  Launch in console",
        "fr": "  ÉCHAP  Retour au tableau de bord    /    ENTRÉE  Exécuter    /    TERMINAL  Lancer en console",
        "es": "  ESC  Volver al panel    /    ENTER  Ejecutar    /    TERMINAL  Lanzar en consola",
        "de": "  ESC  Zurück zum Dashboard    /    ENTER  Ausführen    /    TERMINAL  In Konsole starten",
        "zh": "  ESC  返回仪表板    /    ENTER  执行    /    终端  在控制台启动",
        "ar": "  ESC  العودة إلى لوحة التحكم    /    ENTER  تشغيل    /    الطرفية  إطلاق في وحدة التحكم",
    },
    "footnote_term": {
        "en": "  ESC  Back to dashboard    /    ENTER  Launch in console",
        "fr": "  ÉCHAP  Retour au tableau de bord    /    ENTRÉE  Lancer en console",
        "es": "  ESC  Volver al panel    /    ENTER  Lanzar en consola",
        "de": "  ESC  Zurück zum Dashboard    /    ENTER  In Konsole starten",
        "zh": "  ESC  返回仪表板    /    ENTER  在控制台启动",
        "ar": "  ESC  العودة إلى لوحة التحكم    /    ENTER  إطلاق في وحدة التحكم",
    },
    "timeout": {
        "en": "Execution timeout expired (18s).",
        "fr": "Délai d'attente dépassé (18s).",
        "es": "Tiempo de ejecución agotado (18s).",
        "de": "Ausführungszeitlimit abgelaufen (18s).",
        "zh": "执行超时（18秒）。",
        "ar": "انتهت مهلة التنفيذ (18 ثانية).",
    },
    "no_result": {
        "en": "No results returned by module.",
        "fr": "Aucun résultat retourné par le module.",
        "es": "No se devolvieron resultados.",
        "de": "Keine Ergebnisse vom Modul zurückgegeben.",
        "zh": "模块未返回任何结果。",
        "ar": "لم يُرجع الوحدة أي نتائج.",
    },
    "no_input": {
        "en": "Please provide a valid input value.",
        "fr": "Veuillez renseigner une valeur d'entrée valide.",
        "es": "Por favor, introduce un valor de entrada válido.",
        "de": "Bitte gib einen gültigen Eingabewert an.",
        "zh": "请提供有效的输入值。",
        "ar": "يرجى تقديم قيمة إدخال صحيحة.",
    },
    "exec_error": {
        "en": "Execution error",
        "fr": "Erreur d'exécution",
        "es": "Error de ejecución",
        "de": "Ausführungsfehler",
        "zh": "执行错误",
        "ar": "خطأ في التنفيذ",
    },
    "module_error": {
        "en": "Module error",
        "fr": "Erreur du module",
        "es": "Error del módulo",
        "de": "Modulfehler",
        "zh": "模块错误",
        "ar": "خطأ في الوحدة",
    },
}

def _ui(key: str, lang: str) -> str:
    return _VIP_UI.get(key, {}).get(lang) or _VIP_UI.get(key, {}).get("en", "")


# ─────────────────────────────────────────────────────────────
#  MODULES NÉCESSITANT OBLIGATOIREMENT UN TERMINAL INTERACTIF
# ─────────────────────────────────────────────────────────────
TERMINAL_ONLY_NAMES = {
    "discord graphics",
    "zip cracker",
    "rar cracker",
    "basic auth bf",
    "exif forensic",
    "exif",
}

# ─────────────────────────────────────────────────────────────
#  PLACEHOLDERS — 6 langues — tous les 81 modules
# ─────────────────────────────────────────────────────────────
# Format: {module_name: {lang: placeholder_text}}
VIP_PLACEHOLDERS: dict[str, dict[str, str]] = {

    # ── IP / WEB ─────────────────────────────────────────────
    "IP Lookup": {
        "en": "IP address (e.g. 8.8.8.8)",
        "fr": "Adresse IP (ex : 8.8.8.8)",
        "es": "Dirección IP (ej: 8.8.8.8)",
        "de": "IP-Adresse (z.B. 8.8.8.8)",
        "zh": "IP 地址（如 8.8.8.8）",
        "ar": "عنوان IP (مثال: 8.8.8.8)",
    },
    "IP Localise": {
        "en": "IP address to geolocate (e.g. 8.8.8.8)",
        "fr": "Adresse IP à géolocaliser (ex : 8.8.8.8)",
        "es": "Dirección IP para geolocalizar (ej: 8.8.8.8)",
        "de": "IP-Adresse zur Geolokalisierung (z.B. 8.8.8.8)",
        "zh": "要定位的 IP 地址（如 8.8.8.8）",
        "ar": "عنوان IP للتحديد الجغرافي (مثال: 8.8.8.8)",
    },
    "IP Operator": {
        "en": "IP address — get operator / ISP info",
        "fr": "Adresse IP — infos opérateur / FAI",
        "es": "Dirección IP — info del operador / ISP",
        "de": "IP-Adresse — Operator / ISP-Info",
        "zh": "IP 地址 — 获取运营商信息",
        "ar": "عنوان IP — معلومات المشغل / مزود الخدمة",
    },
    "IP Open Ports": {
        "en": "IP address to port-scan (e.g. 1.1.1.1)",
        "fr": "Adresse IP à scanner (ex : 1.1.1.1)",
        "es": "IP para escaneo de puertos (ej: 1.1.1.1)",
        "de": "IP-Adresse für Port-Scan (z.B. 1.1.1.1)",
        "zh": "要扫描端口的 IP（如 1.1.1.1）",
        "ar": "عنوان IP لمسح المنافذ (مثال: 1.1.1.1)",
    },
    "IP Pinger": {
        "en": "IP address or hostname to ping",
        "fr": "Adresse IP ou domaine à pinger",
        "es": "Dirección IP o dominio a hacer ping",
        "de": "IP-Adresse oder Hostname zum Pingen",
        "zh": "要 ping 的 IP 或主机名",
        "ar": "عنوان IP أو اسم المضيف للـ ping",
    },
    "IP Gen": {
        "en": "Number of random IPs to generate (e.g. 10)",
        "fr": "Nombre d'IPs aléatoires à générer (ex : 10)",
        "es": "Cantidad de IPs a generar (ej: 10)",
        "de": "Anzahl zufälliger IPs (z.B. 10)",
        "zh": "要生成的随机 IP 数量（如 10）",
        "ar": "عدد عناوين IP العشوائية (مثال: 10)",
    },
    "IP Oracle": {
        "en": "IP address for full threat analysis",
        "fr": "Adresse IP pour analyse complète des menaces",
        "es": "IP para análisis completo de amenazas",
        "de": "IP-Adresse für vollständige Bedrohungsanalyse",
        "zh": "用于全面威胁分析的 IP 地址",
        "ar": "عنوان IP لتحليل التهديدات الكامل",
    },
    "IP All Lookup": {
        "en": "IP address — full audit (geo, ASN, ports...)",
        "fr": "Adresse IP — audit complet (géo, ASN, ports…)",
        "es": "IP — auditoría completa (geo, ASN, puertos…)",
        "de": "IP-Adresse — vollständiges Audit (Geo, ASN, Ports…)",
        "zh": "IP 地址 — 完整审计（地理位置、ASN、端口…）",
        "ar": "عنوان IP — تدقيق كامل (موقع جغرافي، ASN، منافذ...)",
    },
    "IP Blacklist": {
        "en": "IP address to check against blacklists",
        "fr": "Adresse IP à vérifier dans les listes noires",
        "es": "IP a verificar en listas negras",
        "de": "IP-Adresse auf Blacklists prüfen",
        "zh": "检查黑名单的 IP 地址",
        "ar": "عنوان IP للتحقق من القوائم السوداء",
    },
    "IP VPN Detector": {
        "en": "IP address — detect VPN / proxy / TOR",
        "fr": "Adresse IP — détecter VPN / proxy / TOR",
        "es": "IP — detectar VPN / proxy / TOR",
        "de": "IP-Adresse — VPN / Proxy / TOR erkennen",
        "zh": "IP 地址 — 检测 VPN / 代理 / TOR",
        "ar": "عنوان IP — اكتشاف VPN / وكيل / TOR",
    },
    "Website Info": {
        "en": "Website URL (e.g. https://example.com)",
        "fr": "URL du site (ex : https://example.com)",
        "es": "URL del sitio (ej: https://example.com)",
        "de": "Website-URL (z.B. https://example.com)",
        "zh": "网站 URL（如 https://example.com）",
        "ar": "عنوان URL للموقع (مثال: https://example.com)",
    },
    "URL Scanner": {
        "en": "URL to scan for malware / phishing",
        "fr": "URL à analyser (malware, phishing…)",
        "es": "URL a escanear (malware, phishing…)",
        "de": "URL auf Malware / Phishing scannen",
        "zh": "扫描恶意软件/网络钓鱼的 URL",
        "ar": "URL للمسح بحثًا عن البرامج الضارة / التصيد",
    },
    "Vuln Scanner": {
        "en": "Website URL to vulnerability-scan",
        "fr": "URL du site à analyser (vulnérabilités)",
        "es": "URL del sitio para escaneo de vulnerabilidades",
        "de": "Website-URL für Schwachstellenscan",
        "zh": "要扫描漏洞的网站 URL",
        "ar": "عنوان URL للموقع لمسح الثغرات",
    },
    "Web Cloner": {
        "en": "Website URL to clone locally",
        "fr": "URL du site à cloner localement",
        "es": "URL del sitio a clonar localmente",
        "de": "Website-URL zum lokalen Klonen",
        "zh": "要本地克隆的网站 URL",
        "ar": "عنوان URL للموقع للاستنساخ المحلي",
    },
    "Subdomain BF": {
        "en": "Domain name to brute-force subdomains (e.g. example.com)",
        "fr": "Domaine à brute-forcer les sous-domaines (ex : example.com)",
        "es": "Dominio para fuerza bruta de subdominios (ej: example.com)",
        "de": "Domain für Subdomain-Brute-Force (z.B. example.com)",
        "zh": "要暴力枚举子域名的域名（如 example.com）",
        "ar": "اسم النطاق لتخمين النطاقات الفرعية (مثال: example.com)",
    },
    "Admin Hunter": {
        "en": "Website URL to hunt admin panels",
        "fr": "URL du site pour trouver les panneaux admin",
        "es": "URL del sitio para buscar paneles de admin",
        "de": "Website-URL für Admin-Panel-Suche",
        "zh": "搜索管理面板的网站 URL",
        "ar": "عنوان URL للبحث عن لوحات الإدارة",
    },
    "Dir Buster": {
        "en": "Website URL to enumerate directories",
        "fr": "URL du site pour énumérer les répertoires",
        "es": "URL para enumeración de directorios",
        "de": "Website-URL für Verzeichnisenumeration",
        "zh": "要枚举目录的网站 URL",
        "ar": "عنوان URL لتعداد المجلدات",
    },
    "Domain Intel": {
        "en": "Domain name (e.g. github.com)",
        "fr": "Nom de domaine (ex : github.com)",
        "es": "Nombre de dominio (ej: github.com)",
        "de": "Domainname (z.B. github.com)",
        "zh": "域名（如 github.com）",
        "ar": "اسم النطاق (مثال: github.com)",
    },

    # ── OSINT ────────────────────────────────────────────────
    "Name Finder": {
        "en": "Full name or username to search",
        "fr": "Nom complet ou pseudo à rechercher",
        "es": "Nombre completo o usuario a buscar",
        "de": "Vollständiger Name oder Benutzername",
        "zh": "要搜索的全名或用户名",
        "ar": "الاسم الكامل أو اسم المستخدم للبحث",
    },
    "Email Info": {
        "en": "Email address (e.g. user@domain.com)",
        "fr": "Adresse email (ex : user@domain.com)",
        "es": "Dirección de correo (ej: user@domain.com)",
        "de": "E-Mail-Adresse (z.B. user@domain.com)",
        "zh": "电子邮件地址（如 user@domain.com）",
        "ar": "عنوان البريد الإلكتروني (مثال: user@domain.com)",
    },
    "Email OSINT": {
        "en": "Email address for OSINT deep-dive",
        "fr": "Adresse email pour analyse OSINT approfondie",
        "es": "Correo electrónico para análisis OSINT",
        "de": "E-Mail-Adresse für OSINT-Analyse",
        "zh": "用于 OSINT 深度分析的电子邮件",
        "ar": "عنوان البريد الإلكتروني لتحليل OSINT",
    },
    "Number Info": {
        "en": "Phone number with country code (e.g. +33612345678)",
        "fr": "Numéro avec indicatif pays (ex : +33612345678)",
        "es": "Número con código de país (ej: +33612345678)",
        "de": "Telefonnummer mit Ländervorwahl (z.B. +33612345678)",
        "zh": "带国家区号的电话号码（如 +33612345678）",
        "ar": "رقم الهاتف مع رمز البلد (مثال: +33612345678)",
    },
    "Search DB": {
        "en": "Email, username or phone to search in leaks",
        "fr": "Email, pseudo ou téléphone à rechercher dans les fuites",
        "es": "Email, usuario o teléfono a buscar en filtraciones",
        "de": "E-Mail, Benutzername oder Telefon in Leaks suchen",
        "zh": "在泄露库中搜索的电子邮件、用户名或电话",
        "ar": "البريد الإلكتروني أو اسم المستخدم أو الهاتف للبحث في التسريبات",
    },
    "Username Hunter": {
        "en": "Username to hunt across all platforms",
        "fr": "Pseudo à traquer sur toutes les plateformes",
        "es": "Nombre de usuario a rastrear en todas las plataformas",
        "de": "Benutzername auf allen Plattformen suchen",
        "zh": "跨所有平台追踪的用户名",
        "ar": "اسم المستخدم للتتبع عبر جميع المنصات",
    },
    "Breach Finder": {
        "en": "Email or username to check in breach databases",
        "fr": "Email ou pseudo à rechercher dans les bases de données de fuite",
        "es": "Email o usuario en bases de datos de brechas",
        "de": "E-Mail oder Benutzername in Breach-Datenbanken",
        "zh": "在泄露数据库中检查的电子邮件或用户名",
        "ar": "البريد الإلكتروني أو اسم المستخدم في قواعد بيانات الاختراق",
    },
    "EXIF Forensic": {
        "en": "Path to local image file (e.g. C:\\image.jpg)",
        "fr": "Chemin du fichier image local (ex : C:\\image.jpg)",
        "es": "Ruta al archivo de imagen local (ej: C:\\imagen.jpg)",
        "de": "Pfad zur lokalen Bilddatei (z.B. C:\\bild.jpg)",
        "zh": "本地图像文件路径（如 C:\\image.jpg）",
        "ar": "مسار ملف الصورة المحلي (مثال: C:\\image.jpg)",
    },

    # ── DISCORD ──────────────────────────────────────────────
    "Token Checker": {
        "en": "Discord user or bot token to validate",
        "fr": "Token Discord utilisateur ou bot à valider",
        "es": "Token de usuario o bot de Discord a validar",
        "de": "Discord-Benutzer- oder Bot-Token prüfen",
        "zh": "要验证的 Discord 用户或机器人令牌",
        "ar": "رمز مستخدم أو بوت Discord للتحقق",
    },
    "User Lookup": {
        "en": "Discord User ID (numeric, e.g. 123456789012345678)",
        "fr": "ID utilisateur Discord (chiffres, ex : 123456789012345678)",
        "es": "ID de usuario Discord (numérico)",
        "de": "Discord-Benutzer-ID (numerisch)",
        "zh": "Discord 用户 ID（数字，如 123456789012345678）",
        "ar": "معرف مستخدم Discord (رقمي)",
    },
    "Invite Resolver": {
        "en": "Discord invite code or full URL",
        "fr": "Code d'invitation ou URL Discord complète",
        "es": "Código de invitación o URL de Discord",
        "de": "Discord-Einladungscode oder vollständige URL",
        "zh": "Discord 邀请码或完整 URL",
        "ar": "رمز الدعوة أو عنوان URL الكامل لـ Discord",
    },
    "Webhook Info": {
        "en": "Discord Webhook URL",
        "fr": "URL de webhook Discord",
        "es": "URL del Webhook de Discord",
        "de": "Discord-Webhook-URL",
        "zh": "Discord Webhook URL",
        "ar": "عنوان URL لـ Discord Webhook",
    },

    # ── SOCIAL ───────────────────────────────────────────────
    "Username Check": {
        "en": "Username to check across all social networks",
        "fr": "Pseudo à vérifier sur tous les réseaux sociaux",
        "es": "Usuario a verificar en todas las redes sociales",
        "de": "Benutzername auf allen sozialen Netzwerken prüfen",
        "zh": "跨所有社交网络检查的用户名",
        "ar": "اسم المستخدم للتحقق عبر جميع الشبكات الاجتماعية",
    },
    "YouTube Channel": {
        "en": "YouTube @handle or channel ID",
        "fr": "Handle YouTube (@...) ou ID de chaîne",
        "es": "Handle de YouTube (@...) o ID de canal",
        "de": "YouTube @Handle oder Kanal-ID",
        "zh": "YouTube @频道 或频道 ID",
        "ar": "@معرف يوتيوب أو معرف القناة",
    },
    "YouTube Video": {
        "en": "YouTube video URL or video ID",
        "fr": "URL de la vidéo YouTube ou ID de vidéo",
        "es": "URL del vídeo de YouTube o ID de vídeo",
        "de": "YouTube-Video-URL oder Video-ID",
        "zh": "YouTube 视频 URL 或视频 ID",
        "ar": "عنوان URL فيديو YouTube أو معرف الفيديو",
    },
    "X / Twitter Profile": {
        "en": "Twitter / X username (e.g. @elonmusk)",
        "fr": "Nom d'utilisateur Twitter / X (ex : @elonmusk)",
        "es": "Nombre de usuario de Twitter / X (ej: @elonmusk)",
        "de": "Twitter / X-Benutzername (z.B. @elonmusk)",
        "zh": "Twitter / X 用户名（如 @elonmusk）",
        "ar": "اسم مستخدم Twitter / X (مثال: @elonmusk)",
    },
    "TikTok Profile": {
        "en": "TikTok username (e.g. @username)",
        "fr": "Nom d'utilisateur TikTok (ex : @username)",
        "es": "Usuario de TikTok (ej: @username)",
        "de": "TikTok-Benutzername (z.B. @username)",
        "zh": "TikTok 用户名（如 @username）",
        "ar": "اسم مستخدم TikTok (مثال: @username)",
    },
    "Instagram Profile": {
        "en": "Instagram username (e.g. username)",
        "fr": "Nom d'utilisateur Instagram (ex : username)",
        "es": "Usuario de Instagram (ej: username)",
        "de": "Instagram-Benutzername (z.B. username)",
        "zh": "Instagram 用户名（如 username）",
        "ar": "اسم مستخدم Instagram (مثال: username)",
    },
    "Snapchat Check": {
        "en": "Snapchat username to check",
        "fr": "Nom d'utilisateur Snapchat à vérifier",
        "es": "Usuario de Snapchat a verificar",
        "de": "Snapchat-Benutzername prüfen",
        "zh": "要检查的 Snapchat 用户名",
        "ar": "اسم مستخدم Snapchat للتحقق",
    },
    "Telegram Channel": {
        "en": "Telegram @channel or t.me/... URL",
        "fr": "Canal Telegram (@canal) ou URL t.me/...",
        "es": "Canal de Telegram (@canal) o URL t.me/...",
        "de": "Telegram @Kanal oder t.me/...-URL",
        "zh": "Telegram @频道 或 t.me/... URL",
        "ar": "قناة Telegram (@channel) أو عنوان t.me/...",
    },

    # ── ROBLOX ───────────────────────────────────────────────
    "Roblox Username Lookup": {
        "en": "Roblox username to look up",
        "fr": "Pseudo Roblox à rechercher",
        "es": "Nombre de usuario de Roblox",
        "de": "Roblox-Benutzername",
        "zh": "要查找的 Roblox 用户名",
        "ar": "اسم مستخدم Roblox للبحث",
    },
    "Roblox Profile Viewer": {
        "en": "Roblox username",
        "fr": "Pseudo Roblox",
        "es": "Usuario de Roblox",
        "de": "Roblox-Benutzername",
        "zh": "Roblox 用户名",
        "ar": "اسم مستخدم Roblox",
    },
    "Roblox Friends List": {
        "en": "Roblox username to list friends",
        "fr": "Pseudo Roblox pour voir la liste d'amis",
        "es": "Usuario de Roblox para ver amigos",
        "de": "Roblox-Benutzername für Freundesliste",
        "zh": "查看好友列表的 Roblox 用户名",
        "ar": "اسم مستخدم Roblox لعرض قائمة الأصدقاء",
    },
    "Roblox Followers Count": {
        "en": "Roblox username to count followers",
        "fr": "Pseudo Roblox pour compter les abonnés",
        "es": "Usuario de Roblox para contar seguidores",
        "de": "Roblox-Benutzername für Followerzahl",
        "zh": "统计粉丝数量的 Roblox 用户名",
        "ar": "اسم مستخدم Roblox لعد المتابعين",
    },
    "Roblox Account Age": {
        "en": "Roblox username to check account age",
        "fr": "Pseudo Roblox pour voir l'ancienneté du compte",
        "es": "Usuario de Roblox para ver antigüedad",
        "de": "Roblox-Benutzername — Kontoalter",
        "zh": "检查账户年龄的 Roblox 用户名",
        "ar": "اسم مستخدم Roblox للتحقق من عمر الحساب",
    },
    "Roblox Cookie Checker": {
        "en": ".ROBLOSECURITY Cookie to validate",
        "fr": "Cookie .ROBLOSECURITY à valider",
        "es": "Cookie .ROBLOSECURITY para validar",
        "de": ".ROBLOSECURITY-Cookie prüfen",
        "zh": "要验证的 .ROBLOSECURITY Cookie",
        "ar": "كوكي .ROBLOSECURITY للتحقق",
    },
    "Roblox Game Pass Lookup": {
        "en": "Roblox Game Pass ID (numeric)",
        "fr": "ID du Game Pass Roblox (chiffres)",
        "es": "ID del Game Pass de Roblox (numérico)",
        "de": "Roblox-Gamepass-ID (numerisch)",
        "zh": "Roblox 游戏通行证 ID（数字）",
        "ar": "معرف تصريح اللعبة Roblox (رقمي)",
    },
    "Roblox Place Universe": {
        "en": "Roblox Place ID to get Universe ID",
        "fr": "ID de place Roblox pour obtenir l'ID de l'univers",
        "es": "ID de lugar Roblox para obtener Universe ID",
        "de": "Roblox-Place-ID für Universe-ID",
        "zh": "获取宇宙 ID 的 Roblox 地点 ID",
        "ar": "معرف مكان Roblox للحصول على معرف الكون",
    },
    "Roblox Catalog Search": {
        "en": "Keyword to search Roblox catalog items",
        "fr": "Mot-clé pour rechercher dans le catalogue Roblox",
        "es": "Palabra clave para buscar en el catálogo Roblox",
        "de": "Stichwort für Roblox-Katalogsuche",
        "zh": "搜索 Roblox 商品目录的关键词",
        "ar": "كلمة رئيسية للبحث في كتالوج Roblox",
    },
    "Roblox Multi Cookie Check": {
        "en": "Cookie list (one per line) or file path",
        "fr": "Liste de cookies (un par ligne) ou chemin de fichier",
        "es": "Lista de cookies (uno por línea) o ruta de archivo",
        "de": "Cookie-Liste (eins pro Zeile) oder Dateipfad",
        "zh": "Cookie 列表（每行一个）或文件路径",
        "ar": "قائمة الكوكيز (واحدة في كل سطر) أو مسار الملف",
    },
    "Roblox Export Profile JSON": {
        "en": "Roblox username to export as JSON",
        "fr": "Pseudo Roblox à exporter en JSON",
        "es": "Usuario de Roblox para exportar a JSON",
        "de": "Roblox-Benutzername für JSON-Export",
        "zh": "导出为 JSON 的 Roblox 用户名",
        "ar": "اسم مستخدم Roblox للتصدير كـ JSON",
    },
    "Roblox Avatar Batch": {
        "en": "User ID list (comma-separated) or file path",
        "fr": "Liste d'IDs utilisateurs (virgule) ou chemin de fichier",
        "es": "Lista de IDs de usuario (coma) o ruta de archivo",
        "de": "Benutzer-ID-Liste (kommagetrennt) oder Dateipfad",
        "zh": "用户 ID 列表（逗号分隔）或文件路径",
        "ar": "قائمة معرفات المستخدمين (مفصولة بفواصل) أو مسار الملف",
    },
    "Roblox Group Funds": {
        "en": "Roblox Group ID to check funds",
        "fr": "ID du groupe Roblox pour voir les fonds",
        "es": "ID del grupo Roblox para ver fondos",
        "de": "Roblox-Gruppen-ID für Fondsabfrage",
        "zh": "查看资金的 Roblox 群组 ID",
        "ar": "معرف مجموعة Roblox للتحقق من الأموال",
    },
    "Roblox Game Lookup": {
        "en": "Roblox Game / Place ID",
        "fr": "ID du jeu / place Roblox",
        "es": "ID del juego / lugar de Roblox",
        "de": "Roblox-Spiel / Place-ID",
        "zh": "Roblox 游戏 / 地点 ID",
        "ar": "معرف لعبة / مكان Roblox",
    },
    "Roblox Group Lookup": {
        "en": "Roblox Group ID to look up",
        "fr": "ID du groupe Roblox à rechercher",
        "es": "ID del grupo Roblox a buscar",
        "de": "Roblox-Gruppen-ID",
        "zh": "要查找的 Roblox 群组 ID",
        "ar": "معرف مجموعة Roblox للبحث",
    },
    "Roblox Robux Checker": {
        "en": ".ROBLOSECURITY Cookie to check Robux balance",
        "fr": "Cookie .ROBLOSECURITY pour vérifier le solde Robux",
        "es": "Cookie .ROBLOSECURITY para verificar saldo Robux",
        "de": ".ROBLOSECURITY-Cookie für Robux-Guthaben",
        "zh": "检查 Robux 余额的 .ROBLOSECURITY Cookie",
        "ar": "كوكي .ROBLOSECURITY للتحقق من رصيد Robux",
    },
    "Roblox Badge Checker": {
        "en": "Roblox Badge ID (numeric)",
        "fr": "ID du badge Roblox (chiffres)",
        "es": "ID de insignia Roblox (numérico)",
        "de": "Roblox-Abzeichen-ID (numerisch)",
        "zh": "Roblox 徽章 ID（数字）",
        "ar": "معرف شارة Roblox (رقمي)",
    },
    "Roblox Limited Price": {
        "en": "Roblox Limited Item / Asset ID",
        "fr": "ID de l'item limité Roblox",
        "es": "ID de item limitado de Roblox",
        "de": "Roblox-Limited-Item / Asset-ID",
        "zh": "Roblox 限量商品 / 资产 ID",
        "ar": "معرف عنصر محدود Roblox / معرف الأصول",
    },
    "Roblox Avatar Viewer": {
        "en": "Roblox User ID (numeric)",
        "fr": "ID utilisateur Roblox (chiffres)",
        "es": "ID de usuario Roblox (numérico)",
        "de": "Roblox-Benutzer-ID (numerisch)",
        "zh": "Roblox 用户 ID（数字）",
        "ar": "معرف مستخدم Roblox (رقمي)",
    },
    "Roblox Account Checker": {
        "en": ".ROBLOSECURITY Cookie to audit account",
        "fr": "Cookie .ROBLOSECURITY pour auditer le compte",
        "es": "Cookie .ROBLOSECURITY para auditar la cuenta",
        "de": ".ROBLOSECURITY-Cookie für Kontoprüfung",
        "zh": "审计账户的 .ROBLOSECURITY Cookie",
        "ar": "كوكي .ROBLOSECURITY لتدقيق الحساب",
    },
    "Roblox Item Lookup": {
        "en": "Roblox Item / Asset ID",
        "fr": "ID de l'item Roblox",
        "es": "ID de item de Roblox",
        "de": "Roblox-Item / Asset-ID",
        "zh": "Roblox 商品 / 资产 ID",
        "ar": "معرف عنصر Roblox / معرف الأصول",
    },
    "Roblox Inventory View": {
        "en": "Roblox User ID to view inventory",
        "fr": "ID utilisateur Roblox pour voir l'inventaire",
        "es": "ID de usuario Roblox para ver inventario",
        "de": "Roblox-Benutzer-ID für Inventar",
        "zh": "查看库存的 Roblox 用户 ID",
        "ar": "معرف مستخدم Roblox لعرض المخزون",
    },
    "Roblox Game Favorites": {
        "en": "Roblox Game / Place ID to count favorites",
        "fr": "ID du jeu Roblox pour compter les favoris",
        "es": "ID del juego Roblox para contar favoritos",
        "de": "Roblox-Spiel-ID für Favoritenanzahl",
        "zh": "统计收藏数的 Roblox 游戏 ID",
        "ar": "معرف لعبة Roblox لعد المفضلات",
    },
    "Roblox Group Roles": {
        "en": "Roblox Group ID to list roles",
        "fr": "ID du groupe Roblox pour lister les rôles",
        "es": "ID del grupo Roblox para listar roles",
        "de": "Roblox-Gruppen-ID für Rollenliste",
        "zh": "列出角色的 Roblox 群组 ID",
        "ar": "معرف مجموعة Roblox لعرض الأدوار",
    },

    # ── UTILS ────────────────────────────────────────────────
    "Hash Crack": {
        "en": "MD5, SHA1 or SHA256 hash to crack",
        "fr": "Hash MD5, SHA1 ou SHA256 à cracker",
        "es": "Hash MD5, SHA1 o SHA256 a crackear",
        "de": "MD5-, SHA1- oder SHA256-Hash knacken",
        "zh": "要破解的 MD5、SHA1 或 SHA256 哈希",
        "ar": "تجزئة MD5 أو SHA1 أو SHA256 لكسرها",
    },
    "Passw Gen": {
        "en": "Password length (8–64, e.g. 20)",
        "fr": "Longueur du mot de passe (8–64, ex : 20)",
        "es": "Longitud de contraseña (8–64, ej: 20)",
        "de": "Passwortlänge (8–64, z.B. 20)",
        "zh": "密码长度（8–64，如 20）",
        "ar": "طول كلمة المرور (8–64، مثال: 20)",
    },
    "Temp Mail": {
        "en": "Press Enter to generate a temporary email",
        "fr": "Appuyez sur Entrée pour générer un email temporaire",
        "es": "Presiona Enter para generar un correo temporal",
        "de": "Enter drücken für temporäre E-Mail",
        "zh": "按 Enter 生成临时邮箱",
        "ar": "اضغط Enter لإنشاء بريد إلكتروني مؤقت",
    },
    "Base64": {
        "en": "Text to encode — or Base64 string to decode",
        "fr": "Texte à encoder — ou chaîne Base64 à décoder",
        "es": "Texto a codificar — o cadena Base64 a decodificar",
        "de": "Text zum Kodieren — oder Base64-String dekodieren",
        "zh": "要编码的文本 — 或要解码的 Base64 字符串",
        "ar": "نص للتشفير — أو سلسلة Base64 لفك التشفير",
    },
    "QR Gen": {
        "en": "Text or URL to encode as QR code",
        "fr": "Texte ou URL à encoder en QR code",
        "es": "Texto o URL para codificar como código QR",
        "de": "Text oder URL als QR-Code kodieren",
        "zh": "要编码为 QR 码的文本或 URL",
        "ar": "نص أو URL لترميزه كرمز QR",
    },
    "URL Short": {
        "en": "Long URL to shorten",
        "fr": "URL longue à raccourcir",
        "es": "URL larga para acortar",
        "de": "Lange URL kürzen",
        "zh": "要缩短的长 URL",
        "ar": "عنوان URL الطويل للتقصير",
    },
    "JSON Format": {
        "en": "Raw JSON string to format and prettify",
        "fr": "Chaîne JSON brute à formater",
        "es": "Cadena JSON sin formato para formatear",
        "de": "Rohen JSON-String formatieren",
        "zh": "要格式化的原始 JSON 字符串",
        "ar": "سلسلة JSON الخام للتنسيق",
    },

    # ── ATTACK ───────────────────────────────────────────────
    "Zip Cracker": {
        "en": "Requires interactive terminal",
        "fr": "Nécessite un terminal interactif",
        "es": "Requiere terminal interactiva",
        "de": "Erfordert interaktives Terminal",
        "zh": "需要交互式终端",
        "ar": "يتطلب طرفية تفاعلية",
    },
    "Rar Cracker": {
        "en": "Requires interactive terminal",
        "fr": "Nécessite un terminal interactif",
        "es": "Requiere terminal interactiva",
        "de": "Erfordert interaktives Terminal",
        "zh": "需要交互式终端",
        "ar": "يتطلب طرفية تفاعلية",
    },

    # ── TERMINAL ────────────────────────────────────────────
    "Discord Graphics": {
        "en": "Requires interactive terminal",
        "fr": "Nécessite un terminal interactif",
        "es": "Requiere terminal interactiva",
        "de": "Erfordert interaktives Terminal",
        "zh": "需要交互式终端",
        "ar": "يتطلب طرفية تفاعلية",
    },
    "Basic Auth BF": {
        "en": "Requires interactive terminal (URL + wordlist)",
        "fr": "Nécessite un terminal interactif (URL + wordlist)",
        "es": "Requiere terminal interactiva (URL + wordlist)",
        "de": "Erfordert interaktives Terminal (URL + Wortliste)",
        "zh": "需要交互式终端（URL + 字典）",
        "ar": "يتطلب طرفية تفاعلية (URL + قائمة الكلمات)",
    },

    # ── PLUGINS ──────────────────────────────────────────────
    "Example Plugin": {
        "en": "Enter any value to test the plugin",
        "fr": "Entrez une valeur pour tester le plugin",
        "es": "Ingresa un valor para probar el plugin",
        "de": "Beliebigen Wert eingeben (Plugin-Test)",
        "zh": "输入任意值以测试插件",
        "ar": "أدخل أي قيمة لاختبار الإضافة",
    },
}


def get_placeholder(name: str, lang: str = "en") -> str:
    """Retourne le placeholder localisé pour un module VIP donné."""
    from .vip_policy import require_allowed_module
    require_allowed_module(module)
    lang = lang if lang in ("en", "fr", "es", "de", "zh", "ar") else "en"

    # Exact match
    entry = VIP_PLACEHOLDERS.get(name)
    if entry:
        return entry.get(lang) or entry.get("en", "")

    # Fuzzy match (substring)
    name_l = name.lower()
    for k, v in VIP_PLACEHOLDERS.items():
        if k.lower() in name_l or name_l in k.lower():
            return v.get(lang) or v.get("en", "")

    # Generic fallback
    _generic = {
        "en": "Enter input value...",
        "fr": "Entrez une valeur...",
        "es": "Introduce un valor...",
        "de": "Eingabewert eingeben...",
        "zh": "输入值...",
        "ar": "أدخل قيمة...",
    }
    return _generic.get(lang, "Enter input value...")


def is_terminal_only(name: str) -> bool:
    clean = name.lower().strip()
    if "[premium]" in clean or "premium" in clean:
        return True
    if clean in TERMINAL_ONLY_NAMES:
        return True
    return any(t in clean for t in [
        "zip cracker",
        "rar cracker", "nitro gen", "graphics", "basic auth",
        "générateur multi", "generateur multi"
    ])


# ─────────────────────────────────────────────────────────────
#  CACHE EXTRACTION ZIP
# ─────────────────────────────────────────────────────────────
def get_extracted_vip_root(archive_path) -> Path:
    arc = Path(archive_path).resolve()
    from .vip_bundle import validate
    with zipfile.ZipFile(arc) as archive:
        validate(archive)
    mtime = arc.stat().st_mtime
    cache_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\CrownTools\vip_extracted"))
    stamp_file = cache_dir / ".stamp"

    if cache_dir.is_dir() and stamp_file.is_file():
        try:
            if float(stamp_file.read_text().strip()) == mtime:
                return cache_dir
        except Exception:
            pass

    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(arc) as zf:
        zf.extractall(cache_dir)

    try:
        stamp_file.write_text(str(mtime))
    except Exception:
        pass
    return cache_dir


# ─────────────────────────────────────────────────────────────
#  NETTOYAGE DE LA SORTIE TERMINAL
# ─────────────────────────────────────────────────────────────
# Box-drawing characters used in tool banners
_BOX_CHARS = set("─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬═║╭╮╯╰")
_ANSI_ESC = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]+[a-zA-Z]')

# Phrases that signal a line to drop (lowercased, substring match)
_SKIP_PHRASES = {
    # press enter — all languages + rich markup variants
    'press enter', 'press [bold', 'appuyez sur entr', 'appuie sur entr',
    'presiona enter', 'presione enter', 'drücke enter', 'drücken sie enter',
    '按回车键', '按 enter', '按enter', 'اضغط enter', '엔터를 누르세요',
    'нажмите enter',
    # skip exit prompts (only when combined with enter/key pattern)
    'appuie sur une touche', 'drücke eine taste', '按任意键',
    # tool infrastructure lines
    'system armed', 'sec-node', 'crown tools // defense', 'crown-vip //',
    'crown-tools  //  ', '// osint', '// geo-tracking', '// report',
    '// discord', '// roblox', '// social', '// attack', '// utils',
    '// ip', '// web', '// gen',
}


def _strip_ansi(line: str) -> str:
    return _ANSI_ESC.sub('', line)


def _is_banner_line(plain: str) -> bool:
    """True si la ligne est un cadre de bannière decoratif à supprimer."""
    stripped = plain.strip()
    if not stripped:
        return False
    # Line made almost entirely of box/border chars + spaces
    # ── 1. Pure horizontal border lines (┌──┐, └──┘, ─────): always drop ──────
    # These lines are made of horizontal box chars only (no │ content lines).
    # Only apply the ratio check when the line does NOT start/end with │.
    if not (stripped.startswith('│') or stripped.endswith('│')):
        non_box = sum(1 for c in stripped if c not in _BOX_CHARS and c != ' ')
        if len(stripped) > 4 and non_box / len(stripped) < 0.15:
            return True

    # ── 2. Wide centered │...│ banner lines (title bars only) ─────────────────
    if stripped.startswith('│') and stripped.endswith('│'):
        inner = stripped[1:-1].strip()
        # Always keep section headers like │ ┌─[ IP Address ]
        if inner.startswith('┌─[') or inner.startswith('└─'):
            return False
        # Drop CROWN-TOOLS header banners
        if 'CROWN-TOOLS' in inner or 'CROWN TOOLS' in inner:
            return True
        # Drop if inner is purely box chars / empty
        inner_no_box = _strip_ansi(inner).strip()
        if not inner_no_box or all(c in _BOX_CHARS or c == ' ' for c in inner_no_box):
            return True
        # Keep everything else — data results, descriptions, tool names, etc.
        return False

    return False


def _is_skip_phrase(plain_lower: str) -> bool:
    return any(sp in plain_lower for sp in _SKIP_PHRASES)


def clean_terminal_output(raw: str) -> str:
    """Nettoie la sortie terminal: supprime bandeaux, prompts, artefacts ANSI."""
    # First pass: strip terminal control sequences (cursor, clear screen, etc.)
    text = re.sub(r'\x1b\[\?[0-9]+[a-zA-Z]', '', raw)
    text = re.sub(r'\x1b\[[0-9;]*[HfJ]', '', text)

    lines = text.splitlines()
    filtered = []

    for line in lines:
        plain = _strip_ansi(line).strip()
        plain_l = plain.lower()

        # Drop blank lines at the start (keep them mid-output)
        if not plain and not filtered:
            continue

        # Drop skip phrases
        if _is_skip_phrase(plain_l):
            continue

        # Drop interactive prompt lines (end with >> — stdin prompt lines)
        if plain.endswith('>>'):
            continue

        # Drop concatenated prompt+box lines: "Prompt >> Prompt2 >> ┌────┐"
        # These occur when tools write prompts without newlines before the result box.
        if '>>' in plain:
            after_last = plain.rsplit('>>', 1)[-1].strip()
            # If what follows >> is a box border start (┌/└) OR purely box chars → prompt concat
            if after_last.startswith(('┌', '└', '╔', '╚')) or not any(
                c not in _BOX_CHARS and c != ' ' for c in after_last
            ):
                continue

        if plain_l.startswith('open ?') or plain_l.startswith('ouvrir ?'):
            continue
        # Drop standalone prompt arrows (└─▶ or │└─▶│ etc.)
        stripped_box = ''.join(c for c in plain if c not in _BOX_CHARS and c not in ' ▶▸►→')
        if not stripped_box and plain.strip():
            continue
        # Drop input-prompt section headers that introduce a user input field
        # (e.g. "┌─[ Adresse IP Cible ]" followed by "└─▶")
        if plain.startswith('┌─[') and plain.endswith(']') and len(plain) < 50:
            continue

        # Drop decorative banner lines
        if _is_banner_line(plain):
            continue

        # Drop Rich markup that leaked as plain text (not ANSI-rendered)
        if plain.startswith('[bold') and plain.endswith('[/]'):
            continue

        filtered.append(line)

    # Strip trailing blank lines
    while filtered and not _strip_ansi(filtered[-1]).strip():
        filtered.pop()

    return '\n'.join(filtered)


# ─────────────────────────────────────────────────────────────
#  EXÉCUTION HEADLESS
# ─────────────────────────────────────────────────────────────
def execute_vip_headless(module: dict, value: str, lang: str, archive_path) -> Text:
    from .vip_policy import require_allowed_module
    require_allowed_module(module)
    lang = lang if lang in ("en", "fr", "es", "de", "zh", "ar") else "en"

    if (not value or not value.strip()) and module["name"].lower() != "temp mail":
        return Text(_ui("no_input", lang), style="bold red")

    root = get_extracted_vip_root(Path(archive_path))
    target_script = resolve_entry_path(root, module['entry'], lang)

    env = os.environ.copy()
    env['CROWN_NO_ANIM'] = '1'
    if module['name'].lower() == 'exif forensic':
        env['CROWN_IMAGE_PATH'] = value.strip().strip(chr(34))
    env['CROWN_LANG'] = lang
    env['CROWN_MODULE_NAME'] = module['name']
    env['CROWN_MODULE_CAT'] = module.get('category', 'VIP')
    # Force UTF-8 output
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    env['CROWN_INPUT_DIR'] = str(INPUT_DIR)
    env['CROWN_OUTPUT_DIR'] = str(OUTPUT_DIR)

    tools_dir = root / 'tools'
    lib_dir = root / 'tools' / 'lib'
    pythonpath = os.pathsep.join(
        [str(root), str(tools_dir), str(lib_dir)]
        + ([env['PYTHONPATH']] if 'PYTHONPATH' in env else [])
    )
    env['PYTHONPATH'] = pythonpath

    # Per-tool stdin templates: maps module name (lower) → callable(value) → stdin string
    # Most tools: first input = target value
    # Some tools have a preceding choice prompt before the actual value
    _INPUT_TEMPLATES = {
        "base64":       lambda v: f"e\n{v}\n\n\n",   # e=encode, then text
        "json format":  lambda v: f"{v}\n\n\n",
        "passw gen":    lambda v: f"{v}\n\n\n",       # length
        "qr gen":       lambda v: f"{v}\n\n\n",
        "url short":    lambda v: f"{v}\n\n\n",
        "hash crack":   lambda v: f"{v}\n\n\n",
        "temp mail":    lambda v: f"\n\n\n",          # no input needed, just hit enter
    }
    name_l = module['name'].lower()
    template_fn = None
    for key, fn in _INPUT_TEMPLATES.items():
        if key in name_l:
            template_fn = fn
            break
    proc_input = template_fn(value.strip()) if template_fn else f"{value.strip()}\n\n\n\n"

    try:
        p = subprocess.Popen(
            [sys.executable, str(target_script)],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        out, err = p.communicate(input=proc_input, timeout=20)
    except subprocess.TimeoutExpired:
        try:
            p.kill()
        except Exception:
            pass
        return Text(_ui("timeout", lang), style="bold red")
    except Exception as exc:
        return Text(f"{_ui('exec_error', lang)}: {exc}", style="bold red")

    cleaned = clean_terminal_output(out)

    if not cleaned.strip():
        if err and err.strip():
            err_clean = _strip_ansi(err.strip())
            return Text(f"{_ui('module_error', lang)}:\n{err_clean}", style="bold red")
        return Text(_ui("no_result", lang), style="dim")

    return Text.from_ansi(cleaned)


# ─────────────────────────────────────────────────────────────
#  ÉCRAN TERMINAL-ONLY
# ─────────────────────────────────────────────────────────────
class VipTerminalToolScreen(Screen):
    """Écran pour les modules nécessitant obligatoirement un terminal interactif."""
    from textual.binding import Binding
    BINDINGS = [Binding("escape", "close_screen", "Fermer")]

    def __init__(self, module: dict, archive_path):
        self.TITLE_TOOL = module['name']
        self.PLACEHOLDER = ""
        self.MODULE_DEF = module
        self.ARCHIVE_PATH = archive_path
        super().__init__()

    def compose(self) -> ComposeResult:
        lang = getattr(self.app, 'lang', 'en')
        yield Topline(classes='tool-topline')
        with Vertical(id='tool-toolbar'):
            with Horizontal(id='title-row'):
                yield Button(_ui("back", lang), id='back-btn')
                yield Static(
                    Text(self.TITLE_TOOL.upper(), style='bold ' + color(self.app, 'crown-accent')),
                    id='screen-title'
                )
            yield Static(Text(self.app.descriptions.get(self.TITLE_TOOL, '')), id='tool-context')
            with Horizontal(id='input-row'):
                yield Button(_ui("launch_term", lang), id='run-terminal-btn', variant='error')
        with VerticalScroll(id='result-scroll') as result:
            result.border_title = _ui("info_title", lang)
            yield Static(_ui("terminal_msg", lang), id='tool-empty')
        yield Static(_ui("footnote_term", lang), classes='tool-footnote')

    def on_mount(self) -> None:
        self.app.localize(self)
        self.set_class(self.app.size.height < 30, 'compact-tool')
        self.query_one('#run-terminal-btn', Button).focus()
        if self.app.motion:
            self.styles.opacity = 0.
            self.styles.animate('opacity', 1., duration=.18)

    def action_close_screen(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'back-btn':
            self.app.pop_screen()
        elif event.button.id == 'run-terminal-btn':
            launch_bundle_module(self.app, self.MODULE_DEF, self.ARCHIVE_PATH)


# ─────────────────────────────────────────────────────────────
#  ÉCRAN INTÉGRÉ DE BASE (tous les modules non-terminal-only)
# ─────────────────────────────────────────────────────────────
class BaseVipIntegratedScreen(ToolPresentation, legacy.ToolScreen):
    """Écran intégré pour les modules VIP exécutables dans Textual."""
    MODULE_DEF: dict = {}
    ARCHIVE_PATH = None

    def compose(self) -> ComposeResult:
        lang = getattr(self.app, 'lang', 'en')
        placeholder_text = get_placeholder(self.TITLE_TOOL, lang)
        yield Topline(classes='tool-topline')
        with Vertical(id='tool-toolbar'):
            with Horizontal(id='title-row'):
                yield Button(_ui("back", lang), id='back-btn')
                yield Static(
                    Text(self.TITLE_TOOL.upper(), style='bold ' + color(self.app, 'crown-accent')),
                    id='screen-title'
                )
                yield Button(_ui("terminal", lang), id='terminal-btn')
            yield Static(Text(self.app.descriptions.get(self.TITLE_TOOL, '')), id='tool-context')
            with Horizontal(id='input-row'):
                yield Input(placeholder=placeholder_text, id='tool-input', disabled=self.TITLE_TOOL.lower() == 'temp mail')
                yield Button(_ui("execute", lang), id='run-btn', variant='error')
        with VerticalScroll(id='result-scroll') as result:
            result.border_title = _ui("result_title", lang)
            yield Static(_ui("ready_prompt", lang), id='tool-empty')
        yield Static(_ui("footnote_full", lang), classes='tool-footnote')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'back-btn':
            self.app.pop_screen()
        elif event.button.id == 'run-btn':
            self.run_tool()
        elif event.button.id == 'terminal-btn':
            launch_bundle_module(self.app, self.MODULE_DEF, self.ARCHIVE_PATH)

    def on_mount(self):
        if self.TITLE_TOOL.lower() == 'temp mail':
            self.query_one('#run-btn', Button).focus()
        elif self.TITLE_TOOL.lower() == 'exif forensic':
            self.call_after_refresh(self.run_tool)

    def run_tool(self):
        if self.TITLE_TOOL.lower() == 'exif forensic':
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                try:
                    selected = filedialog.askopenfilename(title='Crown — Image EXIF',initialdir=str(INPUT_DIR),
                        filetypes=[('Images', '*.jpg *.jpeg *.png *.webp *.tif *.tiff'), ('All files', '*.*')])
                finally:
                    root.destroy()
                if not selected:
                    return
                self.query_one('#tool-input', Input).value = selected
            except Exception as exc:
                self.app.notify(f'Sélecteur indisponible : {exc}. Saisissez le chemin.', severity='warning')
                if not self.query_one('#tool-input', Input).value.strip():
                    return
        super().run_tool()

    def execute(self, value: str):
        lang = getattr(self.app, 'lang', 'en')
        if self.TITLE_TOOL.lower() == 'exif forensic':value=str(resolve_input_path(value))
        return execute_vip_headless(self.MODULE_DEF, value, lang, self.ARCHIVE_PATH)


# ─────────────────────────────────────────────────────────────
#  FACTORY
# ─────────────────────────────────────────────────────────────
def create_vip_screen(module: dict, archive_path, app=None):
    """Fabrique dynamiquement la classe d'écran Textual pour un module VIP donné.
    Avec une application, chaque option est lancée directement dans le terminal
    sans passer par un écran intermédiaire."""
    from .vip_policy import require_allowed_module
    require_allowed_module(module)
    name = module['name']
    if app is not None or is_terminal_only(name):
        def _direct_terminal_launcher(a=app, m=dict(module), arc=archive_path):
            if a is not None:
                launch_bundle_module(a, m, arc)
                return None
            return VipTerminalToolScreen(m, arc)
        return _direct_terminal_launcher

    attrs = {
        'TITLE_TOOL': name,
        'PLACEHOLDER': get_placeholder(name, 'en'),
        'MODULE_DEF': dict(module),
        'ARCHIVE_PATH': archive_path,
    }
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return type(f"VipScreen_{clean_name}", (BaseVipIntegratedScreen,), attrs)

