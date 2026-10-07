"""The final eleven public-information and local-analysis options."""
from lib.constants import resolve_input_path
import collections
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email import policy
from email.parser import BytesParser, Parser
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import threading
from urllib.parse import quote, unquote_plus, urlsplit, urlunsplit

FILE_LIMIT=20_000_000
SKIP_DIRS={'.git','.venv','venv','node_modules','__pycache__','packages'}
_secret_lock=threading.Lock()

def required(value):
    if not value.strip():raise ValueError('Entrée requise / Input required')
    if len(value)>200000:raise ValueError('Entrée trop longue / Input too long')
    return value.strip()
def file_path(value):
    path=resolve_input_path(required(value))
    if not path.is_file():raise ValueError('Fichier introuvable / File not found')
    if path.stat().st_size>FILE_LIMIT:raise ValueError('Fichier limité à 20 Mo / File limit: 20 MB')
    return path
def folder(value):
    path=resolve_input_path(required(value))
    if not path.is_dir():raise ValueError('Dossier introuvable / Directory not found')
    return path.resolve()
def walk_files(root,limit=1000):
    for directory,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in SKIP_DIRS and not Path(directory,d).is_symlink())
        for name in sorted(files):
            path=Path(directory,name)
            if path.is_symlink():continue
            yield path
            limit-=1
            if limit<=0:return

def usernames(value):
    import requests
    user=required(value).lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,39}',user):raise ValueError('Pseudo invalide / Invalid username')
    safe=quote(user,safe='')
    services=[
        ('GitHub',f'https://api.github.com/users/{safe}',f'https://github.com/{safe}',lambda d:d.get('login','').casefold()==user.casefold()),
        ('GitLab',f'https://gitlab.com/api/v4/users?username={safe}',f'https://gitlab.com/{safe}',lambda d:any(v.get('username','').casefold()==user.casefold() for v in d) if isinstance(d,list) else False),
        ('DEV',f'https://dev.to/api/users/by_username?url={safe}',f'https://dev.to/{safe}',lambda d:d.get('username','').casefold()==user.casefold()),
        ('Hacker News',f'https://hacker-news.firebaseio.com/v0/user/{safe}.json',f'https://news.ycombinator.com/user?id={safe}',lambda d:d.get('id')==user if isinstance(d,dict) else False),
        ('Codeberg',f'https://codeberg.org/api/v1/users/{safe}',f'https://codeberg.org/{safe}',lambda d:d.get('login','').casefold()==user.casefold()),
        ('Reddit',f'https://www.reddit.com/user/{safe}/about.json',f'https://www.reddit.com/user/{safe}',lambda d:d.get('data',{}).get('name','').casefold()==user.casefold()),
    ]
    def check(service):
        name,address,profile,validate=service
        try:
            with requests.get(address,headers={'User-Agent':'Crown-Tools/2.3 public profile checker','Accept':'application/json'},timeout=(4,7),stream=True) as response:
                code=response.status_code
                if code==404:return {'service':name,'status':'absent','http':code,'url':profile}
                if code!=200:return {'service':name,'status':'indéterminé / unknown','http':code,'url':profile}
                chunks=[];size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>1_000_000:raise ValueError('Response too large')
                    chunks.append(chunk)
                import json
                data=json.loads(b''.join(chunks))
                found=validate(data)
                if found:status='présent / present'
                elif name=='GitLab' and data==[] or name=='Hacker News' and data is None:status='absent'
                else:status='indéterminé / unknown'
                return {'service':name,'status':status,'http':code,'url':profile}
        except Exception as exc:return {'service':name,'status':'indéterminé / unknown','detail':type(exc).__name__,'url':profile}
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(check,services))
    return {'username':user,'results':results,'scope':'6 services publics / 6 public services',
            'note':'Même pseudo ≠ même personne / Matching usernames do not establish identity'}

