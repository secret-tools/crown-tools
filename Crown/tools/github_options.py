"""Independent Python implementations inspired by established GitHub utilities.

No upstream implementation code is embedded.
"""
import base64
import collections
import difflib
import gzip
import json
import math
from lib.constants import resolve_input_path
from pathlib import Path
import re
import tomllib
from urllib.parse import urlsplit
import zlib

LIMIT=1_000_000

def text(value):
    if not value.strip():raise ValueError('Entrée requise / Input required')
    if len(value)>200000:raise ValueError('Entrée trop longue / Input too long')
    return value

def read_sample(value):
    path=resolve_input_path(text(value))
    if not path.is_file():raise ValueError('Fichier introuvable / File not found')
    with path.open('rb') as stream:data=stream.read(LIMIT+1)
    return path,data[:LIMIT],len(data)>LIMIT

def base32_encode(value):return base64.b32encode(text(value).encode()).decode()
def base32_decode(value):
    raw=''.join(text(value).split()).upper()
    return base64.b32decode(raw+'='*(-len(raw)%8),casefold=True).decode('utf-8')
def gzip_encode(value):return base64.b64encode(gzip.compress(text(value).encode(),mtime=0)).decode()
def gzip_decode(value):
    raw=base64.b64decode(''.join(text(value).split()),validate=True)
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
    data=decoder.decompress(raw,LIMIT+1)
    if len(data)>LIMIT or decoder.unconsumed_tail:raise ValueError('Sortie limitée à 1 Mo / Output limit: 1 MB')
    if not decoder.eof or decoder.unused_data:raise ValueError('Flux gzip incomplet ou multiple / Incomplete or multiple gzip streams')
    return data.decode('utf-8')

def json_query(value):
    path,separator,document=text(value).partition('\n')
    if not separator:raise ValueError('Première ligne : chemin. Lignes suivantes : JSON. / First line: path, then JSON.')
    result=json.loads(document)
    # RFC 6901 JSON Pointer, a focused alternative to full jq expressions.
    if path and not path.startswith('/'):raise ValueError('Chemin JSON Pointer requis : /users/0/name')
    for component in path.split('/')[1:] if path else []:
        component=component.replace('~1','/').replace('~0','~')
        if isinstance(result,list):
            if not re.fullmatch(r'0|[1-9][0-9]*',component):raise ValueError('Index de liste invalide / Invalid array index')
            result=result[int(component)]
        elif isinstance(result,dict):result=result[component]
        else:raise ValueError('Chemin absent / Path does not exist')
    return {'path':path,'value':result}

def split_pair(value):
    parts=re.split(r'^---[ \t]*\r?$',text(value),maxsplit=1,flags=re.M)
    if len(parts)!=2:raise ValueError('Séparer les deux documents par une ligne --- / Separate documents with a line ---')
    a,b=parts
    a=a[:-2] if a.endswith('\r\n') else a.removesuffix('\n')
    b=b[2:] if b.startswith('\r\n') else b.removeprefix('\n')
    return a,b

def json_diff(value):
    a,b=[json.loads(v) for v in split_pair(value)]
    changes=[]
    def walk(left,right,path=''):
        if len(changes)>=200:return
        if type(left)!=type(right):changes.append({'path':path,'change':'changed','before':left,'after':right})
        elif isinstance(left,dict):
            for key in sorted(set(left)|set(right)):
                child=path+'/'+key.replace('~','~0').replace('/','~1')
                if key not in left:changes.append({'path':child,'change':'added','after':right[key]})
                elif key not in right:changes.append({'path':child,'change':'removed','before':left[key]})
                else:walk(left[key],right[key],child)
                if len(changes)>=200:break
        elif isinstance(left,list):
            for index in range(max(len(left),len(right))):
                child=path+'/'+str(index)
                if index>=len(left):changes.append({'path':child,'change':'added','after':right[index]})
                elif index>=len(right):changes.append({'path':child,'change':'removed','before':left[index]})
                else:walk(left[index],right[index],child)
                if len(changes)>=200:break
        elif left!=right:changes.append({'path':path,'change':'changed','before':left,'after':right})
    walk(a,b)
    return {'identical':not changes,'changes':changes,'display_limit':200,'limit_reached':len(changes)>=200}

def toml_json(value):return json.dumps(tomllib.loads(text(value)),indent=2,ensure_ascii=False,default=str)
def text_diff(value):
    a,b=split_pair(value)
    if max(len(a.splitlines()),len(b.splitlines()))>2000:raise ValueError('Maximum 2 000 lignes par document / 2,000-line limit per document')
    return {'identical':a==b,'diff':'\n'.join(difflib.unified_diff(a.splitlines(),b.splitlines(),fromfile='before',tofile='after',lineterm=''))}

def encoding(value):
    from charset_normalizer import from_bytes
    path,data,truncated=read_sample(value)
    result=from_bytes(data).best()
    return {'file':path.name,'sample_bytes':len(data),'sample_truncated':truncated,
            'encoding':result.encoding if result else None,
            'note':'Estimation sur échantillon / Sample-based estimate',
            'preview':str(result)[:1000] if result else 'Indéterminé / Unknown'}
