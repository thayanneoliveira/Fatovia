"""Reusable fixed-baseline caption layout, independent of scene/camera transforms."""
from dataclasses import dataclass
from PIL import ImageDraw, ImageFont
from functools import lru_cache
import math

@dataclass(frozen=True)
class CaptionStyle:
    font_path: str = '/usr/share/fonts/truetype/lato/Lato-Black.ttf'
    font_scale: float = 28/540
    min_font_scale: float = 18/540
    width_fraction: float = .80
    baseline_fraction: float = .813
    stroke_scale: float = 3/720
    text_color: str = '#faf1df'
    active_color: str = '#e7bc69'
    outline: str = '#142f29'
    hold: float = .10
    max_words: int = 4

@lru_cache(maxsize=64)
def font(path,size):
    return ImageFont.truetype(path,size)

class KineticCaptions:
    def __init__(self, groups, width, height, style=CaptionStyle()):
        self.width,self.height,self.style=width,height,style
        self.groups=[]
        self.baseline=round(height*style.baseline_fraction)
        self.stroke=max(1,round(width*style.stroke_scale))
        previous=-1.
        for text,words in groups:
            if not 1<=len(text)<=style.max_words or len(text)!=len(words): raise ValueError('bad caption group')
            for w in words:
                s,e=float(w['start']),float(w['end'])
                if not math.isfinite(s) or not math.isfinite(e) or s<0 or e<=s or s<previous: raise ValueError('bad timestamp')
                previous=s
            self.groups.append((tuple(text),tuple(words),self.layout(text)))
    def layout(self,text):
        s=self.style; limit=self.width*s.width_fraction
        size=round(self.width*s.font_scale); minimum=max(1,round(self.width*s.min_font_scale))
        for n in range(size,minimum-1,-1):
            f=font(s.font_path,n); widths=[f.getlength(w) for w in text];space=f.getlength(' ')
            total=sum(widths)+space*(len(text)-1)
            if total+4*self.stroke<=limit: break
        else: raise ValueError('caption cannot fit safe area')
        x=(self.width-total)/2;positions=[];boxes=[]
        for word,w in zip(text,widths):
            xx=round(x);positions.append(xx)
            l,t,r,b=f.getbbox(word,anchor='ls',stroke_width=self.stroke)
            boxes.append((xx+l,self.baseline+t,xx+r,self.baseline+b))
            x+=w+space
        if any(l<self.width*(1-s.width_fraction)/2 or r>self.width*(1+s.width_fraction)/2 or t<0 or b>self.height*.85 for l,t,r,b in boxes):raise ValueError('caption outside safe area')
        return f,tuple(positions),tuple(boxes)
    def state(self,t):
        for i,(text,words,layout) in enumerate(self.groups):
            start=words[0]['start'];end=words[-1]['end']+self.style.hold
            if i+1<len(self.groups):end=min(end,self.groups[i+1][1][0]['start'])
            if start<=t<end:
                shown=tuple(j for j,w in enumerate(words) if t>=w['start'])
                return i,shown
        return None,()
    def draw(self,im,t):
        if im.size!=(self.width,self.height):raise ValueError('canvas mismatch')
        i,shown=self.state(t)
        if i is None or not shown:return im
        text,_,(f,positions,_)=self.groups[i];d=ImageDraw.Draw(im);s=self.style
        for j in shown:
            d.text((positions[j],self.baseline),text[j],font=f,fill=s.active_color if j==shown[-1] else s.text_color,stroke_width=self.stroke,stroke_fill=s.outline,anchor='ls')
        return im