STRINGS = {
    'en': {
        'brand': 'CROWN TOOLS  /  UPDATE CENTER', 'checking': 'Checking your version…',
        'installed': 'Installed', 'update': 'Update ↗', 'retry': 'Retry', 'exit': 'Exit',
        'ready': 'A new version is ready.', 'required': 'Update to continue using Crown Tools.',
        'unavailable': 'Unable to verify your version.',
        'offline': 'Check your connection and try again. Access stays locked until GitHub confirms your version.',
        'files': 'Your Input and Output folders stay on your computer.',
        'instructions': 'Download the new version, extract it into a new folder and run setup.bat.\nKeep your Input and Output folders, then close this window and launch the new copy.',
        'open_link': 'Open this link in your browser: ', 'notes': 'Release notes', 'language': 'Language',
    },
    'fr': {
        'brand': 'CROWN TOOLS  /  MISES À JOUR', 'checking': 'Vérification de votre version…',
        'installed': 'Version installée', 'update': 'Mettre à jour ↗', 'retry': 'Réessayer', 'exit': 'Quitter',
        'ready': 'Une nouvelle version est disponible.', 'required': 'Mettez Crown Tools à jour pour continuer.',
        'unavailable': 'Impossible de vérifier votre version.',
        'offline': 'Vérifiez votre connexion puis réessayez. L’accès reste bloqué jusqu’à la confirmation de GitHub.',
        'files': 'Vos dossiers Input et Output restent sur votre ordinateur.',
        'instructions': 'Téléchargez la nouvelle version, extrayez-la dans un nouveau dossier et lancez setup.bat.\nConservez vos dossiers Input et Output, puis fermez cette fenêtre et lancez la nouvelle copie.',
        'open_link': 'Ouvrez ce lien dans votre navigateur : ', 'notes': 'Nouveautés', 'language': 'Langue',
    },
    'es': {
        'brand': 'CROWN TOOLS  /  ACTUALIZACIONES', 'checking': 'Comprobando tu versión…',
        'installed': 'Versión instalada', 'update': 'Actualizar ↗', 'retry': 'Reintentar', 'exit': 'Salir',
        'ready': 'Hay una nueva versión disponible.', 'required': 'Actualiza Crown Tools para continuar.',
        'unavailable': 'No se pudo comprobar tu versión.',
        'offline': 'Comprueba tu conexión e inténtalo de nuevo. El acceso seguirá bloqueado hasta que GitHub confirme tu versión.',
        'files': 'Tus carpetas Input y Output permanecen en tu equipo.',
        'instructions': 'Descarga la nueva versión, extráela en una carpeta nueva y ejecuta setup.bat.\nConserva tus carpetas Input y Output, cierra esta ventana e inicia la nueva copia.',
        'open_link': 'Abre este enlace en tu navegador: ', 'notes': 'Novedades', 'language': 'Idioma',
    },
    'de': {
        'brand': 'CROWN TOOLS  /  AKTUALISIERUNGEN', 'checking': 'Deine Version wird geprüft…',
        'installed': 'Installierte Version', 'update': 'Aktualisieren ↗', 'retry': 'Erneut prüfen', 'exit': 'Beenden',
        'ready': 'Eine neue Version ist verfügbar.', 'required': 'Aktualisiere Crown Tools, um fortzufahren.',
        'unavailable': 'Deine Version konnte nicht geprüft werden.',
        'offline': 'Prüfe deine Verbindung und versuche es erneut. Der Zugriff bleibt gesperrt, bis GitHub deine Version bestätigt.',
        'files': 'Deine Ordner Input und Output bleiben auf deinem Computer.',
        'instructions': 'Lade die neue Version herunter, entpacke sie in einen neuen Ordner und starte setup.bat.\nBehalte deine Ordner Input und Output, schließe dieses Fenster und starte die neue Kopie.',
        'open_link': 'Öffne diesen Link in deinem Browser: ', 'notes': 'Neuerungen', 'language': 'Sprache',
    },
    'zh': {
        'brand': 'CROWN TOOLS  /  更新中心', 'checking': '正在检查版本…',
        'installed': '已安装版本', 'update': '更新 ↗', 'retry': '重试', 'exit': '退出',
        'ready': '新版本已发布。', 'required': '请更新 Crown Tools 后继续使用。',
        'unavailable': '无法验证当前版本。',
        'offline': '请检查网络连接后重试。在 GitHub 确认版本之前，工具将保持锁定。',
        'files': 'Input 和 Output 文件夹会保留在你的电脑上。',
        'instructions': '下载新版本，解压到新文件夹，然后运行 setup.bat。\n保留 Input 和 Output 文件夹，关闭此窗口，然后启动新版本。',
        'open_link': '请在浏览器中打开此链接：', 'notes': '更新说明', 'language': '语言',
    },
    'ar': {
        'brand': 'CROWN TOOLS  /  مركز التحديثات', 'checking': 'جارٍ التحقق من إصدارك…',
        'installed': 'الإصدار المثبت', 'update': 'تحديث ↗', 'retry': 'إعادة المحاولة', 'exit': 'خروج',
        'ready': 'يتوفر إصدار جديد.', 'required': 'حدّث Crown Tools لمتابعة الاستخدام.',
        'unavailable': 'تعذّر التحقق من إصدارك.',
        'offline': 'تحقق من اتصالك ثم حاول مجددًا. سيبقى الوصول مقفلاً حتى يؤكد GitHub إصدارك.',
        'files': 'ستبقى مجلدات Input وOutput على جهازك.',
        'instructions': 'نزّل الإصدار الجديد وفك ضغطه في مجلد جديد ثم شغّل setup.bat.\nاحتفظ بمجلدات Input وOutput، ثم أغلق هذه النافذة وشغّل النسخة الجديدة.',
        'open_link': 'افتح هذا الرابط في متصفحك: ', 'notes': 'ملاحظات الإصدار', 'language': 'اللغة',
    },
}


def preferred_language(explicit=None):
    if explicit in STRINGS:
        return explicit
    from .config import PROFILE_PATH, read_settings
    saved = read_settings(PROFILE_PATH).get('language', 'en')
    return saved if saved in STRINGS else 'en'


def render_text(language, key):
    text = STRINGS[language][key]
    if language == 'ar':
        from .localization import display_arabic
        return display_arabic(text)
    return text