def phone(value):
    import phonenumbers as p
    from phonenumbers import carrier,geocoder,timezone
    raw=required(value).split('|')
    if len(raw)>2:raise ValueError('Format : +336... ou 06... | FR')
    region=raw[1].strip().upper() if len(raw)==2 else None
    if region and region not in p.SUPPORTED_REGIONS:raise ValueError('Code pays invalide / Invalid region code')
    number=p.parse(raw[0].strip(),region)
    types={getattr(p.PhoneNumberType,key):key for key in ['FIXED_LINE','MOBILE','FIXED_LINE_OR_MOBILE','TOLL_FREE','PREMIUM_RATE','SHARED_COST','VOIP','PERSONAL_NUMBER','PAGER','UAN','VOICEMAIL','UNKNOWN']}
    return {'international':p.format_number(number,p.PhoneNumberFormat.INTERNATIONAL),'E164':p.format_number(number,p.PhoneNumberFormat.E164),
            'possible':p.is_possible_number(number),'valid':p.is_valid_number(number),'region':p.region_code_for_number(number),
            'type':types.get(p.number_type(number),'UNKNOWN'),'area':geocoder.description_for_number(number,'fr'),
            'original_carrier':carrier.name_for_number(number,'en'),'timezones':list(timezone.time_zones_for_number(number)),
            'note':'Métadonnées du plan de numérotation ; pas de propriétaire ni localisation en direct / Numbering-plan metadata only'}

def rdap(value):
    from tools.core import api,domain
    host=domain(value)
    tld=host.rsplit('.',1)[-1]
    bootstrap=api('https://data.iana.org/rdap/dns.json')
    endpoints=next((urls for tlds,urls in bootstrap.get('services',[]) if tld in tlds),[])
    if not endpoints:raise ValueError('RDAP indisponible pour ce TLD / No RDAP service for this TLD')
    address=next((u for u in endpoints if u.startswith('https://')),None)
    if not address:raise ValueError('Aucun service RDAP HTTPS / No HTTPS RDAP endpoint')
    source=address.rstrip('/')+'/domain/'+quote(host,safe='')
    data=api(source)
    contacts=[]
    for entity in data.get('entities',[]):
        card=entity.get('vcardArray',[])
        fields=card[1] if len(card)>1 and isinstance(card[1],list) else []
        name=next((v[3] for v in fields if len(v)>3 and v[0]=='fn'),None)
        contacts.append({'name':name,'roles':entity.get('roles',[]),'handle':entity.get('handle')})
    return {'domain':data.get('ldhName',host),'source':source,'handle':data.get('handle'),
            'status':data.get('status',[]),'events':data.get('events',[]),'nameservers':[d.get('ldhName') for d in data.get('nameservers',[])],
            'dnssec':data.get('secureDNS',{}),'entities':contacts,
            'note':'Informations publiques disponibles ; champs parfois masqués / Public registration data; some fields may be redacted'}

def mail_headers(value):
    raw=required(value)
    # File mode is explicit enough to avoid turning multiline headers into paths.
    if '\n' not in raw and '\r' not in raw:
        path=file_path(raw)
        message=BytesParser(policy=policy.default).parsebytes(path.read_bytes(),headersonly=True)
    else:message=Parser(policy=policy.default).parsestr(raw,headersonly=True)
    received=[]
    for index,header in enumerate(message.get_all('Received',[])[:50],1):
        header=str(header)
        from_match=re.search(r'\bfrom\s+([^\s;]+)',header,re.I)
        by_match=re.search(r'\bby\s+([^\s;]+)',header,re.I)
        received.append({'hop':index,'from':from_match.group(1) if from_match else None,'by':by_match.group(1) if by_match else None,'raw':header[:2000]})
    return {'from':str(message.get('From','')),'to':str(message.get('To','')),'reply_to':str(message.get('Reply-To','')),
            'subject':str(message.get('Subject','')),'date':str(message.get('Date','')),'message_id':str(message.get('Message-ID','')),
            'authentication_results':[str(v) for v in message.get_all('Authentication-Results',[])[:20]],
            'received':received,'defects':[type(v).__name__ for v in message.defects],
            'note':'En-têtes déclarés, non vérifiés ; Received présenté du plus récent au plus ancien / Unverified declared headers, newest hop first'}

