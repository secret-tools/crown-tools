"""Additional local utilities. No network requests or writes to user files."""
import ast
import base64
import csv
import html
import io
import ipaddress
import json
import math
import re
import secrets
import statistics
import string
import unicodedata
import urllib.parse
from lib.constants import resolve_input_path
from pathlib import Path
import xml.etree.ElementTree as ET


def text(value):
    if not value.strip():
        raise ValueError('Entrée requise / Input required')
    if len(value) > 200000:
        raise ValueError('Entrée limitée à 200 000 caractères / Input limit: 200,000 characters')
    return value


def lines(value):
    return text(value).splitlines()


def deduplicate(value):
    original = lines(value)
    unique = list(dict.fromkeys(original))
    return {'input_lines': len(original), 'removed': len(original)-len(unique), 'result': '\n'.join(unique)}


def cases(value):
    value = text(value)
    return {'lower': value.lower(), 'upper': value.upper(), 'title': value.title(), 'casefold': value.casefold()}


def slug(value):
    normalized = unicodedata.normalize('NFKD', text(value)).encode('ascii', 'ignore').decode()
    return {'slug': re.sub(r'[^a-z0-9]+', '-', normalized.lower()).strip('-')}


def unicode_info(value):
    value = text(value)
    return {'characters': [{'character': c, 'codepoint': f'U+{ord(c):04X}',
                            'name': unicodedata.name(c, 'UNNAMED'), 'category': unicodedata.category(c)}
                           for c in value[:200]], 'total': len(value), 'shown': min(len(value),200)}


def csv_json(value):
    value = text(value)
    try:dialect=csv.Sniffer().sniff(value[:8192],delimiters=',;\t')
    except csv.Error:
        if any(delimiter in value for delimiter in ',;\t'):raise ValueError('CSV incohérent / Inconsistent CSV')
        dialect=csv.excel
    reader = csv.DictReader(io.StringIO(value), dialect=dialect)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('En-têtes CSV absents ou dupliqués / Missing or duplicate CSV headers')
    rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError('Nombre de colonnes incohérent / Inconsistent column count')
    return json.dumps(rows, ensure_ascii=False, indent=2)


def json_csv(value):
    rows = json.loads(text(value))
    if not isinstance(rows,list) or not rows or not all(isinstance(r,dict) for r in rows):
        raise ValueError('Liste JSON non vide d’objets requise / Nonempty JSON array of objects required')
    fields = list(dict.fromkeys(k for r in rows for k in r))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    return output.getvalue()


def xml_format(value):
    value = text(value)
    if '<!DOCTYPE' in value.upper() or '<!ENTITY' in value.upper():
        raise ValueError('DTD et entités non prises en charge / DTD and entities unsupported')
    tree = ET.fromstring(value)
    ET.indent(tree,space='  ')
    return ET.tostring(tree,encoding='unicode')


def base_convert(value):
    raw = text(value).strip()
    number = int(raw, 0) if raw.lower().lstrip('-').startswith(('0x','0b','0o')) else int(raw,10)
    if number.bit_length() > 4096:
        raise ValueError('Entier trop grand / Integer too large')
    return {'decimal': str(number), 'hexadecimal':hex(number), 'binary':bin(number), 'octal':oct(number)}


