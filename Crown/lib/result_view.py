"""Readable, bounded rendering for integrated tool results."""
import json
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax


def render_result(output, title, accent, translate=lambda s:s):
    if isinstance(output,str):
        lexer={'JSON Format':'json','JSON Minify':'json','CSV to JSON':'json','TOML to JSON':'json','XML Format':'xml','Text Diff':'diff','JSON Diff':'diff'}.get(title)
        content=output[:120000] + ('\n…' if len(output)>120000 else '')
        body=Syntax(content,lexer,theme='ansi_dark',background_color='default',word_wrap=True,line_numbers=True) if lexer else Text(content)
        return Panel(body,title=Text(title),border_style=accent,padding=(1,1))
    def label(value):
        return str(value).replace('_',' ').strip().capitalize()
    def cell(value):
        if value is None:return Text('—',style='dim')
        if isinstance(value,bool):return Text('✓ Oui / Yes' if value else '× Non / No',style='green' if value else 'yellow')
        if isinstance(value,(dict,list)):
            value=json.dumps(value,ensure_ascii=False,default=str,indent=2)
        value=str(value)
        return Text(value[:6000] + ('\n…' if len(value)>6000 else ''))
    def table(data):
        result=Table(box=box.SIMPLE_HEAD,expand=True,border_style=accent,show_header=False,padding=(0,1))
        result.add_column(style=accent,ratio=1)
        result.add_column(ratio=3,overflow='fold')
        for key,value in list(data.items())[:100]:result.add_row(Text(label(key)),cell(value))
        if len(data)>100:result.add_row(Text('…'),Text(f'{len(data)-100} additional fields'))
        return result
    def listing(values):
        if values and all(isinstance(v,dict) for v in values):
            columns=list(dict.fromkeys(str(k) for row in values for k in row))[:8]
            result=Table(box=box.SIMPLE_HEAD,expand=True,border_style=accent,header_style='bold '+accent,padding=(0,1))
            for key in columns:result.add_column(label(key),overflow='fold')
            for row in values[:50]:result.add_row(*(cell(row.get(key)) for key in columns))
            if len(values)>50:result.caption=f'50 / {len(values)} · aperçu / preview'
            if len(set(k for row in values for k in row))>8:result.caption=(result.caption or '')+' · colonnes limitées à 8 / up to 8 columns'
            return result
        result=Table(box=None,show_header=False,expand=True,padding=(0,1))
        result.add_column(style=accent,width=4)
        result.add_column(overflow='fold')
        for index,value in enumerate(values[:50],1):result.add_row(str(index),cell(value))
        if len(values)>50:result.caption=f'50 / {len(values)} · aperçu / preview'
        return result if values else Text(translate('Aucun résultat.'))
    if isinstance(output,dict):
        sections=[]
        summary={key:value for key,value in output.items() if not isinstance(value,(dict,list))}
        if summary:sections.append(table(summary))
        for key,value in output.items():
            if isinstance(value,dict):
                sections.append(Panel(table(value),title=Text(label(key)),border_style=accent))
            elif isinstance(value,list):
                sections.append(Panel(listing(value),title=Text(f'{label(key)} · {len(value)}'),border_style=accent))
        body=Group(*sections) if sections else Text(translate('Aucun résultat.'))
    elif isinstance(output,list):
        body=listing(output)
    else:body=cell(output)
    return Panel(body,title=Text(title),border_style=accent,padding=(1,1),expand=True)
