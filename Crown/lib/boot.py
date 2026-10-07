"""Ancienne direction néon, adaptée au rendu non bloquant de Textual."""
import math
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from rich.text import Text
from rich.style import Style
from functools import lru_cache
from textual.widgets import Static
from intro_valider import _load_logo_font, _compose_frame


@lru_cache(maxsize=4096)
def _pixel_style(top, bottom):
    return Style(color=f"#{top:06x}", bgcolor=f"#{bottom:06x}")


def _rgb_array_to_text(arr):
    """Find color runs in NumPy; reuse styles across animation frames."""
    pixels = arr.astype(np.uint32)
    packed = (pixels[..., 0] << 16) | (pixels[..., 1] << 8) | pixels[..., 2]
    out = Text(no_wrap=True, overflow='crop')
    width = packed.shape[1]
    for y in range(0, packed.shape[0] - 1, 2):
        top, bottom = packed[y], packed[y + 1]
        edges = np.flatnonzero((top[1:] != top[:-1]) | (bottom[1:] != bottom[:-1])) + 1
        start = 0
        if y:
            out.append('\n')
        for end in (*edges, width):
            out.append('▀' * (int(end) - start), _pixel_style(int(top[start]), int(bottom[start])))
            start = int(end)
    return out


class NeonBoot(Static):
    def on_mount(self):
        self.started=time.monotonic()
        self.shape=None
        self.preview_time=None
        self._still_key=None
        self._skip_key=None
        self.styles.content_align=("center", "middle")
        self.set_interval(1/20,self.tick)
        self.tick()

    def prepare(self,w,h):
        self.shape=(w,h)
        scale=4
        image=Image.new('L',(w*scale,h*scale))
        draw=ImageDraw.Draw(image)
        size=max(10,int(h*scale*.62))
        while True:
            font=_load_logo_font(size)
            box=draw.textbbox((0,0),'CROWN-TOOLS',font=font)
            tw,th=box[2]-box[0],box[3]-box[1]
            if tw<=w*scale*.90 or size<=8:break
            size-=max(1,size//40)
        draw.text(((w*scale-tw)/2-box[0],(h*scale-th)/2-box[1]),'CROWN-TOOLS',font=font,fill=255)
        mask=np.asarray(image.resize((w,h),Image.Resampling.LANCZOS),dtype=np.float32)/255
        self.sharp=np.clip((mask-.5)*2.2+.5,0,1)
        self.core=Image.fromarray((self.sharp*255).astype(np.uint8))
        self.glow=np.asarray(self.core.filter(ImageFilter.GaussianBlur(max(.5,h*.010))),dtype=np.float32)/255
        self.bloom=np.asarray(self.core.filter(ImageFilter.GaussianBlur(max(1,h*.024))),dtype=np.float32)/255
        self.base=_compose_frame(self.sharp,self.glow,self.bloom)
        self.yy,self.xx=np.mgrid[:h,:w]
        self.distance=np.sqrt((self.xx-w/2)**2+(self.yy-h/2)**2)
        self.radial=np.sqrt(((self.xx-w/2)/(w*.46))**2+((self.yy-h/2)/(h*.36))**2)
        rng=np.random.default_rng(17)
        self.stars=rng.random((max(55,w*h//75),4))
        ys,xs=np.where(self.sharp>.55)
        ids=rng.integers(0,len(xs),55) if len(xs) else np.array([],dtype=int)
        self.embers=np.column_stack((xs[ids],ys[ids],rng.uniform(-12,12,len(ids)),rng.uniform(-22,-5,len(ids))))
        self.outline=np.exp(-((self.radial-1.0)**2)/.0012)*.29
        self.halo=np.exp(-((self.radial-1.0)**2)/.006)*.065
        self.angle=np.arctan2(self.yy-h/2,self.xx-w/2)
        self.arc=(self.angle+math.pi/2)%(2*math.pi)

    def tick(self):
        if not self.is_mounted or self.app.screen is not self.screen:return
        w=min(160,max(10,self.size.width));h=min(80,max(8,self.size.height*2))
        if self.shape!=(w,h):self.prepare(w,h)
        t=self.preview_time if self.preview_time is not None else time.monotonic()-self.started
        if not self.app.motion:t=5.0
        accent=self.app.get_css_variables()['crown-accent']
        still_key=(w,h,accent)
        if not self.app.motion and self._still_key==still_key:return
        self._still_key=still_key if not self.app.motion else None
        tint=np.array([int(accent[i:i+2],16)/255 for i in (1,3,5)])
        stars=np.zeros((h,w),dtype=np.float32)
        for x,y,s,b in self.stars:
            expansion=1+(t%18)*(.015+s*.012)
            xx=int((w/2+(x-.5)*w*expansion)%w)
            yy=int((h/2+(y-.5)*h*expansion)%h)
            stars[yy,xx]=(.12+b*.25)*(.8+.2*math.sin(t+s*12))
            if t<1.8:
                for tail in range(1,4):
                    tx=int(xx+(w/2-xx)*tail*.018);ty=int(yy+(h/2-yy)*tail*.018)
                    if 0<=tx<w and 0<=ty<h:stars[ty,tx]=max(stars[ty,tx],(.12+b*.25)*(1-tail/4))
        if t<1.8:
            p=max(0,t/1.8);ease=p*p*(3-2*p)
            radius=max(0,12*(1-ease)**2)
            sharp=np.asarray(self.core.filter(ImageFilter.GaussianBlur(radius)),dtype=np.float32)/255
            rgb=_compose_frame(sharp,self.glow,self.bloom,stars,brightness=.2+.8*min(1,ease*1.4))
            shift=round(6*(1-ease))
            rgb[:,:,0]=np.roll(rgb[:,:,0],shift,axis=1)
            rgb[:,:,2]=np.roll(rgb[:,:,2],-shift,axis=1)
        else:
            rgb=self.base.copy()+stars[:,:,None]*.25
            if t<2.5:
                p=(t-1.8)/.7
                for x,y,vx,vy in self.embers:
                    xx=int(x+vx*p);yy=int(y+vy*p+10*p*p)
                    if 0<=xx<w and 0<=yy<h:rgb[yy,xx]+=np.array([1,.55,.15])*(1-p)
                if p<.25:rgb=np.roll(rgb,round(math.sin(p*60)*(1-p*4)*2),axis=1)
            elif t<3.3:
                sx=(-.1+(t-2.5)/.8*1.2)*w
                band=np.exp(-((self.xx-sx)**2)/(2*max(2,w*.025)**2))
                rgb+=band[:,:,None]*(self.sharp+self.glow*.4)[:,:,None]*.9
            elif t<4.2:
                radius=(t-3.3)/.9*(float(self.distance.max())+5)
                ring=np.exp(-((self.distance-radius)**2)/(2*max(1,h*.035)**2))
                rgb+=ring[:,:,None]*(self.sharp*.7+.1)[:,:,None]
        # Un anneau elliptique encadre le logo et anime toute la scène, sans masquer le texte.
        outline=self.outline
        halo=self.halo
        orbit_time=max(0.0,t-4.2)
        progress=min(1.0,orbit_time/3.0)
        reveal=progress**3*(progress*(progress*6.0-15.0)+10.0)
        angle=self.angle
        # L'anneau se dessine depuis le haut, après l'onde de choc.
        arc=self.arc
        edge=progress*(2*math.pi+.32)
        arc_reveal=np.clip((edge-arc)/.32,0,1)
        arc_reveal=arc_reveal*arc_reveal*(3.0-2.0*arc_reveal)
        sweep=np.maximum(0,np.cos(angle+math.pi/2-orbit_time*.5))**12
        rgb=np.maximum(rgb[:,:,0:1]*tint,stars[:,:,None]*.4)
        rgb+=((outline*(.65+1.7*sweep)+halo)*arc_reveal*reveal)[:,:,None]*tint
        if t>=4.2:rgb*=.95+.05*math.sin((t-4.2)*1.5)
        arr=np.clip(rgb*255,0,255).astype(np.uint8)
        # Réduire les changements de couleur presque invisibles et le trafic terminal.
        arr=(arr//4)*4
        self.update(_rgb_array_to_text(arr))
        skip_key=(t>=4.2,accent,self.app.lang)
        if self._skip_key!=skip_key:
            self._skip_key=skip_key
            self.screen.query_one('#boot-skip',Static).update(Text(self.app.tr('ENTRÉE  /  '+('CONTINUER' if t>=4.2 else 'PASSER L’INTRODUCTION')),style='bold '+accent))
