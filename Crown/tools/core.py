"""Read-only public lookups and local utilities, integrated into the Crown UI.
No credentials, external scripts, shell commands or automatic file writes.
"""
from lib.constants import resolve_input_path
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin, parse_qsl, quote, unquote
from html.parser import HTMLParser
import base64, hashlib, ipaddress, json, re, socket, uuid, zipfile
import requests
import dns.resolver
from PIL import Image, ExifTags

@dataclass(frozen=True)
class Tool:
    category: str
    name: str
    fr: str
    en: str
    hint: str
    run: object
    network: bool=False

TOOLS=[]
def add(cat,name,fr,en,hint,fn,network=False):
    TOOLS.append(Tool(cat,name,fr,en,hint,fn,network))

def required(value):
    if not value.strip():raise ValueError('Entrée requise / Input required')
    if len(value)>200000:raise ValueError('Entrée trop longue / Input too long')
    return value.strip()

def domain(value):
    raw=required(value)
    host=urlsplit(raw if '://' in raw else '//'+raw).hostname
    if not host:raise ValueError('Domaine invalide / Invalid domain')
    host=host.encode('idna').decode('ascii').rstrip('.')
    if len(host)>253 or not all(re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?',part) for part in host.split('.')):
        raise ValueError('Domaine invalide / Invalid domain')
    return host

def url(value):
    value=required(value)
    value=value if '://' in value else 'https://'+value
    parsed=urlsplit(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('URL HTTP(S) sans identifiants requise / HTTP(S) URL without credentials required')
    return value

def fetch(address,*,json_body=None):
    # Bounded read and explicit timeouts; no cookies or saved credentials.
    with requests.request('POST' if json_body is not None else 'GET',address,json=json_body,
                          headers={'User-Agent':'Crown-Tools/1.0','Accept':'application/json, text/html;q=0.9, */*;q=0.5'},
                          timeout=(5,12),stream=True) as response:
        response.raise_for_status()
        chunks=[];size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size>2_000_000:raise ValueError('Réponse limitée à 2 Mo / Response limit: 2 MB')
            chunks.append(chunk)
        return response.url,dict(response.headers),b''.join(chunks).decode(response.encoding or 'utf-8',errors='replace')

def api(address,body=None):return json.loads(fetch(address,json_body=body)[2])
def numeric(value):
    value=required(value)
    if not re.fullmatch(r'[1-9][0-9]{0,19}',value):raise ValueError('Identifiant numérique requis / Numeric ID required')
    return value

def dns_records(value,kind):
    host=domain(value)
    records=dns.resolver.resolve(host,kind,lifetime=6)
    return {'domain':host,'type':kind,'records':[r.to_text() for r in records]}

def email_info(value):
    value=required(value)
    if value.count('@')!=1:raise ValueError('Adresse invalide / Invalid email')
    local,host=value.rsplit('@',1)
    if not local or len(local)>64 or re.search(r'\s',local):raise ValueError('Adresse invalide / Invalid email')
    host=domain(host)
    return {'address':value,'domain':host,'mx':dns_records(host,'MX')['records'],
            'note':'MX only: this does not verify that the mailbox exists.'}

def subnet(value):
    n=ipaddress.ip_network(required(value),strict=False)
    if n.version==4 and n.prefixlen<31:first,last=n.network_address+1,n.broadcast_address-1
    else:first,last=n.network_address,n.broadcast_address
    return {'network':str(n),'version':n.version,'netmask':str(n.netmask),'addresses':n.num_addresses,
            'first_host':str(first),'last_host':str(last),'private':n.is_private,'global':n.is_global}

def ip_info(value):
    a=ipaddress.ip_address(required(value))
    return {'ip':str(a),'version':a.version,'expanded':a.exploded,'integer':int(a),'reverse_pointer':a.reverse_pointer,
            'private':a.is_private,'global':a.is_global,'loopback':a.is_loopback,'multicast':a.is_multicast,'reserved':a.is_reserved}

def reverse_dns(value):
    a=ipaddress.ip_address(required(value))
    return {'ip':str(a),'PTR':[r.to_text() for r in dns.resolver.resolve(a.reverse_pointer,'PTR',lifetime=6)]}

class Page(HTMLParser):
    def __init__(self):super().__init__();self.in_title=False;self.title=[];self.links=[];self.meta={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='title':self.in_title=True
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='meta' and attrs.get('content'):self.meta[attrs.get('name') or attrs.get('property') or 'meta']=attrs['content']
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title.append(data)

def website(value,links=False):
    final,headers,body=fetch(url(value));page=Page();page.feed(body)
    if links:
        found=sorted({urljoin(final,x) for x in page.links if urlsplit(urljoin(final,x)).scheme in ('http','https')})
        return {'url':final,'link_count':len(found),'links':found[:250],'limit':250}
    return {'url':final,'title':''.join(page.title).strip(),'metadata':page.meta,'headers':headers}

def website_file(value,name):
    parsed=urlsplit(url(value));address=f'{parsed.scheme}://{parsed.netloc}/{name}'
    final,headers,body=fetch(address)
    return {'url':final,'content':body[:50000],'truncated':len(body)>50000}

def header_info(value):
    final,headers,_=fetch(url(value))
    keys=['Strict-Transport-Security','Content-Security-Policy','X-Content-Type-Options','Referrer-Policy','Permissions-Policy','X-Frame-Options']
    lower={k.lower():v for k,v in headers.items()}
    return {'url':final,'headers':{k:lower.get(k.lower(),'Not present') for k in keys},'note':'Presence check only, not a vulnerability assessment.'}

def parse_url(value):
    u=urlsplit(url(value))
    return {'scheme':u.scheme,'host':u.hostname,'port':u.port,'path':u.path,'query':parse_qsl(u.query,keep_blank_values=True),'fragment':u.fragment}

def path_file(value,limit=100_000_000):
    p=resolve_input_path(required(value))
    if not p.is_file():raise ValueError('Fichier introuvable / File not found')
    if p.stat().st_size>limit:raise ValueError(f'Fichier trop volumineux / File exceeds {limit} bytes')
    return p

def file_hash(value):
    p=path_file(value,512_000_000);h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return {'file':str(p),'size':p.stat().st_size,'sha256':h.hexdigest()}

def image_info(value,exif=False):
    p=path_file(value,50_000_000)
    with Image.open(p) as im:
        result={'file':str(p),'format':im.format,'width':im.width,'height':im.height,'mode':im.mode,'frames':getattr(im,'n_frames',1)}
        if exif:result['EXIF']={str(ExifTags.TAGS.get(k,k)):str(v)[:2000] for k,v in im.getexif().items()}
        return result

def zip_info(value):
    p=path_file(value)
    with zipfile.ZipFile(p) as z:
        entries=z.infolist()
        return {'file':str(p),'count':len(entries),'entries':[{'name':i.filename,'size':i.file_size,'compressed':i.compress_size,'encrypted':bool(i.flag_bits&1)} for i in entries[:500]],'limit':500}

def text_stats(value):
    required(value)
    return {'characters':len(value),'utf8_bytes':len(value.encode()),'words':len(value.split()),'lines':len(value.splitlines()),'unique_words':len(set(value.casefold().split()))}

def json_pretty(value):return json.dumps(json.loads(required(value)),indent=2,ensure_ascii=False)
def json_minify(value):return json.dumps(json.loads(required(value)),separators=(',',':'),ensure_ascii=False)
def jwt_decode(value):
    parts=required(value).split('.')
    if len(parts)!=3:raise ValueError('JWT attendu : header.payload.signature / Expected JWT')
    def decode(x):return json.loads(base64.urlsafe_b64decode(x+'='*(-len(x)%4)))
    return {'header':decode(parts[0]),'payload':decode(parts[1]),'signature_verified':False,'note':'Local decoding only. Claims are untrusted.'}
def timestamp(value):
    value=value.strip()
    if not value:dt=datetime.now(timezone.utc)
    elif re.fullmatch(r'-?\d+(\.\d+)?',value):dt=datetime.fromtimestamp(float(value),timezone.utc)
    else:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return {'utc':dt.astimezone(timezone.utc).isoformat(),'unix_seconds':dt.timestamp()}
def uuid_gen(value):
    count=int(value or '1')
    if not 1<=count<=50:raise ValueError('1–50')
    return [str(uuid.uuid4()) for _ in range(count)]
def color_info(value):
    h=required(value).lstrip('#')
    if not re.fullmatch('[0-9a-fA-F]{6}',h):raise ValueError('#RRGGBB')
    rgb=[int(h[i:i+2],16) for i in (0,2,4)]
    return {'hex':'#'+h.upper(),'rgb':rgb,'css':f'rgb({rgb[0]}, {rgb[1]}, {rgb[2]})'}
def snowflake(value):
    n=int(numeric(value))
    if n>=2**64:raise ValueError('ID exceeds 64 bits')
    return {'id':str(n),'created_utc':datetime.fromtimestamp(((n>>22)+1420070400000)/1000,timezone.utc).isoformat(),'worker':(n>>17)&31,'process':(n>>12)&31,'increment':n&4095}
def invite(value):
    code=required(value).rstrip('/').rsplit('/',1)[-1]
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,100}',code):raise ValueError('Code d’invitation invalide / Invalid invite code')
    data=api('https://discord.com/api/v10/invites/'+code+'?with_counts=true')
    return {k:data.get(k) for k in ('code','guild','channel','approximate_member_count','approximate_presence_count','expires_at')}
def roblox_user(value):
    value=required(value)
    if value.isdecimal():uid=numeric(value)
    else:
        if not re.fullmatch(r'[A-Za-z0-9_]{3,20}',value):raise ValueError('Pseudo Roblox invalide / Invalid Roblox username')
        data=api('https://users.roblox.com/v1/usernames/users',{'usernames':[value],'excludeBannedUsers':False}).get('data',[])
        if not data:raise ValueError('Profil introuvable / Profile not found')
        uid=str(data[0]['id'])
    return api('https://users.roblox.com/v1/users/'+uid)
def roblox_age(value):
    data=roblox_user(value);created=datetime.fromisoformat(data['created'].replace('Z','+00:00'))
    return {'id':data['id'],'name':data['name'],'created':data['created'],'age_days':(datetime.now(timezone.utc)-created).days}
def roblox_count(value,kind):return api(f'https://friends.roblox.com/v1/users/{numeric(value)}/{kind}/count')
def roblox_game(value):
    universe=api(f'https://apis.roblox.com/universes/v1/places/{numeric(value)}/universe')['universeId']
    return api(f'https://games.roblox.com/v1/games?universeIds={universe}')

add('IP & Network','IP Inspector','Classification IPv4 / IPv6','IPv4 / IPv6 classification','Ex. 192.168.1.1',ip_info)
add('IP & Network','Subnet Calculator','Réseau, masque et plage','Network, mask and range','Ex. 192.168.1.0/24',subnet)
add('IP & Network','Reverse DNS','Résolution DNS inverse','Reverse DNS records','Ex. 1.1.1.1',reverse_dns,True)
for name,kind,fr,en in [('MX Lookup','MX','Serveurs de messagerie','Mail servers'),('TXT Lookup','TXT','Enregistrements texte DNS','DNS text records'),('NS Lookup','NS','Serveurs DNS autoritaires','Authoritative name servers')]:
    add('Domains & Infrastructure',name,fr,en,'Ex. example.com',lambda v,k=kind:dns_records(v,k),True)
add('Website','Website Info','Titre, métadonnées et en-têtes','Title, metadata and headers','Ex. https://example.com',website,True)
add('Website','URL Scanner','Liens présents sur une page','Links found on one page','Ex. https://example.com',lambda v:website(v,True),True)
add('Website','HTTP Headers','En-têtes de sécurité HTTP','HTTP security headers','Ex. https://example.com',header_info,True)
add('Website','Robots Reader','Lire le fichier robots.txt','Read robots.txt','Ex. https://example.com',lambda v:website_file(v,'robots.txt'),True)
add('Website','Sitemap Reader','Lire le fichier sitemap.xml','Read sitemap.xml','Ex. https://example.com',lambda v:website_file(v,'sitemap.xml'),True)
add('Website','URL Inspector','Décomposer une URL','Inspect URL components','Ex. https://example.com/?q=test',parse_url)
add('OSINT','Email Info','Domaine mail et serveurs MX','Email domain and MX records','Ex. contact@example.com',email_info,True)
add('Files & Media','EXIF Forensic','Métadonnées locales de photo','Local photo metadata','Chemin du fichier / File path',lambda v:image_info(v,True))
add('Files & Media','Image Info','Format et dimensions d’image','Image format and dimensions','Chemin du fichier / File path',image_info)
add('Files & Media','File SHA256','Empreinte SHA-256 de fichier','File SHA-256 digest','Chemin du fichier / File path',file_hash)
add('Files & Media','ZIP Inspector','Lister sans extraire','List archive without extracting','Chemin .zip / ZIP path',zip_info)
add('Data & Encoding','JSON Format','Valider et indenter JSON','Validate and format JSON','Ex. {"hello":"world"}',json_pretty)
add('Data & Encoding','JSON Minify','JSON compact sans espaces','Compact JSON representation','Ex. {"hello":"world"}',json_minify)
add('Data & Encoding','JWT Inspector','Décodage local, sans validation','Local decoding, not verification','header.payload.signature',jwt_decode)
add('Data & Encoding','URL Decode','Décoder les caractères URL','Decode URL escapes','Ex. hello%20world',lambda v:unquote(required(v)))
add('Data & Encoding','Hex Encode','Texte UTF-8 vers hexadécimal','UTF-8 text to hexadecimal','Texte / Text',lambda v:required(v).encode().hex())
add('Data & Encoding','Hex Decode','Hexadécimal vers texte UTF-8','Hexadecimal to UTF-8 text','Ex. 68656c6c6f',lambda v:bytes.fromhex(required(v)).decode('utf-8'))
add('Data & Encoding','Text Statistics','Compter mots et caractères','Count words and characters','Texte / Text',text_stats)
add('Utilities','UUID Generator','Identifiants aléatoires UUID v4','Random UUID v4 identifiers','Nombre / Count : 1–50',uuid_gen)
add('Utilities','Timestamp','Conversion date / Unix UTC','UTC date / Unix conversion','ISO 8601 / Unix seconds (empty = now)',timestamp)
add('Utilities','Color Converter','Couleur HEX vers RGB','HEX to RGB color','Ex. #FF506A',color_info)
add('Discord','Invite Resolver','Informations d’invitation publique','Public invite information','Ex. https://discord.gg/kaostools',invite,True)
add('Discord','Snowflake Decoder','Date de création d’un identifiant','Creation time from a Discord ID','Discord ID',snowflake)
add('Roblox','Username Lookup','Profil public par pseudo ou ID','Public profile by username or ID','Roblox username / ID',roblox_user,True)
add('Roblox','Account Age','Date de création du compte','Account creation date','Roblox username / ID',roblox_age,True)
add('Roblox','Friends Count','Nombre public d’amis','Public friend count','Roblox user ID',lambda v:roblox_count(v,'friends'),True)
add('Roblox','Followers Count','Nombre public d’abonnés','Public follower count','Roblox user ID',lambda v:roblox_count(v,'followers'),True)
add('Roblox','Following Count','Nombre public d’abonnements','Public following count','Roblox user ID',lambda v:roblox_count(v,'followings'),True)
add('Roblox','Group Lookup','Informations publiques du groupe','Public group information','Roblox group ID',lambda v:api('https://groups.roblox.com/v1/groups/'+numeric(v)),True)
add('Roblox','Game Lookup','Informations publiques du jeu','Public game information','Roblox place ID',roblox_game,True)
add('Roblox','Place to Universe','Résoudre l’univers d’une place','Resolve a place universe','Roblox place ID',lambda v:api(f'https://apis.roblox.com/universes/v1/places/{numeric(v)}/universe'),True)
add('Roblox','Avatar Info','Configuration publique de l’avatar','Public avatar configuration','Roblox user ID',lambda v:api(f'https://avatar.roblox.com/v1/users/{numeric(v)}/avatar'),True)


from tools.release_options import register as register_release_options
register_release_options(add)

from tools.github_options import register as register_github_options
register_github_options(add)

from tools.final_options import register as register_final_options
register_final_options(add)

from tools.catalog_policy import RETIRED_TOOLS
TOOLS[:]=[tool for tool in TOOLS if tool.name not in RETIRED_TOOLS]