def calculator(value):
    expression = text(value).strip()
    if len(expression)>300:
        raise ValueError('Expression trop longue / Expression too long')
    tree = ast.parse(expression,mode='eval')
    if sum(1 for _ in ast.walk(tree))>100:
        raise ValueError('Expression trop complexe / Expression too complex')
    operators = {ast.Add:lambda a,b:a+b, ast.Sub:lambda a,b:a-b, ast.Mult:lambda a,b:a*b,
                 ast.Div:lambda a,b:a/b, ast.FloorDiv:lambda a,b:a//b, ast.Mod:lambda a,b:a%b,
                 ast.Pow:lambda a,b:a**b}
    def evaluate(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            result=node.value
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            result=evaluate(node.operand)*(-1 if isinstance(node.op,ast.USub) else 1)
        elif isinstance(node,ast.BinOp) and type(node.op) in operators:
            a,b=evaluate(node.left),evaluate(node.right)
            if isinstance(node.op,ast.Pow) and abs(b)>100:
                raise ValueError('Exposant limité à 100 / Exponent limit: 100')
            result=operators[type(node.op)](a,b)
        else:
            raise ValueError('Opérations arithmétiques uniquement / Arithmetic operations only')
        if type(result) not in (int,float) or abs(result)>1e100 or not math.isfinite(result):
            raise ValueError('Résultat hors limites / Result outside limits')
        return result
    return {'expression':expression, 'result':evaluate(tree.body)}


def number_stats(value):
    values = [float(x) for x in re.split(r'[,;\s]+',text(value).strip())]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Nombres finis requis / Finite numbers required')
    return {'count':len(values),'sum':math.fsum(values),'minimum':min(values),'maximum':max(values),
            'mean':statistics.mean(values),'median':statistics.median(values),
            'population_deviation':statistics.pstdev(values)}


def cidr_overlap(value):
    parts = text(value).split()
    if len(parts)!=2:
        raise ValueError('Deux réseaux CIDR requis / Two CIDR networks required')
    a,b = [ipaddress.ip_network(p,strict=False) for p in parts]
    return {'first':str(a),'second':str(b),'same_ip_version':a.version==b.version,
            'overlap':a.overlaps(b) if a.version==b.version else False}


def file_info(value):
    path = resolve_input_path(text(value))
    if not path.is_file():
        raise ValueError('Fichier introuvable / File not found')
    stat=path.stat()
    from datetime import datetime,timezone
    return {'name':path.name,'path':str(path.resolve()),'extension':path.suffix,
            'bytes':stat.st_size,'modified_utc':datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat()}


def file_compare(value):
    paths = [resolve_input_path(p) for p in text(value).split('|')]
    if len(paths)!=2 or not all(p.is_file() for p in paths):
        raise ValueError('Deux chemins de fichiers séparés par | requis / Two file paths separated by | required')
    def digest(path):
        import hashlib
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    hashes=[digest(p) for p in paths]
    return {'first':str(paths[0]),'second':str(paths[1]),'first_sha256':hashes[0],'second_sha256':hashes[1],
            'identical_content':hashes[0]==hashes[1]}


def random_token(value):
    size=int(value.strip() or '32')
    if not 16<=size<=128:
        raise ValueError('16 à 128 octets requis / 16–128 bytes required')
    return {'bytes':size,'token':secrets.token_urlsafe(size)}


def register(add):
    entries = [
        ('Data & Encoding','HTML Escape','Encoder les caractères HTML','Escape HTML characters','<p>Hello</p>',lambda v:html.escape(text(v))),
        ('Data & Encoding','HTML Unescape','Décoder les entités HTML','Decode HTML entities','&lt;p&gt;',lambda v:html.unescape(text(v))),
        ('Data & Encoding','URL Encode','Encoder les caractères URL','Encode URL characters','Texte / Text',lambda v:urllib.parse.quote(text(v),safe='')),
        ('Data & Encoding','Base64 URL Encode','Encoder en Base64 URL','Encode URL-safe Base64','Texte / Text',lambda v:base64.urlsafe_b64encode(text(v).encode()).decode()),
        ('Data & Encoding','CSV to JSON','Convertir CSV vers JSON','Convert CSV to JSON','name,age / CSV multiligne',csv_json),
        ('Data & Encoding','JSON to CSV','Convertir JSON vers CSV','Convert JSON to CSV','[{"name":"Crown"}]',json_csv),
        ('Data & Encoding','XML Format','Valider et indenter XML','Validate and format XML','<root><item>1</item></root>',xml_format),
        ('Data & Encoding','Number Base Converter','Convertir les bases numériques','Convert numeric bases','42 / 0x2A / 0b101010',base_convert),
        ('Utilities','Text Case Converter','Changer la casse du texte','Convert text case','Texte / Text',cases),
        ('Utilities','Slug Generator','Créer un identifiant de texte','Create a text slug','Titre / Title',slug),
        ('Utilities','Line Deduplicator','Supprimer les lignes dupliquées','Remove duplicate lines','Texte multiligne / Multiline text',deduplicate),
        ('Utilities','Line Sorter','Trier les lignes de texte','Sort text lines','Texte multiligne / Multiline text',lambda v:'\n'.join(sorted(lines(v),key=str.casefold))),
        ('Utilities','Unicode Inspector','Inspecter les caractères Unicode','Inspect Unicode characters','Texte / Text',unicode_info),
        ('Utilities','Calculator','Calculer une expression','Calculate an expression','(12 + 8) * 3',calculator),
        ('Utilities','Number Statistics','Statistiques de nombres','Number statistics','1 2 3 4 5',number_stats),
        ('Utilities','Random Token','Générer un jeton aléatoire local','Generate a local random token','16–128 bytes (default: 32)',random_token),
        ('IP & Network','CIDR Overlap','Comparer deux plages réseau','Compare two network ranges','10.0.0.0/24 10.0.0.0/16',cidr_overlap),
        ('IP & Network','IPv6 Expander','Développer une adresse IPv6','Expand an IPv6 address','2001:db8::1',lambda v:{'compressed':str(ipaddress.IPv6Address(text(v).strip())),'expanded':ipaddress.IPv6Address(text(v).strip()).exploded}),
        ('Files & Media','File Details','Informations locales du fichier','Local file details','Chemin du fichier / File path',file_info),
        ('Files & Media','File Compare','Comparer le contenu de deux fichiers','Compare two file contents','C:/first.txt | C:/second.txt',file_compare),
    ]
    for entry in entries:add(*entry)
