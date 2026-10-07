"""Complete menu registry shared by the dashboard and per-tool launchers."""
import re
import unicodedata
from .tools import legacy
from .localization import EN
from tools.core import TOOLS as EXTRA_TOOLS
from tools.catalog_policy import RETIRED_TOOLS

CATEGORIES=[category for category in legacy.MENU if category!='Settings']
CAT_LABELS={'all':'HOME','IP & Network':'IP & RÉSEAU','Domains & Infrastructure':'DOMAINES','Utilities':'UTILITAIRES'}
CAT_ICONS={'all':'◈','IP & Network':'◎','Domains & Infrastructure':'◇','Utilities':'⌘'}
SHORT={
 'Web Lookup':('WEB LOOKUP','DNS, HTTP et réseau'),
 'IP Localisation':('IP LOCALISATION','Coordonnées & région'),
 'IP Opérateur':('IP OPÉRATEUR','FAI & infrastructure'),
 'Open Ports':('OPEN PORTS','Services TCP accessibles'),
 'IP Pinger':('IP PINGER','Connectivité & latence'),
 'IP Generator':('IP GENERATOR','Adresses IPv4 aléatoires'),
 'WHOIS Lookup':('WHOIS LOOKUP','Identité du domaine'),
 'DNS Records':('DNS RECORDS','Cartographie des enregistrements'),
 'Subdomain Finder':('SUBDOMAIN FINDER','Explorer les sous-domaines'),
 'SSL Certificate Info':('SSL CERTIFICATE','Certificats & expiration'),
 'Hash Tools':('HASH TOOLS','Empreintes & intégrité'),
 'Password Generator':('PASSWORD GENERATOR','Aléatoire cryptographique'),
 'QR Code':('QR CODE','Texte vers code matriciel'),
 'Text Encoder':('TEXT ENCODER','URL · HTML · ROT13 · HEX'),
 'Base64 Tools':('BASE64 TOOLS','Encodage & décodage'),
}
CAT_ART={'IP & Network':'NETWORK','Domains & Infrastructure':'DOMAIN','Utilities':'UTILITY'}
TOOLS=[(cat,num,name) for cat in CATEGORIES for num,name in legacy.MENU[cat] if name not in RETIRED_TOOLS]
CAT_LABELS.update({'Website':'SITES WEB','OSINT':'OSINT','Files & Media':'FICHIERS','Data & Encoding':'DONNÉES','Discord':'DISCORD','Roblox':'ROBLOX'})
EN.update({'SITES WEB':'WEBSITES','FICHIERS':'FILES','DONNÉES':'DATA'})
for tool in EXTRA_TOOLS:
    if tool.category not in CATEGORIES:CATEGORIES.append(tool.category)
    number=1+sum(1 for category,_,_ in TOOLS if category==tool.category)
    TOOLS.append((tool.category,f'{number:02}',tool.name))
    SHORT[tool.name]=(tool.name.upper(),tool.fr)
    legacy.TOOL_DESCRIPTIONS[tool.name]=tool.fr
    EN[tool.fr]=tool.en



def tool_slug(name):
    return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().lower()).strip('-')

TOOL_IDS={tool_slug(name):(cat,name) for cat,_,name in TOOLS}
if len(TOOL_IDS)!=len(TOOLS):raise RuntimeError('Duplicate tool IDs')