def email_audit(value):
    from tools.core import domain
    import dns.resolver
    host=domain(value)
    def txt(name):
        try:
            answer=dns.resolver.resolve(name,'TXT',lifetime=5)
            return [''.join(part.decode('utf-8',errors='replace') for part in row.strings) for row in answer],None
        except (dns.resolver.NXDOMAIN,dns.resolver.NoAnswer):return [],'absent'
        except Exception as exc:return [],type(exc).__name__
    records,spf_error=txt(host)
    spf=[v for v in records if v.lower().startswith('v=spf1')]
    records,dmarc_error=txt('_dmarc.'+host)
    dmarc=[v for v in records if v.lower().startswith('v=dmarc1')]
    findings=[]
    if len(spf)!=1:findings.append('SPF absent ou multiple / SPF missing or multiple')
    if len(dmarc)!=1:findings.append('DMARC absent ou multiple / DMARC missing or multiple')
    policy_values={}
    if len(dmarc)==1:
        tags=[v.strip().split('=',1) for v in dmarc[0].split(';') if v.strip()]
        if any(len(v)!=2 for v in tags):findings.append('Balise DMARC invalide / Invalid DMARC tag')
        for item in tags:
            if len(item)==2:
                key,content=item
                if key.lower() in policy_values:findings.append('Balise DMARC dupliquée / Duplicate DMARC tag: '+key)
                policy_values[key.lower()]=content
        if policy_values.get('p') not in ('none','quarantine','reject'):findings.append('Politique DMARC absente ou invalide / Missing or invalid DMARC policy')
    return {'domain':host,'spf_records':spf,'spf_dns_status':spf_error or 'OK','dmarc_records':dmarc,
            'dmarc_dns_status':dmarc_error or 'OK','dmarc_tags':policy_values,'findings':findings,
            'note':'Audit des enregistrements publiés ; pas de simulation complète SPF ni vérification DKIM / Published-record audit, not full SPF or DKIM verification'}

def secret_audit(value):
    from detect_secrets.core.scan import scan_file
    from detect_secrets.settings import transient_settings
    root=folder(value)
    candidates=[];errors=[];scanned=0;skipped=0;used=0
    config={'plugins_used':[{'name':v} for v in ['PrivateKeyDetector','AWSKeyDetector','KeywordDetector','JwtTokenDetector']],
            'filters_used':[]}
    with _secret_lock,transient_settings(config):
        for path in walk_files(root):
            try:
                size=path.stat().st_size
                if size>1_000_000 or used+size>20_000_000:skipped+=1;continue
                with path.open('rb') as stream:
                    if b'\0' in stream.read(8192):skipped+=1;continue
                used+=size;scanned+=1
                for secret in scan_file(str(path)):
                    candidates.append({'file':str(path.relative_to(root)),'line':getattr(secret,'line_number',None),'type':secret.type,'value':'[MASQUÉ / REDACTED]'})
                    if len(candidates)>=100:break
            except OSError as exc:errors.append({'file':str(path.relative_to(root)),'error':type(exc).__name__})
            if len(candidates)>=100:break
    return {'directory':str(root),'files_scanned':scanned,'files_skipped':skipped,'findings':candidates,'errors':errors[:20],
            'scope':'4 détecteurs locaux ; aucun appel de validation / 4 local detectors, no verification calls',
            'limits':'1 000 fichiers examinés, 20 Mo lus, 100 résultats / 1,000 enumerated files, 20 MB read, 100 results',
            'note':'Candidats à vérifier ; aucune garantie d’exhaustivité / Candidates for review; not an exhaustive certification'}

