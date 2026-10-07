"""Présentation exclusivement : aucun execute() de l'application initiale modifié."""
from __future__ import annotations
import json
import zipfile
import math
import os
import colorsys
from pathlib import Path
import time
from datetime import datetime

import pyfiglet
import psutil
from rich.text import Text
from textual import events
from textual.color import Color
from textual.content import Content
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll, Grid
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Label, ListView, ListItem, TextArea
from .boot import NeonBoot
from .dark import DarkConfirmation, DarkAccess, DarkConstruction
from .vip import VipPicker, VipArrival, load_pack, execute as execute_vip
import zipfile
from types import SimpleNamespace
from .config import PROFILE_PATH, read_profile, write_profile, read_vip, write_vip
from .setup import ProfileScreen
from .localization import translate, EN, LANGUAGES
from tools.core import TOOLS as EXTRA_TOOLS
from tools.catalog_policy import RETIRED_TOOLS

from .constants import APP_DIR as ROOT, STYLES_DIR, INPUT_DIR
from .result_export import save_result
from .tools import legacy
from .pages import CATEGORIES, CAT_LABELS, CAT_ICONS, SHORT, CAT_ART, TOOLS

def compact_qr(matrix):
    """Même matrice QR ; deux modules verticaux par cellule terminal."""
    width=len(matrix[0])+6
    padded=[[False]*width for _ in range(3)]
    padded += [[False]*3+list(row)+[False]*3 for row in matrix]
    padded += [[False]*width for _ in range(3)]
    if len(padded)%2:padded.append([False]*width)
    lines=[]
    for y in range(0,len(padded),2):
        lines.append(''.join(' ▀▄█'[int(padded[y][x])+2*int(padded[y+1][x])] for x in range(width)))
    return Text('\n'.join(lines),style='#080808 on #ffffff',no_wrap=True,overflow='crop')

legacy._qr_to_text=compact_qr

from .themes import PALETTES

for key,(_,accent,secondary,bg,surface,line,fg,dim,gold) in PALETTES.items():
    legacy.THEMES[key]={'crown-bg':bg,'crown-bg-alt':surface,'crown-border':line,'crown-accent':accent,'crown-accent-2':secondary,'crown-cyan':gold,'crown-text':fg,'crown-text-dim':dim,'crown-success':'#8bd5ae','crown-warning':gold,'crown-error':'#ff6378'}


def color(app,key):
    if app.active_theme=='rainbow' and not app.accent and key in ('crown-accent','crown-accent-2'):
        accent=getattr(app,'rainbow_accent','#ff506a')
        return accent if key=='crown-accent' else blend(accent,'#100d13',.32)
    if getattr(app,'accent','') and key in ('crown-accent','crown-accent-2'):
        return app.accent if key=='crown-accent' else blend(app.accent,'#100d13',.32)
    return legacy.THEMES[app.active_theme][key]
def blend(a,b,t):
    aa=tuple(int(a[i:i+2],16) for i in (1,3,5));bb=tuple(int(b[i:i+2],16) for i in (1,3,5))
    return '#'+''.join(f'{round(x+(y-x)*max(0,min(1,t))):02x}' for x,y in zip(aa,bb))

class VipZoneButton(Button):
    """An animated dark portal drawn cell by cell, with native button controls."""
    def on_mount(self):
        self.styles.line_pad=0
        self.phase=0.;self.engagement=0.;self.last_tick=time.monotonic()
        self.set_interval(1/24,self.aura_frame)

    def aura_frame(self):
        now=time.monotonic();delta=min(.1,now-self.last_tick);self.last_tick=now
        if self.app.screen is not self.screen:return
        target=float(self.is_mouse_over or self.has_focus)
        if self.app.motion:
            self.phase+=delta
            self.engagement+=(target-self.engagement)*.22
        else:self.engagement=target
        self.refresh()

    def render(self):
        width=max(4,self.content_size.width)
        phase=getattr(self,'phase',0.)
        engagement=getattr(self,'engagement',0.)
        pulse=(.5-.5*math.cos(phase*math.tau/4)) if self.app.motion else .35
        vip=bool(self.app.vip_pack)
        violet=blend('#a62039' if vip else '#ad8544','#ff9aab' if vip else '#f4d997',engagement)
        head=(phase/3.8%1)*(width*2+2)
        title='◇  VIP ZONE  ↗' if width>=19 else 'VIP ZONE'
        if self.app.vip_pack:title='◆  VIP ON  ◆' if width>=15 else 'VIP ON'
        inner=width-2
        title=title[:inner].center(inner)
        lines=['╭'+'─'*inner+'╮','│'+title+'│','╰'+'─'*inner+'╯']
        out=Text(no_wrap=True,overflow='crop')
        for y,line in enumerate(lines):
            for x,char in enumerate(line):
                edge=y!=1 or x in (0,width-1)
                perimeter=x if y==0 else width+1+(width-1-x)
                distance=min(abs(perimeter-head),width*2+2-abs(perimeter-head))
                flare=max(0,1-distance/5) if self.app.motion else .15
                if edge:
                    ink=blend('#49202a' if vip else '#49391f',violet,.35+.3*pulse+.35*engagement)
                    ink=blend(ink,'#ffe3e9' if vip else '#fff0c5',flare*.9)
                else:
                    ink=blend('#ff9aab' if vip else '#dfcc9f','#fff4f7' if vip else '#fff4d9',engagement)
                    if char in '◇↗':ink=blend(violet,'#fff0c5',engagement)
                depth=max(0,1-abs(x-(width-1)/2)/(width/2))
                background=blend('#10080c' if vip else '#0c0a07','#6b172b' if vip else '#51401d',depth*(.18+.28*engagement))
                out.append(char,style=('bold ' if not edge else '')+ink+' on '+background)
            if y<2:out.append('\n')
        return Content.from_rich_text(out)

class Wordmark(Static):
    def on_mount(self):
        self.phase=0.;self.logo=pyfiglet.figlet_format('CROWN',font='ansi_shadow').rstrip('\n')
        self.set_interval(.12,self.tick)
    def tick(self):
        if self.app.motion and self.app.screen is self.screen:
            self.phase+=.12;self.refresh()
    def render(self):
        accent=color(self.app,'crown-accent');dim=color(self.app,'crown-accent-2');fg=color(self.app,'crown-text')
        if self.size.width<38:
            return Text('C R O W N  /  T O O L S',style='bold '+accent)
        lines=self.logo.splitlines();width=max(map(len,lines));out=Text()
        for y,line in enumerate(lines):
            for x,ch in enumerate(line):
                gleam=max(0,1-abs((x-self.phase*6)%(width+20)-8)/7)*.65 if self.app.motion else 0
                out.append(ch,style=blend(blend(accent,dim,y/max(1,len(lines)-1)*.5),fg,gleam))
            if y<len(lines)-1:out.append('\n')
        return out

class CompactSignature(Static):
    """Custom geometric lettering: eight pixel rows packed into four terminal rows."""
    GLYPHS=(
        ('011111','111111','110000','110000','110000','110000','111111','011111'),
        ('111110','111111','110011','110011','111110','111100','110110','110011'),
        ('011110','111111','110011','110011','110011','110011','111111','011110'),
        ('11000011','11000011','11000011','11011011','11011011','11011011','01111110','01100110'),
        ('110011','111011','111011','111111','111111','110111','110111','110011'),
    )
    @classmethod
    def logo_lines(cls,width):
        base_width=sum(len(glyph[0]) for glyph in cls.GLYPHS)+2*(len(cls.GLYPHS)-1)
        if width<base_width:
            label='CROWN TOOLS' if width>=10 else 'CROWN'
            return ['',label[:max(0,width)],'','']
        scale=2 if width>=base_width*2 else 1
        pixels=['00'.join(glyph[y] for glyph in cls.GLYPHS) for y in range(8)]
        lines=[''.join(' ▀▄█'[int(top)+2*int(bottom)]*scale for top,bottom in zip(pixels[y],pixels[y+1])) for y in range(0,8,2)]
        if width>=base_width*scale+13:
            lines=[line+('    T O O L S' if y==1 else '') for y,line in enumerate(lines)]
        return lines
    def on_mount(self):
        self.phase=0.;self.last_tick=time.monotonic()
        self.set_interval(1/24,self.tick)
    def tick(self):
        now=time.monotonic();elapsed=min(.1,now-self.last_tick);self.last_tick=now
        if self.app.motion and self.app.screen is self.screen:
            self.phase+=elapsed;self.refresh()
    def render(self):
        lines=self.logo_lines(self.size.width)
        logo_width=max(map(len,lines),default=0)
        text=Text(no_wrap=True,overflow='crop')
        accent=color(self.app,'crown-accent');fg=color(self.app,'crown-text')
        for y,line in enumerate(lines):
            for x,char in enumerate(line):
                # A highlight crosses the solid letter faces without moving the logo.
                sweep=(self.phase%4.6)/2.2
                head=-10+sweep*(logo_width+20)
                gleam=max(0,1-abs(x-head)/10)**1.2 if self.app.motion and sweep<1.2 else 0
                base=blend(accent,fg,.24-y*.07)
                text.append(char,style=blend(base,fg,gleam*.8))
            if y<len(lines)-1:text.append('\n')
        return text