def hexdump(value):
    path,data,truncated=read_sample(value)
    sample=data[:512]
    rows=[]
    for offset in range(0,len(sample),16):
        chunk=sample[offset:offset+16]
        rows.append({'offset':f'{offset:08X}','hex':chunk.hex(' '),
                     'ascii':''.join(chr(b) if 32<=b<127 else '.' for b in chunk)})
    return {'file':path.name,'bytes_shown':len(sample),'rows':rows,'display_limit':512}
def entropy(value):
    path,data,truncated=read_sample(value)
    counts=collections.Counter(data)
    h=-sum((n/len(data))*math.log2(n/len(data)) for n in counts.values()) if data else 0
    return {'file':path.name,'sample_bytes':len(data),'sample_truncated':truncated,
            'entropy_bits_per_byte':round(h,6),'maximum':8,
            'note':'Mesure statistique ; ne détecte pas un malware / Statistical measure, not malware detection'}

def defang(value):
    raw=text(value).strip()
    return raw.replace('https://','hxxps://').replace('http://','hxxp://').replace('.','[.]').replace('@','[@]')
def refang(value):
    return text(value).strip().replace('hxxps://','https://').replace('hxxp://','http://').replace('[.]','.').replace('[@]','@')

def http_response(value):
    from tools.core import fetch,url
    address,headers,body=fetch(url(value))
    try:preview=json.loads(body)
    except json.JSONDecodeError:preview=body[:12000]
    return {'url':address,'headers':headers,'body':preview,
            'note':'GET uniquement ; réponses HTTP non réussies signalées comme erreurs / GET only; non-success HTTP responses shown as errors'}

def github_repo(value):
    from tools.core import api
    raw=text(value).strip().rstrip('/')
    if '://' in raw:
        parsed=urlsplit(raw)
        if parsed.hostname not in ('github.com','www.github.com'):raise ValueError('URL GitHub requise / GitHub URL required')
        raw=parsed.path.strip('/')
    if raw.endswith('.git'):raw=raw[:-4]
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',raw):raise ValueError('Format owner/repo requis / owner/repo required')
    data=api('https://api.github.com/repos/'+raw)
    return {k:data.get(k) for k in ['full_name','description','html_url','stargazers_count','forks_count',
            'open_issues_count','language','topics','license','default_branch','created_at','updated_at','pushed_at','archived']}
def github_user(value):
    from tools.core import api
    raw=text(value).strip().lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',raw):raise ValueError('Pseudo GitHub invalide / Invalid GitHub username')
    data=api('https://api.github.com/users/'+raw)
    return {k:data.get(k) for k in ['login','name','bio','html_url','avatar_url','company','location','blog',
            'public_repos','followers','following','created_at','updated_at']}

def register(add):
    entries=[
        ('Data & Encoding','Base32 Encode','Encoder en Base32','Encode Base32','Texte / Text',base32_encode),
        ('Data & Encoding','Base32 Decode','Décoder le Base32','Decode Base32','JBSWY3DP',base32_decode),
        ('Data & Encoding','Gzip Encode','Compresser le texte en gzip Base64','Compress text to gzip Base64','Texte / Text',gzip_encode),
        ('Data & Encoding','Gzip Decode','Décompresser le gzip Base64','Decompress gzip Base64','Base64 gzip',gzip_decode),
        ('Data & Encoding','JSON Pointer','Extraire une valeur JSON','Extract a JSON value','/users/0/name puis JSON à la ligne suivante',json_query),
        ('Data & Encoding','JSON Diff','Comparer deux documents JSON','Compare two JSON documents','JSON avant / ligne --- / JSON après',json_diff),
        ('Data & Encoding','TOML to JSON','Convertir TOML vers JSON','Convert TOML to JSON','name = "Crown"',toml_json),
        ('Utilities','Text Diff','Comparer deux textes ligne par ligne','Compare text line by line','Texte avant / ligne --- / texte après',text_diff),
        ('Files & Media','Encoding Detector','Estimer l’encodage d’un fichier','Estimate a file encoding','Chemin du fichier / File path',encoding),
        ('Files & Media','File Hexdump','Aperçu hexadécimal du fichier','File hexadecimal preview','Chemin du fichier / File path',hexdump),
        ('Files & Media','File Entropy','Mesurer l’entropie des octets','Measure byte entropy','Chemin du fichier / File path',entropy),
        ('Utilities','URL Defang','Neutraliser un lien pour partage','Defang a link for sharing','https://example.com',defang),
        ('Utilities','URL Refang','Restaurer un lien neutralisé','Restore a defanged link','hxxps://example[.]com',refang),
        ('Website','HTTP Response','Inspecter une réponse HTTP GET','Inspect an HTTP GET response','https://example.com',http_response,True),
        ('OSINT','GitHub Repository','Informations publiques d’un dépôt','Public repository information','owner/repo ou URL GitHub',github_repo,True),
        ('OSINT','GitHub User','Informations publiques d’un profil','Public profile information','Pseudo GitHub / GitHub username',github_user,True),
    ]
    for entry in entries:add(*entry)