def pdf_info(value):
    from pypdf import PdfReader
    path=file_path(value)
    reader=PdfReader(str(path))
    result={'file':str(path),'encrypted':reader.is_encrypted}
    if reader.is_encrypted:
        result['note']='PDF chiffré : contenu non lu / Encrypted PDF: content not read'
        return result
    result.update({'pages':len(reader.pages),'metadata':{str(k):str(v)[:1000] for k,v in (reader.metadata or {}).items()}})
    previews=[]
    for i,page in enumerate(reader.pages[:3],1):
        content=page.get_contents()
        if content is not None and len(content.get_data())>10_000_000:
            previews.append({'page':i,'text':'Page content exceeds 10 MB preview limit'});continue
        previews.append({'page':i,'width':float(page.mediabox.width),'height':float(page.mediabox.height),'text':(page.extract_text() or '')[:3000]})
    result['preview']=previews
    result['note']='Texte des 3 premières pages ; les scans nécessitent un OCR / First 3 pages; scans require OCR'
    return result

def image_open(path):
    from PIL import Image,ImageOps
    with Image.open(path) as image:
        if image.width*image.height>16_000_000:raise ValueError('Image limitée à 16 mégapixels / 16 MP image limit')
        return ImageOps.exif_transpose(image).convert('RGB')
def qr_read(value):
    import zxingcpp
    image=image_open(file_path(value))
    codes=zxingcpp.read_barcodes(image)
    return {'codes':[{'format':str(v.format),'text':v.text,'content_type':str(v.content_type),'position':str(v.position)} for v in codes[:50]],
            'count':len(codes),'note':'Contenu décodé ; aucun lien ouvert automatiquement / Decoded content; links are not opened automatically'}
def dhash(path):
    from PIL import Image
    image=image_open(path).convert('L').resize((9,8),Image.Resampling.LANCZOS)
    pixels=list(image.getdata())
    result=0
    for y in range(8):
        for x in range(8):result=(result<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
    return result
def similar_images(value):
    parts=required(value).split('|')
    if len(parts)==2:
        paths=[file_path(v.strip()) for v in parts]
        distance=(dhash(paths[0])^dhash(paths[1])).bit_count()
        return {'first':str(paths[0]),'second':str(paths[1]),'distance':distance,'bits':64,
                'note':'dHash : distance faible = structures proches, pas une probabilité / Low dHash distance indicates structural similarity, not probability'}
    if len(parts)!=1:raise ValueError('Dossier ou deux fichiers séparés par | / Directory or two file paths separated by |')
    root=folder(value)
    hashes=[];errors=[];candidate_count=0
    for path in walk_files(root):
        if path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'}:continue
        candidate_count+=1
        try:hashes.append((path,dhash(file_path(str(path)))))
        except Exception as exc:errors.append({'file':str(path.relative_to(root)),'error':type(exc).__name__})
        if candidate_count>=100:break
    matches=[]
    for i,(path,h) in enumerate(hashes):
        for other,h2 in hashes[i+1:]:
            distance=(h^h2).bit_count()
            if distance<=10:matches.append({'first':str(path.relative_to(root)),'second':str(other.relative_to(root)),'distance':distance})
    return {'directory':str(root),'images_compared':len(hashes),'threshold':10,'matches':sorted(matches,key=lambda d:d['distance'])[:100],
            'errors':errors[:20],'limits':'100 candidats parmi 1 000 fichiers / 100 image candidates among 1,000 files',
            'note':'Ressemblance dHash à vérifier visuellement / dHash candidates require visual review'}

def duplicates(value):
    root=folder(value)
    by_size=collections.defaultdict(list);errors=[];scanned=0;skipped=0
    for path in walk_files(root):
        try:
            size=path.stat().st_size
            if size>FILE_LIMIT:skipped+=1;continue
            by_size[size].append(path);scanned+=1
        except OSError as exc:errors.append({'file':str(path.relative_to(root)),'error':type(exc).__name__})
    groups=[];used=0
    for size,paths in by_size.items():
        if len(paths)<2:continue
        hashes=collections.defaultdict(list)
        for path in paths:
            if used+size>256_000_000:skipped+=1;continue
            try:
                before=path.stat();h=hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda:stream.read(65536),b''):h.update(block)
                after=path.stat();used+=size
                if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                    errors.append({'file':str(path.relative_to(root)),'error':'File changed while reading'});continue
                hashes[h.hexdigest()].append(str(path.relative_to(root)))
            except OSError as exc:errors.append({'file':str(path.relative_to(root)),'error':type(exc).__name__})
        for digest,paths in hashes.items():
            if len(paths)>1:groups.append({'sha256':digest,'size':size,'copies':len(paths),'extra_bytes':size*(len(paths)-1),'files':paths})
    return {'directory':str(root),'files_examined':scanned,'files_skipped':skipped,'groups':groups[:100],
            'extra_bytes':sum(v['extra_bytes'] for v in groups),'errors':errors[:20],
            'limits':'1 000 fichiers, 20 Mo par fichier, 256 Mo hachés / 1,000 files, 20 MB per file, 256 MB hashed',
            'note':'Aucune suppression ; copies identifiées par SHA-256 / No deletion; copies identified by SHA-256'}