class SignatureRail(Static):
    def on_mount(self):
        self.phase=0.;self.last_tick=time.monotonic();self.set_interval(1/24,self.tick)
    def tick(self):
        now=time.monotonic();elapsed=min(.1,now-self.last_tick);self.last_tick=now
        if self.app.motion and self.app.screen is self.screen:
            self.phase+=elapsed;self.refresh()
    def render(self):
        width=max(1,self.size.width)
        out=Text(no_wrap=True)
        for x in range(width):
            strength=max(0,1-x/max(1,width*.55))**2
            if self.app.motion:
                head=((self.phase%5.2)/3.7)*(width+20)-10
                strength=max(strength,max(0,1-abs(x-head)/11)**1.5)
            out.append('━' if x<3 or strength>.55 else '─',style=blend(color(self.app,'crown-border'),color(self.app,'crown-accent'),strength))
        return out

class Orbital(Static):
    """Sculpture de particules braille, purement décorative et calculée localement."""
    def on_mount(self):
        self.phase=0.;self.set_interval(.14,self.tick)
    def tick(self):
        if self.app.motion and self.app.screen is self.screen:
            self.phase+=.045;self.refresh()
    def render(self):
        w=max(8,self.size.width);h=max(3,self.size.height);pw=w*2;ph=h*4
        dots={};brightness={};lut=((1,8),(2,16),(4,32),(64,128))
        def plot(x,y,level):
            x=int(x);y=int(y)
            if 0<=x<pw and 0<=y<ph:
                key=(x//2,y//4);dots[key]=dots.get(key,0)|lut[y%4][x%2];brightness[key]=max(level,brightness.get(key,0))
        for ring in range(3):
            tilt=(-.8,.8,0.05)[ring];r=min(pw*.42,ph*.6)
            for i in range(230):
                t=i/230*math.tau
                xx=math.cos(t)*r;yy=math.sin(t)*r*.4
                x=xx*math.cos(tilt)-yy*math.sin(tilt);y=xx*math.sin(tilt)+yy*math.cos(tilt)
                phase=(t-self.phase-ring*1.7)%math.tau
                plot(pw/2+x,ph/2+y*.65,.3+.7*max(0,1-phase/1.5))
        for k in range(28):
            t=k/28*math.tau+self.phase*.3
            plot(pw/2+math.cos(t)*5,ph/2+math.sin(t)*4,1)
        out=Text();accent=color(self.app,'crown-accent');line=color(self.app,'crown-border')
        for y in range(h):
            for x in range(w):
                key=(x,y);out.append(chr(0x2800+dots[key]) if key in dots else ' ',style=blend(line,accent,brightness.get(key,0)))
            if y<h-1:out.append('\n')
        return out

class Topline(Static):
    def on_mount(self):self.set_interval(1,self.refresh)
    def render(self):
        a=color(self.app,'crown-accent');d=color(self.app,'crown-text-dim');f=color(self.app,'crown-text')
        text=Text('  ◈ ',style=a);text.append('CROWN',style='bold '+f);text.append(' / TOOLS',style=d)
        suffix=self.app.username+'  /  '+datetime.now().strftime('%H:%M')+'  '
        text.append(' '*max(2,self.size.width-len(text.plain)-len(suffix)));text.append(suffix,style=d)
        return text

class Telemetry(Static):
    def on_mount(self):
        self.cpu=[0.]*16;self.mem=0.;psutil.cpu_percent();self.set_interval(1,self.tick);self.tick()
    def tick(self):
        self.cpu=(self.cpu+[psutil.cpu_percent()])[-16:];self.mem=psutil.virtual_memory().percent;self.refresh()
    def render(self):
        a=color(self.app,'crown-accent');d=color(self.app,'crown-text-dim');f=color(self.app,'crown-text')
        out=Text('SYSTÈME LOCAL\n\n',style=d)
        out.append('CPU  ',style=d);out.append(f'{self.cpu[-1]:5.1f}%\n',style=f)
        out.append(''.join('▁▂▃▄▅▆▇█'[min(7,int(v/100*8))] for v in self.cpu)+'\n\n',style=a)
        out.append('RAM  ',style=d);out.append(f'{self.mem:5.1f}%\n',style=f)
        n=round(self.mem/100*16);out.append('━'*n,style=a);out.append('━'*(16-n),style=color(self.app,'crown-border'))
        return out

class CommunityLink(Static,can_focus=True):
    BINDINGS=[Binding('enter','open',show=False),Binding('space','open',show=False)]
    def __init__(self,service,path,url,**kwargs):
        super().__init__(**kwargs);self.service=service;self.path=path;self.url=url
    def render(self):
        return Text(f'{self.service:<10}{self.path}',no_wrap=True,overflow='ellipsis')
    def action_open(self):self.app.open_url(self.url)
    def on_click(self):self.focus();self.action_open()

class ModuleCard(Static,can_focus=True):
    BINDINGS=[Binding('enter','open','Ouvrir',show=False),Binding('right','next_card',show=False),Binding('left','previous_card',show=False),Binding('down','down_card',show=False),Binding('up','up_card',show=False)]
    class Picked(Message):
        def __init__(self,card):super().__init__();self.card=card
    def __init__(self,cat,num,name,index):
        super().__init__(id=f'module-{index}',classes='module-card');self.cat=cat;self.num=num;self.tool_name=name;self.index=index;self.hovered=False;self.glow=0.;self.reveal_at=None;self.motion_style=None
        self.tooltip=None
        self.is_premium = '[PREMIUM]' in name or 'PREMIUM' in name.upper() or name in getattr(self.app, 'premium_tools', set())
        if self.is_premium:
            self.add_class('premium-card')
    def on_mount(self):self.tooltip=self.app.tr(self.app.descriptions[self.tool_name])
    def on_focus(self):self.post_message(self.Picked(self));self.scroll_visible(animate=self.app.motion)
    def on_enter(self):self.hovered=True
    def on_leave(self):self.hovered=False
    def motion_frame(self,now,enabled):
        target=1. if self.hovered or self.has_focus else 0.
        self.glow=target if not enabled else self.glow+(target-self.glow)*.27
        if abs(self.glow-target)<.005:self.glow=target
        opacity=1.
        if self.reveal_at is not None and enabled:
            progress=max(0.,min(1.,(now-self.reveal_at)/.22))
            opacity=.25+.75*(1-(1-progress)**3)
            if progress>=1:self.reveal_at=None
        elif not enabled:self.reveal_at=None
        state=(round(self.glow,3),round(opacity,3),self.app.active_theme,color(self.app,'crown-accent'),getattr(self,'is_premium',False))
        if state==self.motion_style:return
        self.motion_style=state
        if getattr(self, 'is_premium', False):
            self.styles.border=('round',blend('#8a6d1b','#ffd700',self.glow))
            self.styles.background=Color.parse(blend('#130f04','#2b2106',self.glow*.35))
        else:
            self.styles.border=('round',blend(color(self.app,'crown-border'),color(self.app,'crown-accent'),self.glow))
            self.styles.background=Color.parse(blend(color(self.app,'crown-bg-alt'),color(self.app,'crown-accent'),self.glow*.18))
        self.styles.opacity=state[1]
    def on_click(self):self.focus();self.action_open()
    def action_open(self):self.app.open_tool(self.cat,self.tool_name)
    def action_next_card(self):self.app.move_card(self,1)
    def action_previous_card(self):self.app.move_card(self,-1)
    def action_down_card(self):self.app.move_card(self,self.app.columns)
    def action_up_card(self):self.app.move_card(self,-self.app.columns)
    def render(self):
        a=color(self.app,'crown-accent');d=color(self.app,'crown-text-dim');f=color(self.app,'crown-text')
        title,subtitle=self.app.short[self.tool_name];title=self.app.tr(title);subtitle=self.app.tr(subtitle);width=max(12,self.content_size.width)
        out=Text(no_wrap=True,overflow='ellipsis')
        if getattr(self, 'is_premium', False):
            out.append((f'{self.index+1:02}' if self.app.category=='all' else self.num)+' ',style='bold #ffd700')
            clean_title = title.replace('[PREMIUM]', '').strip()
            out.append(clean_title[:max(1,width-10)]+' ',style='bold #ffffff')
            out.append('★ VIP\n',style='bold #ffd700')
            out.append((subtitle[:width-1]+'…' if len(subtitle)>width else subtitle)+'\n',style='#e6c200')
            out.append(self.app.tr(self.app.cat_labels.get(self.cat,self.cat.upper()))+' · PREMIUM',style='bold #ffa500')
            return out
        if self.cat == 'all':
            out.append((f'{self.index+1:02}')+' ',style='bold #ff3452')
            out.append(title[:max(1,width-10)]+' ',style='bold #ffffff')
            out.append('◈ HUB\n',style='bold #ff3452')
            out.append((subtitle[:width-1]+'…' if len(subtitle)>width else subtitle)+'\n',style=d)
            out.append(self.app.tr('HOME · ACCÈS RAPIDE'),style='bold #ffacbb')
            return out
        out.append((f'{self.index+1:02}' if self.app.category=='all' else self.num)+' ',style=a)
        out.append(title[:max(1,width-3)]+'\n',style='bold '+f)
        out.append((subtitle[:width-1]+'…' if len(subtitle)>width else subtitle)+'\n',style=d)
        out.append(self.app.tr(self.app.cat_labels.get(self.cat,self.cat.upper())),style=color(self.app,'crown-accent-2'))
        return out

class Inspector(Vertical):
    def compose(self):
        yield Static('MODULE / FOCUS',id='inspector-tag')
        yield Orbital(id='detail-orbit')
        yield Static('01',id='detail-number')
        yield Static('WEB LOOKUP',id='detail-name')
        yield Static(self.app.descriptions[self.app.catalog[0][2]],id='detail-description')
        yield Static('IP & RÉSEAU',id='detail-meta')
        yield Button('OUVRIR LE MODULE  ↗',id='detail-open')
        yield Static('La précision commence\npar le bon outil.',id='detail-caption')
    def select(self,card):
        is_prem = getattr(card, 'is_premium', False)
        if card.cat == 'all':
            self.query_one('#detail-number',Static).update(Text(f"{card.num} ◈ HUB", style="bold #ffd700" if is_prem else "bold #ff3452"))
            self.query_one('#detail-name',Static).update(Text(self.app.tr(self.app.short[card.tool_name][0]), style="bold #ffffff"))
            self.query_one('#detail-description',Static).update(Text(self.app.tr(self.app.descriptions[card.tool_name]), style="#f6e9ed"))
            self.query_one('#detail-meta',Static).update(Text(self.app.tr("HOME · HUB OFFICIEL"), style="bold #ffacbb"))
            btn = self.query_one('#detail-open',Button)
            if card.tool_name in ('Discord', 'Telegram'):
                btn.label = self.app.tr('REJOINDRE  ↗')
            elif card.tool_name == 'Zone VIP':
                btn.label = self.app.tr('ACTIVER VIP  ★')
            elif is_prem:
                btn.label = 'DÉBLOQUER (PREMIUM) ★'
            elif card.tool_name == 'Mode Standard':
                btn.label = self.app.tr('QUITTER LE VIP  ←')
            else:
                btn.label = self.app.tr('OUVRIR L’OPTION  ↗')
            btn.styles.background = '#8a6d1b' if is_prem else color(self.app, 'crown-accent-2')
            btn.styles.color = '#ffffff'
            return
        if is_prem:
            self.query_one('#detail-number',Static).update(Text(f"{card.num} ★ PREMIUM", style="bold #ffd700"))
            self.query_one('#detail-name',Static).update(Text(self.app.tr(self.app.short[card.tool_name][0]), style="bold #ffffff"))
            self.query_one('#detail-description',Static).update(Text(self.app.tr(self.app.descriptions[card.tool_name]), style="#e6c200"))
            self.query_one('#detail-meta',Static).update(Text(self.app.tr(self.app.cat_labels.get(card.cat, card.cat.upper())) + " · ACCÈS VIP", style="bold #ffa500"))
            btn = self.query_one('#detail-open',Button)
            btn.label = 'DÉBLOQUER (PREMIUM) ★'
            btn.styles.background = '#8a6d1b'
            btn.styles.color = '#ffffff'
        else:
            self.query_one('#detail-number',Static).update(card.num)
            self.query_one('#detail-name',Static).update(self.app.tr(self.app.short[card.tool_name][0]))
            self.query_one('#detail-description',Static).update(self.app.tr(self.app.descriptions[card.tool_name]))
            self.query_one('#detail-meta',Static).update(self.app.tr(self.app.cat_labels.get(card.cat, card.cat.upper())))
            btn = self.query_one('#detail-open',Button)
            btn.label = 'OUVRIR LE MODULE  ↗'
            btn.styles.background = color(self.app, 'crown-accent-2')
            btn.styles.color = color(self.app, 'crown-text')

class BootScreen(ModalScreen):
    BINDINGS=[Binding('enter','skip',show=False),Binding('escape','skip',show=False)]
    def compose(self):
        yield NeonBoot(id='neon-canvas')
        yield Static('ENTRÉE  /  PASSER L’INTRODUCTION',id='boot-skip')
    def on_mount(self):self.done=False;self.app.localize(self)
    def action_skip(self):
        if not self.done:self.done=True;self.dismiss()

class AppearanceScreen(ModalScreen):
    def on_mount(self):self.app.localize(self)
    BINDINGS=[Binding('escape','close',show=False)]
    def compose(self):
        with Vertical(id='appearance-box'):
            yield Static('ATELIER / APPARENCE',classes='eyebrow')
            yield Static('Choisis ton atmosphère.',id='appearance-title')
            for key,(name,*_) in PALETTES.items():yield Button(('●  ' if self.app.active_theme==key else '○  ')+name,id='theme-'+key)
            yield Button('ANIMATIONS  /  '+('ACTIVES' if self.app.motion else 'PAUSE'),id='motion-toggle')
            yield Button('PROFIL / LANGUE / COULEUR',id='edit-profile')
            yield Button('REJOUER L’INTRODUCTION',id='replay-boot')
            yield Button('RETOUR  /  ÉCHAP',id='appearance-close')
    def on_button_pressed(self,event):
        key=event.button.id
        if key.startswith('theme-'):
            self.app.apply_theme(key[6:])
            for k,(name,*_) in PALETTES.items():self.query_one('#theme-'+k,Button).label=('●  ' if k==self.app.active_theme else '○  ')+name
        elif key=='motion-toggle':
            self.app.action_motion();event.button.label=self.app.tr('ANIMATIONS  /  '+('ACTIVES' if self.app.motion else 'PAUSE'))
        elif key=='edit-profile':self.dismiss();self.app.call_after_refresh(self.app.action_profile)
        elif key=='replay-boot':self.dismiss();self.app.call_after_refresh(self.app.action_intro)
        else:self.dismiss()
    def action_close(self):self.dismiss()

class SearchScreen(ModalScreen):
    BINDINGS=[Binding('escape','close',show=False),Binding('down','next',show=False),Binding('up','previous',show=False)]
    def compose(self):
        with Vertical(id='search-box'):
            yield Static('ACCÈS RAPIDE  /  CTRL K',classes='eyebrow')
            yield Input(placeholder='Un outil, une idée…',id='search-input')
            yield ListView(id='search-results')
            yield Static('↑ ↓  NAVIGUER     ENTRÉE  OUVRIR     ÉCHAP  FERMER',classes='search-hint')
    async def on_mount(self):self.app.localize(self);self.seq=0;await self.populate('');self.query_one(Input).focus()
    async def populate(self,value):
        self.seq+=1;seq=self.seq;lv=self.query_one(ListView);await lv.clear()
        if seq!=self.seq:return
        for cat,num,name in self.app.catalog:
            if value.casefold() in (name+' '+self.app.descriptions[name]+' '+self.app.tr(self.app.descriptions[name])+' '+self.app.cat_labels[cat]+' '+cat).casefold():
                await lv.append(ListItem(Label(Text(f'{num}  {self.app.short[name][0]}   {self.app.tr(self.app.cat_labels[cat])}')),name=cat+'|'+name))
        if lv.children:lv.index=0
    async def on_input_changed(self,event):
        if hasattr(self,'seq'):await self.populate(event.value)
    def on_input_submitted(self,event):self.choose()
    def on_list_view_selected(self,event):self.choose()
    def action_next(self):
        lv=self.query_one(ListView);lv.index=min(len(lv.children)-1,(lv.index or 0)+1) if lv.children else None
    def action_previous(self):
        lv=self.query_one(ListView);lv.index=max(0,(lv.index or 0)-1) if lv.children else None
    def choose(self):
        lv=self.query_one(ListView)
        if lv.index is not None and lv.children:
            cat,name=lv.children[lv.index].name.split('|',1);self.dismiss();self.app.open_tool(cat,name)
    def action_close(self):self.dismiss()

class ChangelogScreen(ModalScreen):
    BINDINGS = [Binding('escape', 'close', show=False), Binding('enter', 'close', show=False)]
    def __init__(self, vip=False):
        super().__init__()
        self.vip = vip
    def compose(self):
        with Vertical(id='appearance-box'):
            yield Static('CROWN-TOOLS / CHANGELOG', classes='eyebrow')
            yield Static('Nouveautés & Historique des versions', id='appearance-title')
            yield Static(Text('◆ Édition 2.4.1 — 78 outils standards · résultats structurés · copie · sélection de fichiers', style='bold #ff3452'))
            content = VerticalScroll()
            content.styles.height = "auto"
            content.styles.max_height = 22
            content.styles.margin = (0, 0, 1, 0)
            with content:
                if self.vip:
                    yield Static(Text("◆ CROWN-TOOLS VIP PACK v2.1.0 (Actif)", style="bold #ffd700"))
                    yield Static(Text("  • Packs VIP : modules locaux validés à l’import", style="#ffffff"))
                    yield Static(Text("  • Cache de chemin instantané (%LOCALAPPDATA%/CrownTools/vip_cache.json)", style="#ffffff"))
                    yield Static(Text("  • Support multilingue 6 langues synchro (FR, EN, ES, DE, ZH, AR)", style="#ffffff"))
                    yield Static(Text("  • Liens officiels : discord.gg/kaostools | t.me/v0idtool", style="#ffa500"))
                else:
                    yield Static(Text("◆ CROWN-TOOLS v1.0.0 — Terminal Edition", style="bold #ff3452"))
                    yield Static(Text("  • Moteur TUI moderne Textual + Rich haute performance", style="#ffffff"))
                    yield Static(Text("  • 78 modules standard (Réseau, Domaines, Utilitaires, Crypto, Web)", style="#ffffff"))
                    yield Static(Text("  • HOME Hub inspiré de Void-Tools avec accès direct communautaire", style="#ffffff"))
                    yield Static(Text("  • Localisation intégrale en 6 langues avec bidi/reshaper", style="#ffffff"))
                    yield Static(Text("  • Personnalisation complète : thèmes, animations, profils", style="#ffffff"))
                    yield Static(Text("  • Compatibilité pack VIP v2 avec décompression automatique", style="#ffffff"))
            yield Button('RETOUR  /  ÉCHAP', id='changelog-close')
    def on_button_pressed(self, event):
        self.dismiss()
    def action_close(self):
        self.dismiss()

class CreditsScreen(ModalScreen):
    BINDINGS = [Binding('escape', 'close', show=False), Binding('enter', 'close', show=False)]
    def compose(self):
        with Vertical(id='appearance-box'):
            yield Static('CROWN-TOOLS / CRÉDITS', classes='eyebrow')
            yield Static('Informations & Équipe du projet', id='appearance-title')
            content = VerticalScroll()
            content.styles.height = "auto"
            content.styles.max_height = 22
            content.styles.margin = (0, 0, 1, 0)
            with content:
                yield Static(Text("CROWN-TOOLS — TERMINAL EDITION", style="bold #ff3452"))
                yield Static(Text("Architecture & Réalisation : Dahim & l’équipe Crown", style="#ffffff"))
                yield Static(Text("Inspiré par le projet original Void-Tools par 1s0e", style="#ad8b95"))
                yield Static(Text("\nCommunauté & Support :", style="bold #ffacbb"))
                yield Static(Text("  • Discord : https://discord.gg/kaostools", style="#ffffff"))
                yield Static(Text("  • Telegram : https://t.me/v0idtool", style="#ffffff"))
                import platform, sys
                yield Static(Text("\nSystème :", style="bold #ffacbb"))
                yield Static(Text(f"  • {platform.system()} {platform.release()} · Python {sys.version.split()[0]}", style="#ad8b95"))
                yield Static(Text("\nTechnologies utilisées :", style="bold #ffacbb"))
                yield Static(Text("  • Python 3.12+, Textual, Rich, Requests, Pillow", style="#ad8b95"))
            yield Button('RETOUR  /  ÉCHAP', id='credits-close')
    def on_button_pressed(self, event):
        self.dismiss()
    def action_close(self):
        self.dismiss()

HOME_TOOLS = [
    ('all', '01', 'Discord'),
    ('all', '02', 'Telegram'),
    ('all', '03', 'Zone VIP'),
    ('all', '04', 'Boutique Premium [PREMIUM]'),
    ('all', '05', 'Profil & Thème'),
    ('all', '06', 'Changelog'),
    ('all', '07', 'Crédits & Système'),
    ('all', '08', 'Tous les modules'),
]

HOME_SHORT = {
    'Discord': ('DISCORD', 'Rejoindre le serveur officiel'),
    'Telegram': ('TELEGRAM', 'Canal d’annonces officiel'),
    'Zone VIP': ('ZONE VIP', 'Activer le pack exclusif'),
    'Boutique Premium [PREMIUM]': ('BOUTIQUE PREMIUM', 'Achat de clés & licences'),
    'Profil & Thème': ('PROFIL & THÈME', 'Personnaliser l’apparence'),
    'Changelog': ('CHANGELOG', 'Nouveautés Crown v1.0'),
    'Crédits & Système': ('CRÉDITS & SYSTÈME', 'Informations & diagnostics'),
    'Tous les modules': ('TOUS LES MODULES', 'Explorer tout le catalogue (78)'),
}

HOME_DESCRIPTIONS = {
    'Discord': 'Rejoindre le serveur officiel Crown Tools sur Discord (https://discord.gg/kaostools). Support, communauté et annonces.',
    'Telegram': 'Canal officiel Telegram (https://t.me/v0idtool). Mises à jour, releases, outils et annonces VIP.',
    'Zone VIP': 'Accède à la zone VIP sécurisée. Débloque et charge ton pack VIP d’outils exclusifs (Mon-Pack-VIP.zip).',
    'Boutique Premium [PREMIUM]': 'Portail officiel Crown Premium — Débloque les fonctionnalités avancées et les modules premium exclusifs.',
    'Profil & Thème': 'Configure ton pseudonyme, sélectionne ta langue (FR, EN, ES, DE, ZH, AR) et personnalise ta palette de couleurs.',
    'Changelog': 'Historique complet des mises à jour, correctifs et ajouts de Crown-Tools v1.0 Terminal Edition.',
    'Crédits & Système': 'Crédits officiels Crown Tools & Void Tools. Informations système, environnement d’exécution et diagnostics.',
    'Tous les modules': 'Affiche l’intégralité des 78 modules disponibles dans le catalogue standard sans filtrage.',
}

VIP_HOME_TOOLS = [
    ('all', '01', 'Discord'),
    ('all', '02', 'Telegram'),
    ('all', '03', 'Boutique Premium [PREMIUM]'),
    ('all', '04', 'Mode Standard'),
    ('all', '05', 'Profil & Thème'),
    ('all', '06', 'Changelog VIP'),
    ('all', '07', 'Tous les modules VIP'),
]

VIP_HOME_SHORT = {
    'Discord': ('DISCORD', 'Communauté officielle VIP'),
    'Telegram': ('TELEGRAM', 'Canal officiel t.me/v0idtool'),
    'Boutique Premium [PREMIUM]': ('BOUTIQUE PREMIUM', 'Boutique officielle des clés'),
    'Mode Standard': ('MODE STANDARD', 'Revenir au catalogue normal'),
    'Profil & Thème': ('PROFIL & THÈME', 'Personnaliser l’apparence'),
    'Changelog VIP': ('CHANGELOG VIP', 'Nouveautés du pack VIP v2'),
    'Tous les modules VIP': ('TOUS LES MODULES VIP', 'Explorer les options du pack VIP'),
}

VIP_HOME_DESCRIPTIONS = {
    'Discord': 'Serveur officiel Crown Tools sur Discord (https://discord.gg/kaostools). Support prioritaire VIP et annonces.',
    'Telegram': 'Canal officiel Telegram (https://t.me/v0idtool). Releases VIP et accès aux outils exclusifs.',
    'Boutique Premium [PREMIUM]': 'Portail officiel Crown Premium — Débloque les 43 outils premium du pack VIP.',
    'Mode Standard': 'Quitter l’espace VIP et revenir au tableau de bord standard (78 outils standards).',
    'Profil & Thème': 'Modifier tes préférences utilisateur, changer de thème ou basculer entre les 6 langues disponibles.',
    'Changelog VIP': 'Historique des versions du pack VIP : nouveautés et changements des modules disponibles.',
    'Tous les modules VIP': 'Afficher les modules disponibles dans le pack VIP.',
}

class ToolPresentation:
    BINDINGS=[Binding('f5','screen.run_analysis',show=False,priority=True)]
    def action_run_analysis(self):self.run_tool()
    COPY_RESULT=True
    _last_plain=""
    _last_structured=False
    _last_saved=None
    """Nouvel habillage ; le moteur d'exécution est hérité sans modification."""
    def compose(self):
        yield Topline(classes='tool-topline')
        with Vertical(id='tool-toolbar'):
            with Horizontal(id='title-row'):
                yield Button('← RETOUR',id='back-btn')
                yield Static(Text(self.TITLE_TOOL.upper(),style='bold '+color(self.app,'crown-accent')),id='screen-title')
            yield Static(Text(self.app.descriptions.get(self.TITLE_TOOL,'')),id='tool-context')
            with Horizontal(id='input-row'):
                yield Input(placeholder=legacy.t(self.PLACEHOLDER,self.app.lang),id='tool-input')
                if not getattr(self, 'MULTILINE', False):
                    yield Button('EXÉCUTER  ↗',id='run-btn')
            if getattr(self, 'MULTILINE', False):
                yield TextArea(id='tool-multiline')
            if getattr(self, 'COPY_RESULT', False) or getattr(self, 'FILE_PICKER', False):
                with Horizontal(id='tool-actions'):
                    if getattr(self, 'MULTILINE', False):
                        yield Button('EXÉCUTER  ↗',id='run-btn')
                    if getattr(self, 'FILE_PICKER', False):
                        yield Button(self.app.tr('CHOISIR UN DOSSIER') if self.TITLE_TOOL in {'Local Secret Audit','Similar Image Finder','Duplicate File Finder'} else 'CHOISIR UN FICHIER', id='browse-file-btn')
                    if getattr(self, 'COPY_RESULT', False):
                        yield Button('COPIER LE RÉSULTAT', id='copy-result-btn', disabled=True)
                    yield Button('ENREGISTRER', id='save-result-btn', disabled=True)
        with VerticalScroll(id='result-scroll') as result:
            result.border_title=self.app.tr(' SORTIE / RÉSULTATS ')
            yield Static(Text('◇\n\n' + self.app.tr('PRÊT POUR VOTRE PROCHAINE EXPLORATION') + '\n\n' + legacy.t(self.PLACEHOLDER,self.app.lang)),id='tool-empty')
        yield Static(self.app.tr('ÉCHAP Retour · F5 Exécuter · ENTRÉE Nouvelle ligne') if getattr(self,'MULTILINE',False) else '  ÉCHAP  Retour au tableau de bord    /    ENTRÉE  Exécuter',classes='tool-footnote')
    def on_mount(self):
        self.app.localize(self)
        self.set_class(self.app.size.height<30,'compact-tool')
        self.query_one('#tool-input',Input).focus()
        if getattr(self, 'MULTILINE', False):
            self.query_one('#input-row').display = False
            self.query_one('#tool-multiline',TextArea).focus()
        if self.app.motion:self.styles.opacity=0.;self.styles.animate('opacity',1.,duration=.18)
    def on_button_pressed(self,event):
        if event.button.id == 'save-result-btn':
            self.save_output()
        elif event.button.id == 'copy-result-btn':
            if self._last_plain:
                self.app.copy_to_clipboard(self._last_plain)
                self.app.notify(self.app.tr('Résultat envoyé au presse-papiers du terminal.'))
        else:super().on_button_pressed(event)
    def save_output(self):
        if not self._last_plain:return
        try:
            self._last_saved=save_result(self.TITLE_TOOL,self._last_plain,structured=self._last_structured)
            if self.TITLE_TOOL == 'QR Code':
                import qrcode
                with self._last_saved.with_suffix('.png').open('xb') as stream:
                    qrcode.make(self.query_one('#tool-input',Input).value).save(stream,format='PNG')
            self.app.notify(f'Output : {self._last_saved}')
        except OSError as exc:
            self.app.notify(f'Export impossible : {exc}',severity='warning')

    def run_tool(self):
        self._last_structured=False
        self._last_saved=None
        if self.query('#save-result-btn'):self.query_one('#save-result-btn',Button).disabled=True
        self._started_at=time.monotonic()
        self._last_plain=''
        if self.query('#copy-result-btn'):self.query_one('#copy-result-btn',Button).disabled=True
        if self.query('#run-btn'):self.query_one('#run-btn',Button).disabled=True
        super().run_tool()
    def _finish(self,spinner,scroll,output,ok):
        if not self.is_mounted:return
        if isinstance(output,str) and output.startswith(('[red]','[yellow]')):ok=False
        from rich.console import Console
        from rich.panel import Panel
        import io
        if not ok:
            message=str(output).replace('[bold red]','').replace('[/bold red]','').replace('[red]','').replace('[/red]','').replace('[yellow]','').replace('[/yellow]','')
            output=Panel(Text(message),title='ERREUR / ERROR',border_style='red',padding=(1,1))
        if ok and not self._last_plain:
            stream=io.StringIO();console=Console(file=stream,width=100,color_system=None)
            console.print(output);self._last_plain=stream.getvalue()
        if ok and self._last_plain:
            self.save_output()
        if self.query('#save-result-btn'):self.query_one('#save-result-btn',Button).disabled=not ok or not self._last_plain
        elapsed=time.monotonic()-getattr(self,'_started_at',time.monotonic())
        scroll.border_subtitle=f"{'✓ OK' if ok else '× ERROR'}  ·  {elapsed:.2f} s"
        super()._finish(spinner,scroll,output,ok)
        if self.query('#run-btn'):self.query_one('#run-btn',Button).disabled=False
        if self.query('#copy-result-btn'):self.query_one('#copy-result-btn',Button).disabled=not ok or not self._last_plain
    def on_resize(self,event):
        self.set_class(event.size.height<30,'compact-tool')

SCREEN_CLASSES={(cat,name):type('Styled'+cls.__name__,(ToolPresentation,cls),{}) for (cat,name),cls in legacy.TOOL_SCREENS.items() if name not in RETIRED_TOOLS}

def make_extra_screen(tool):
    class IntegratedTool(ToolPresentation,legacy.ToolScreen):
        BINDINGS=[Binding('f5','screen.run_analysis',show=False,priority=True)]
        TITLE_TOOL=tool.name
        PLACEHOLDER=tool.hint
        MULTILINE=tool.name in {'CSV to JSON','JSON to CSV','XML Format','Line Deduplicator','Line Sorter','JSON Pointer','JSON Diff','TOML to JSON','Text Diff','Email Header Analyzer'}
        FILE_PICKER=tool.name in {'EXIF Forensic','Image Info','File SHA256','ZIP Inspector','File Details','Encoding Detector','File Hexdump','File Entropy','PDF Inspector','QR Barcode Reader','Local Secret Audit','Similar Image Finder','Duplicate File Finder','File Compare','Email Header Analyzer'}
        COPY_RESULT=True
        _last_plain=''
        def on_button_pressed(self,event):
            if event.button.id == 'browse-file-btn':
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root=tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost',True)
                    try:
                        selected=(filedialog.askdirectory(title=self.TITLE_TOOL,initialdir=str(INPUT_DIR)) if self.TITLE_TOOL in {'Local Secret Audit','Similar Image Finder','Duplicate File Finder'} else filedialog.askopenfilenames(title=self.TITLE_TOOL,initialdir=str(INPUT_DIR)) if self.TITLE_TOOL == 'File Compare' else filedialog.askopenfilename(title=self.TITLE_TOOL,initialdir=str(INPUT_DIR)))
                    finally:
                        root.destroy()
                    if selected:
                        if self.TITLE_TOOL == 'File Compare':
                            if len(selected)!=2:raise ValueError('Sélectionnez exactement deux fichiers')
                            selected=' | '.join(selected)
                        if self.MULTILINE:self.query_one('#tool-multiline',TextArea).load_text(selected)
                        else:self.query_one('#tool-input',Input).value=selected
                except Exception as exc:
                    self.app.notify(f'Sélecteur indisponible : {exc}',severity='warning')
            elif event.button.id == 'copy-result-btn':
                if self._last_plain:
                    self.app.copy_to_clipboard(self._last_plain)
                    self.app.notify(self.app.tr('Résultat envoyé au presse-papiers du terminal.'))
            else:super().on_button_pressed(event)
        def run_tool(self):
            self._last_plain=''
            self.query_one('#copy-result-btn',Button).disabled=True
            if self.MULTILINE:
                self.query_one('#tool-input',Input).value=self.query_one('#tool-multiline',TextArea).text
            super().run_tool()
        def _finish(self,spinner,scroll,output,ok):
            if not self.is_mounted:return
            super()._finish(spinner,scroll,output,ok)
            self.query_one('#copy-result-btn',Button).disabled=not ok or not self._last_plain
        def execute(self,value):
            from .result_view import render_result
            output=tool.run(value)
            self._last_structured=isinstance(output,(dict,list))
            self._last_plain=output if isinstance(output,str) else json.dumps(output,indent=2,ensure_ascii=False,default=str)
            return render_result(output,self.TITLE_TOOL,color(self.app,'crown-accent'),self.app.tr)
    IntegratedTool.__name__='Integrated'+tool.name.replace(' ','')
    return IntegratedTool

for tool in EXTRA_TOOLS:SCREEN_CLASSES[tool.category,tool.name]=make_extra_screen(tool)


class CrownApp(App):
    TITLE='CROWN-TOOLS / TERMINAL EDITION'
    SUB_TITLE='Crimson'
    CSS=legacy.CrownToolsApp.CSS+'\n'+(STYLES_DIR/'compact.tcss').read_text(encoding='utf-8')
    CSS_PATH=None
    BINDINGS=[Binding('ctrl+k','search','Recherche'),Binding('f2','appearance','Apparence'),Binding('f6','motion','Animations'),Binding('f1','intro','Introduction'),Binding('ctrl+q','quit','Quitter'),Binding('escape','home','Accueil'),Binding('pagedown','page(1)',show=False),Binding('pageup','page(-1)',show=False),Binding('1','category(0)',show=False),Binding('2','category(1)',show=False),Binding('3','category(2)',show=False),Binding('4','category(3)',show=False)]
    BINDINGS += [Binding(str(i+1) if i<9 else '0',f'category({i})',show=False) for i in range(4,min(10,len(CATEGORIES)+1))]
    def __init__(self,boot=True,profile_path=None,initial_tool=None,language=None,welcome_links=False):
        self.vip_pack=None
        self.catalog=list(HOME_TOOLS)+list(TOOLS);self.categories=list(CATEGORIES);self.cat_labels=dict(CAT_LABELS);self.cat_labels['all']='HOME';self.short=dict(SHORT);self.short.update(HOME_SHORT);self.descriptions=dict(legacy.TOOL_DESCRIPTIONS);self.descriptions.update(HOME_DESCRIPTIONS);self.tool_screens=dict(SCREEN_CLASSES);self.premium_tools={'Boutique Premium [PREMIUM]'}
        self.tool_screens['all', 'Boutique Premium [PREMIUM]'] = lambda: self.open_home_tool('Boutique Premium [PREMIUM]')
        self.active_theme='crimson';self.motion=True;self.boot=boot;self.lang='en';self.config=dict(legacy.DEFAULT_CONFIG,configured=True,sound=False,language='en');self.category='all';self.selected=self.catalog[0];self.columns=2;self.start=time.monotonic()
        try:
            cfg=json.loads((ROOT/'config'/'appearance.json').read_text(encoding='utf-8'))
            if cfg.get('theme') in PALETTES:self.active_theme=cfg['theme']
            self.motion=cfg.get('motion',True) is True
        except (OSError,ValueError,AttributeError):pass
        self.profile_path=Path(profile_path) if profile_path else PROFILE_PATH
        self.welcome_links=welcome_links
        self.vip_settings=read_vip(self.profile_path)
        self.profile=read_profile(self.profile_path);self.username='Invité';self.accent=''
        self.load_preferences()
        self.rainbow_accent='#ff506a';self.rainbow_tick=0.
        self.initial_tool=initial_tool
        if language in LANGUAGES:self.lang=language;self.config['language']=language
        self.page=0;self.page_size=9;self.page_count=1
        super().__init__()
    def get_css_variables(self):
        variables=super().get_css_variables();variables.update(legacy.THEMES[self.active_theme])
        if self.active_theme=='rainbow' and not self.accent:
            variables['crown-accent']=self.rainbow_accent;variables['crown-accent-2']=blend(self.rainbow_accent,'#100d13',.32)
        if self.accent:
            variables['crown-accent']=self.accent;variables['crown-accent-2']=blend(self.accent,'#100d13',.32)
        return variables
    def compose(self):
        yield Topline(id='topline')
        with Horizontal(id='hero'):
            with Horizontal(id='identity'):
                yield CompactSignature(id='dashboard-brand')
                yield VipZoneButton('VIP ZONE',id='secret-entry',tooltip=self.tr('ZONE VIP'))
                with Vertical(id='brand-caption'):
                    yield Static('T O O L S',id='brand-tools')
                    yield Static(self.tr('ESPACE PERSONNEL'),id='hero-tagline')
                    yield Static('',id='brand-rule')
            with Vertical(id='hero-right'):
                with Horizontal(id='profile-identity-row'):
                    yield Static(Text(self.username),id='palette-label')
                    yield Button(self.tr('PROFIL  ↗'),id='edit-header-profile')
                yield Static('',id='signature')
                yield CommunityLink('Discord','Official server','https://discord.gg/kaostools',id='community-discord',classes='community-link')
                yield CommunityLink('Telegram','t.me/v0idtool','https://t.me/v0idtool',id='community-telegram',classes='community-link')
            yield SignatureRail(id='signature-rail')
        with Horizontal(id='workspace'):
            with Vertical(id='navigation'):
                yield Static('NAVIGATION',classes='eyebrow')
                with VerticalScroll(id='category-scroll'):
                    for idx,key in enumerate(['all']+self.categories):
                        yield Button(f'{idx+1:02}  '+self.cat_labels.get(key,key.upper()),id=f'cat-{idx}',classes='nav-button'+(' chosen' if idx==0 else ''))
                yield Button('← MODE STANDARD',id='exit-vip',classes='nav-button',disabled=True)
                yield Static('──────────────',classes='separator')
                yield Button('⌕  RECHERCHER',id='open-search',classes='nav-button')
                yield Button('◐  APPARENCE',id='open-appearance',classes='nav-button')
                yield Telemetry(id='telemetry')
                yield Static('CROWN-TOOLS\nTERMINAL EDITION',id='sidebar-end')
            with Vertical(id='catalog'):
                with Horizontal(id='catalog-heading'):
                    yield Static('01 / COLLECTION',id='collection-title')
                    yield Static(f'{len(self.catalog)} MODULES',id='collection-count')
                yield Static('Molette pour explorer · Entrée pour ouvrir',id='collection-subtitle')
                with VerticalScroll(id='cards-scroll'):
                    with Grid(id='cards'):
                        for index,(cat,num,name) in enumerate(self.catalog):yield ModuleCard(cat,num,name,index)
                yield Static('↕  MOLETTE / DÉFILEMENT CONTINU',id='scroll-hint')
            yield Inspector(id='inspector')
        yield Static('',id='footer')
    def on_mount(self):
        self.query_one('#exit-vip').display=False
        if self.welcome_links:
            from .first_launch import open_welcome_links_once
            self.call_after_refresh(open_welcome_links_once, self.profile_path)
        self.screen.add_class('dashboard');self.resize_layout(self.size.width,self.size.height);self.set_interval(1,self.update_footer);self.update_footer()
        self.query_one(ModuleCard).focus()
        self.localize(self.screen)
        self.set_interval(1/30,self.motion_frame)
        if self.initial_tool:
            self.call_after_refresh(self.open_tool,*self.initial_tool)
        elif self.boot:
            if self.motion:self.push_screen(BootScreen(),lambda _:self.first_run())
            else:self.first_run()
    def on_resize(self,event):
        if self.is_mounted:self.resize_layout(event.size.width,event.size.height)
    def resize_layout(self,width,height):
        dashboard=self.screen_stack[0]
        dashboard.set_class(width<155,'narrow');dashboard.set_class(width<100,'compact');dashboard.set_class(height<34,'short');dashboard.set_class(height<27,'tiny')
        available=width-31-(27 if width>=155 else 0)
        self.columns=max(1,min(4,available//29))
        cards=self.query('#cards')
        if cards:
            cards.first().styles.grid_size_columns=self.columns
            self.paginate()

    def paginate(self):
        if self.category=='all':
            cards=[c for c in self.query(ModuleCard) if c.cat=='all']
        elif self.category=='_full_collection':
            cards=[c for c in self.query(ModuleCard) if c.cat!='all']
        else:
            cards=[c for c in self.query(ModuleCard) if c.cat==self.category]
        visible=cards
        for card in self.query(ModuleCard):card.display=card in visible;card.refresh()
        return visible

    def action_page(self,delta):
        if len(self.screen_stack)>1:return
        scroll=self.query_one('#cards-scroll')
        scroll.scroll_relative(y=delta*max(1,scroll.size.height-2),animate=self.motion)
    def update_footer(self):
        if not self.query('#footer'):return
        elapsed=int(time.monotonic()-self.start);a=color(self,'crown-accent');d=color(self,'crown-text-dim')
        text=Text('  CTRL K ',style=a);text.append(self.tr('recherche')+'   ',style=d);text.append('F2 ',style=a);text.append(self.tr('apparence')+'   ',style=d);text.append('F6 ',style=a);text.append(self.tr('mouvement')+'   ',style=d);text.append('CTRL Q ',style=a);text.append(self.tr('quitter'),style=d)
        if self.size.width<100:
            text=Text(' Ctrl K ',style=a);text.append(self.tr('recherche')+'  ',style=d);text.append('F2 ',style=a);text.append(self.tr('apparence')+'  ',style=d);text.append('Ctrl Q ',style=a);text.append(self.tr('quitter'),style=d)
        tail=('◆ VIP ON  /  ' if self.vip_pack else '')+f'{elapsed//60:02}:{elapsed%60:02}  /  '+('LIVE' if self.motion else 'PAUSE')+'  '
        text.append(' '*max(2,self.size.width-len(text.plain)-len(tail)));text.append(tail,style=d);self.query_one('#footer',Static).update(text)
    def on_module_card_picked(self,message):
        if (message.card.cat,message.card.num,message.card.tool_name) not in self.catalog:return
        self.selected=(message.card.cat,message.card.num,message.card.tool_name)
        self.screen_stack[0].query_one(Inspector).select(message.card)
    def move_card(self,card,delta):
        cards=self.paginate()
        if card in cards:
            index=max(0,min(len(cards)-1,cards.index(card)+delta));cards[index].focus()
    async def on_button_pressed(self,event):
        bid=event.button.id or ''
        if bid.startswith('cat-'):self.action_category(int(bid[4:]))
        elif bid=='open-search':self.action_search()
        elif bid=='open-appearance':self.action_appearance()
        elif bid=='edit-header-profile':self.action_profile()
        elif bid=='secret-entry':await self.action_secret()
        elif bid=='exit-vip':await self.set_catalog(None)
        elif bid=='community-discord':self.open_url('https://discord.gg/kaostools')
        elif bid=='community-telegram':self.open_url('https://t.me/v0idtool')
        elif bid=='detail-open':self.open_tool(self.selected[0],self.selected[2])
    def action_category(self,index):
        if len(self.screen_stack)>1:return
        if not 0<=index<=len(self.categories):return
        key=(['all']+self.categories)[index];self.category=key
        for idx in range(len(self.categories)+1):self.query_one(f'#cat-{idx}').set_class(idx==index,'chosen')
        self.page=0;visible=self.paginate()
        if key=='all':
            title_tag=f'{index+1:02} / '+self.tr('HOME VIP' if self.vip_pack else 'HOME')
            self.query_one('#collection-title',Static).update(title_tag)
            self.query_one('#collection-count',Static).update(self.tr(f'{len(visible):02} OPTIONS'))
            self.query_one('#collection-subtitle',Static).update(Text(self.tr('CROWN-TOOLS · HOME HUB  (discord.gg/kaostools · t.me/v0idtool)')))
        else:
            self.query_one('#collection-title',Static).update(f'{index+1:02} / '+self.tr(self.cat_labels.get(key,key.upper())))
            count=sum(1 for c in self.query(ModuleCard) if c.cat==key)
            self.query_one('#collection-count',Static).update(self.tr(f'{count:02} MODULES'))
            self.query_one('#collection-subtitle',Static).update(Text(self.vip_pack['name'] if self.vip_pack else self.tr('Molette pour explorer · Entrée pour ouvrir')))
        self.query_one('#cards-scroll').scroll_home(animate=False)
        if visible:visible[0].focus()
        now=time.monotonic()
        for i,card in enumerate(visible):card.reveal_at=now+min(i,8)*.018 if self.motion else None
        self.motion_frame()

    def open_home_tool(self,name):
        if name in ('Discord', 'Discord Community'):
            import webbrowser
            webbrowser.open('https://discord.gg/kaostools')
            self.notify(self.tr('Ouverture de Discord (discord.gg/kaostools)...'), severity='information')
        elif name in ('Telegram', 'Telegram Official'):
            import webbrowser
            webbrowser.open('https://t.me/v0idtool')
            self.notify(self.tr('Ouverture de Telegram (t.me/v0idtool)...'), severity='information')
        elif name in ('Zone VIP', 'VIP Zone'):
            self.call_after_refresh(self.action_secret)
        elif 'Boutique Premium' in name or 'Premium Shop' in name:
            self.open_url('https://discord.gg/XS8skNCrWd')
        elif name in ('Mode Standard',):
            self.call_after_refresh(lambda: self.set_catalog(None))
        elif name in ('Profil & Thème', 'Configuration Profil'):
            self.action_profile()
        elif 'Changelog' in name:
            self.push_screen(ChangelogScreen(vip=bool(self.vip_pack)))
        elif 'Crédits' in name:
            self.push_screen(CreditsScreen())
        elif 'Tous les modules' in name:
            self.action_all_collection()

    def action_all_collection(self):
        self.category = '_full_collection'
        for idx in range(len(self.categories)+1):
            self.query_one(f'#cat-{idx}').remove_class('chosen')
        visible = self.paginate()
        self.query_one('#collection-title', Static).update(self.tr('COLLECTION COMPLÈTE'))
        self.query_one('#collection-count', Static).update(self.tr(f'{len(visible):02} MODULES'))
        self.query_one('#collection-subtitle', Static).update(Text(self.tr('Tous les modules sans filtre de catégorie')))
        self.query_one('#cards-scroll').scroll_home(animate=False)
        if visible: visible[0].focus()

    def open_tool(self,cat,name):
        if cat == 'all':
            self.open_home_tool(name)
            return
        handler=self.tool_screens.get((cat,name))
        if not handler:return
        from textual.screen import Screen
        if isinstance(handler,type) and issubclass(handler,Screen):
            self.push_screen(handler())
        elif callable(handler):
            try:
                res=handler()
            except Exception as e:
                self.notify(f"Erreur lancement: {e}", severity="error")
                return
            if isinstance(res,Screen):
                self.push_screen(res)
    def action_search(self):
        if len(self.screen_stack)==1:self.push_screen(SearchScreen())
    async def action_secret(self):
        if len(self.screen_stack)!=1:return
        if self.vip_settings.get('key')=='2027':
            archive=self.vip_settings.get('zip_path','')
            if archive:
                try:
                    pack=load_pack(archive)
                except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
                    self.notify('Pack VIP enregistré indisponible : '+str(error),severity='warning')
                else:
                    await self.vip_selected(pack)
                    return
            self.push_screen(VipPicker(),self.vip_selected)
            return
        self.push_screen(DarkAccess(), self.secret_unlocked)
    def secret_confirmed(self,confirmed):
        if confirmed:self.push_screen(DarkAccess(),self.secret_unlocked)
    def secret_unlocked(self,confirmed):
        if confirmed:
            self.vip_settings={'key':'2027','zip_path':self.vip_settings.get('zip_path','')}
            self.save_vip_access()
            self.push_screen(VipPicker(),self.vip_selected)
    def save_vip_access(self):
        try:write_vip(self.profile_path,self.vip_settings)
        except OSError:self.notify('Accès VIP actif pour cette session, mais sauvegarde impossible.',severity='warning')
    async def vip_selected(self,pack):
        if pack:
            await self.set_catalog(pack)
            self.vip_settings={'key':'2027','zip_path':pack['_archive_path']}
            self.save_vip_access()
            if self.motion:self.push_screen(VipArrival())
    async def set_catalog(self,pack):
        navigation=self.query_one('#category-scroll');cards=self.query_one('#cards')
        await navigation.remove_children();await cards.remove_children()
        self.vip_pack=pack
        self.screen_stack[0].set_class(bool(pack),'vip-active')
        self.refresh_css()
        if pack:
            self.catalog=list(VIP_HOME_TOOLS);self.categories=[];self.cat_labels={'all':'HOME VIP'};self.short=dict(VIP_HOME_SHORT);self.descriptions=dict(VIP_HOME_DESCRIPTIONS);self.tool_screens={('all', 'Boutique Premium [PREMIUM]'): lambda: self.open_home_tool('Boutique Premium [PREMIUM]')};self.premium_tools={'Boutique Premium [PREMIUM]'}
            for module in pack['modules']:
                cat=module.get('category','VIP');name=module['name']
                if module.get('premium') or '[PREMIUM]' in name or 'PREMIUM' in name.upper():
                    self.premium_tools.add(name)
                if cat not in self.categories:self.categories.append(cat)
                num=f"{1+sum(c==cat for c,_,_ in self.catalog):02}"
                self.catalog.append((cat,num,name));self.cat_labels[cat]=cat.upper()
                self.short[name]=(name.upper(),module['description']);self.descriptions[name]=module['description']
                action=module['action']
                if action == 'python':
                    from .vip_integrated_screen import create_vip_screen
                    self.tool_screens[cat,name] = create_vip_screen(module, pack['_archive_path'], app=self)
                    continue
                tool=SimpleNamespace(name=name,hint='Nombre : 1–50' if action=='uuid' else 'Texte à analyser',run=lambda value,a=action:execute_vip(a,value))
                self.tool_screens[cat,name]=make_extra_screen(tool)
        else:
            self.catalog=list(HOME_TOOLS)+list(TOOLS);self.categories=list(CATEGORIES);self.cat_labels=dict(CAT_LABELS);self.cat_labels['all']='HOME';self.short=dict(SHORT);self.short.update(HOME_SHORT);self.descriptions=dict(legacy.TOOL_DESCRIPTIONS);self.descriptions.update(HOME_DESCRIPTIONS);self.tool_screens=dict(SCREEN_CLASSES);self.premium_tools={'Boutique Premium [PREMIUM]'}
        self.category='all';self.selected=self.catalog[0]
        await navigation.mount(*[Button(f'{i+1:02}  '+self.tr(self.cat_labels.get(cat,cat.upper())),id=f'cat-{i}',classes='nav-button'+(' chosen' if i==0 else '')) for i,cat in enumerate(['all']+self.categories)])
        await cards.mount(*[ModuleCard(cat,num,name,i) for i,(cat,num,name) in enumerate(self.catalog)])
        back=self.query_one('#exit-vip',Button);back._source_label='← MODE STANDARD';back.label=self.tr('← MODE STANDARD');back.display=bool(pack);back.disabled=not bool(pack)
        self.query_one('#sidebar-end',Static).update('CROWN-TOOLS\n'+('VIP ZONE' if pack else 'TERMINAL EDITION'))
        self.query_one('#collection-subtitle',Static).update(Text(self.tr('CROWN VIP · HOME HUB  (discord.gg/kaostools · t.me/v0idtool)') if pack else self.tr('CROWN-TOOLS · HOME HUB  (discord.gg/kaostools · t.me/v0idtool)')))
        self.resize_layout(self.size.width,self.size.height);self.action_category(0)
        self.query_one(Inspector).select(self.query_one(ModuleCard))
        portal=self.query_one('#secret-entry',Button)
        portal.tooltip='VIP ON · '+pack['name'] if pack else self.tr('ZONE VIP')
        portal.refresh();self.query_one('#signature-rail').refresh();self.update_footer()

    def action_appearance(self):
        if len(self.screen_stack)==1:self.push_screen(AppearanceScreen())
    def action_intro(self):
        if len(self.screen_stack)==1:self.push_screen(BootScreen())
    def action_home(self):
        if len(self.screen_stack)==1:self.action_category(0)
    def motion_frame(self):
        now=time.monotonic()
        if self.active_theme=='rainbow' and self.motion and not self.accent and now-self.rainbow_tick>.35:
            self.rainbow_tick=now
            self.rainbow_accent='#'+''.join(f'{round(c*255):02x}' for c in colorsys.hsv_to_rgb(((now-self.start)/16)%1,.62,1.))
            self.refresh_css()
        if len(self.screen_stack)!=1:return
        for card in self.query(ModuleCard):
            if card.display:card.motion_frame(now,self.motion)
    def action_motion(self):
        self.motion=not self.motion;self.save_appearance();self.update_footer();self.motion_frame()
        for widget in self.query('CompactSignature, SignatureRail'):widget.refresh()
    def apply_theme(self,key):
        self.active_theme=key;self.accent='';self.refresh_css();self.save_appearance();self.query_one('#signature',Static).update('')
        for widget in self.query(Static):widget.refresh()
    def save_appearance(self):
        if self.profile:
            self.profile.update(theme=self.active_theme,motion=self.motion,accent=self.accent)
            try:write_profile(self.profile_path,self.profile)
            except OSError:self.notify(self.tr('Sauvegarde impossible.'),severity='warning')
            return
        try:write_profile(self.profile_path,{'theme':self.active_theme,'motion':self.motion,'accent':self.accent,'language':self.lang})
        except OSError:self.notify('Impossible de sauvegarder l’apparence.',severity='warning')

    def tr(self,text):return translate(text,self.lang)
    def load_preferences(self):
        if self.profile:
            self.username=self.profile['username'];self.lang=self.profile['language']
            self.active_theme=self.profile['theme'];self.accent=self.profile.get('accent','')
            self.motion=self.profile.get('motion',True) is True
            self.config.update(language=self.lang,username=self.username)
    def first_run(self):
        if not self.profile:self.push_screen(ProfileScreen(first=True))
    def action_profile(self):
        if len(self.screen_stack)==1:self.push_screen(ProfileScreen())
    def profile_updated(self):
        self.refresh_css()
        self.query_one('#palette-label',Static).update(Text(self.username))
        self.localize(self.screen_stack[0])
        self.action_category((['all']+self.categories).index(self.category))
        for widget in self.query(Static):widget.refresh()
        self.update_footer()
    def localize(self,root,language=None):
        tr=lambda text:translate(text,language or self.lang)
        for widget in root.query('Static, Button, Input'):
            if isinstance(widget,ModuleCard):
                widget.tooltip=tr(self.descriptions[widget.tool_name]);widget.refresh()
            elif isinstance(widget,Button):
                if widget.id=='secret-entry':widget.tooltip=tr('ZONE VIP')
                source=getattr(widget,'_source_label',str(widget.label));widget._source_label=source
                widget.label=tr(source)
            elif isinstance(widget,Input):
                source=getattr(widget,'_source_placeholder',widget.placeholder);widget._source_placeholder=source;widget.placeholder=tr(source)
            elif type(widget) is Static and widget.id not in ('palette-label','footer'):
                source=getattr(widget,'_source_text',widget.content)
                if isinstance(source,Text):source=source.plain
                if isinstance(source,str):widget._source_text=source;widget.update(tr(source))