def clean_url(value):
    from tools.core import url
    original=url(value)
    parts=urlsplit(original)
    fragments=parts.query.split('&') if parts.query else []
    keys=[unquote_plus(v.split('=',1)[0]).casefold() for v in fragments]
    signed=any(k in {'sig','signature','token','x-amz-signature','x-goog-signature'} for k in keys)
    removed=[];kept=[]
    for segment,key in zip(fragments,keys):
        if not signed and (key.startswith('utm_') or key in {'fbclid','gclid','dclid','msclkid','mc_cid','mc_eid'}):removed.append(key)
        else:kept.append(segment)
    cleaned=urlunsplit((parts.scheme,parts.netloc,parts.path,'&'.join(kept),parts.fragment))
    return {'original':original,'cleaned':cleaned,'removed_parameters':removed,'signed_link_preserved':signed,
            'note':'Règles conservatrices ; paramètres inconnus conservés / Conservative rules; unknown parameters preserved'}

def register(add):
    options=[
        ('OSINT','Public Username Search','Chercher un pseudo sur 6 services publics','Search a username on 6 public services','Pseudo / Username',usernames,True),
        ('OSINT','Phone Number Inspector','Analyser le plan de numérotation','Inspect numbering-plan metadata','+336... ou numéro | FR',phone),
        ('Domains & Infrastructure','Domain RDAP','Données publiques du registre de domaine','Public domain registration data','example.com',rdap,True),
        ('OSINT','Email Header Analyzer','Lire le trajet et les en-têtes déclarés','Inspect declared email headers and route','En-têtes collés ou chemin .eml',mail_headers),
        ('Domains & Infrastructure','Email Domain Audit','Examiner SPF et DMARC publiés','Inspect published SPF and DMARC','example.com',email_audit,True),
        ('Files & Media','Local Secret Audit','Repérer des secrets locaux, valeurs masquées','Find local secret candidates, values redacted','Chemin du dossier / Directory',secret_audit),
        ('Files & Media','PDF Inspector','Pages, métadonnées et aperçu du texte','Pages, metadata and text preview','Chemin .pdf / PDF file',pdf_info),
        ('Files & Media','QR Barcode Reader','Décoder les codes présents dans une image','Decode barcodes in an image','Chemin image / Image file',qr_read),
        ('Files & Media','Similar Image Finder','Comparer des variantes visuelles locales','Compare local visual variants','Dossier ou image1 | image2',similar_images),
        ('Files & Media','Duplicate File Finder','Regrouper les copies exactes sans supprimer','Group exact duplicates without deletion','Chemin du dossier / Directory',duplicates),
        ('Utilities','Tracking URL Cleaner','Retirer les paramètres de suivi connus','Remove known tracking parameters','https://example.com/?utm_source=test',clean_url),
    ]
    for option in options:add(*option)
