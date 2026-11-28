"""Versioned deterministic editorial layout. No paid services."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .brand import approved_logo, fit_logo

REVISION = "premium-editorial-v1"
CREAM, GOLD, SAGE = "#F5F1E7", "#E5BE74", "#B5D39F"
LABELS = ("ENTENDA O CENÁRIO", "O QUE PROPÕE", "COMO FUNCIONA", "IMPACTO POSSÍVEL", "O QUE ACOMPANHAR", "SITUAÇÃO DOCUMENTAL", "CONCLUSÃO E FONTES")
CTA = {
    "camara:2653944/2d94a3cc4eebf7": "Compartilhe com quem quer entender o projeto antes de opinar.",
    "camara:2658959/312e525a513387": "Compartilhe com quem quer entender como a prevenção de queimadas pode ser financiada.",
    "camara:2659020/0df9252ed4b520": "Compartilhe com quem sempre comenta sobre as condições da estrada.",
    "camara:2659462/b523d110082ee1": "Compartilhe com respeito, sem expor vítimas.",
    "camara:2659342/32c9b9359dcd43": "Compartilhe com quem sempre repara nas árvores e nos fios da rua.",
    "camara:2660119/1d2626b8ceaffc": "Compartilhe com quem já tentou encontrar um documento antigo da família.",
    "camara:2660442/61123c2d60c463": "Compartilhe informação sem reproduzir imagens de vítimas."
}

def closing(item):
    if str(item.get("id","")).startswith("civic:"):
        from .civic import closing as civic_closing
        return civic_closing(item)
    return CTA.get(item["id"]+"/"+item["version"], "Compartilhe com quem quer entender esta proposta antes de opinar.")

def font(size, serif=False, bold=False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVu"
    return ImageFont.truetype(path + ("Serif" if serif else "Sans") + ("-Bold" if bold else "") + ".ttf", size)

def lines(draw, text, f, width):
    out=[]
    for p in str(text).split("\n"):
        current=""
        for word in p.split():
            test=(current+" "+word).strip()
            if draw.textlength(test,font=f)>width:
                if not current: raise ValueError("word_overflow")
                out.append(current)
                current=word
                if draw.textlength(current,font=f)>width: raise ValueError("word_overflow")
            else: current=test
        out.append(current)
    return out

def block(draw,text,x,y,width,max_height,start,minimum,serif=False,bold=False,color=CREAM):
    for size in range(start,minimum-1,-2):
        f=font(size,serif,bold)
        rows=lines(draw,text,f,width)
        step=int(size*1.29)
        if step*len(rows)<=max_height:
            for row in rows:
                draw.text((x,y),row,font=f,fill=color)
                y+=step
            return y
    raise ValueError("premium_text_overflow")

def cover_art(d,item,y):
    # A single contextual line illustration. Not a chart or documentary photograph.
    if y>850: return
    x=760; cy=980
    col="#79916B"; gold=GOLD
    ident=item["id"]
    d.ellipse((x-105,cy-105,x+105,cy+105),outline="#385D49",width=3)
    if ident=="camara:2653944":
        d.ellipse((x-66,cy-59,x+66,cy+59),outline=gold,width=5)
        d.text((x-30,cy-37),"R$",font=font(42,bold=True),fill=gold)
    elif ident=="camara:2658959":
        d.line([(x,cy+75),(x,cy-15),(x-35,cy-55),(x,cy-90),(x+35,cy-55),(x,cy-15)],fill=col,width=6)
        d.arc((x-65,cy-55,x+65,cy+85),20,160,fill=gold,width=4)
    elif ident=="camara:2659020":
        d.line([(x-78,cy+80),(x-25,cy-80)],fill=col,width=6)
        d.line([(x+78,cy+80),(x+25,cy-80)],fill=col,width=6)
        for offset in (-50,0,50):
            d.line((x,cy+offset-12,x,cy+offset+12),fill=gold,width=5)
    elif ident=="camara:2659342":
        d.line([(x-60,cy+75),(x-60,cy-25)],fill=col,width=6)
        d.ellipse((x-100,cy-100,x-20,cy-12),outline=col,width=5)
        d.line([(x+52,cy+75),(x+52,cy-76)],fill=gold,width=5)
        d.line((x+5,cy-53,x+96,cy-53),fill=gold,width=5)
        d.line((x-10,cy-25,x+100,cy-25),fill=gold,width=3)
    elif ident=="camara:2660119":
        d.rounded_rectangle((x-68,cy-82,x+68,cy+82),radius=8,outline=gold,width=5)
        for offset in (-35,0,35):
            d.line((x-40,cy+offset,x+40,cy+offset),fill=col,width=4)
    elif ident in ("camara:2659462","camara:2660442"):
        d.line([(x,cy-80),(x+68,cy-53),(x+58,cy+20),(x,cy+75),(x-58,cy+20),(x-68,cy-53),(x,cy-80)],fill=gold,width=5)
        d.line([(x-25,cy),(x-5,cy+24),(x+30,cy-24)],fill=col,width=5)
    else:
        d.rounded_rectangle((x-66,cy-82,x+66,cy+82),radius=8,outline=gold,width=5)
        d.line((x-35,cy-20,x+35,cy-20),fill=col,width=4)
        d.line((x-35,cy+20,x+35,cy+20),fill=col,width=4)

def card(path, number, headline, body, hint, item):
    if not 1<=number<=7: raise ValueError("card_number")
    im=Image.new("RGB",(1080,1350),"#103629")
    d=ImageDraw.Draw(im)
    for y in range(1350):
        t=y/1349
        d.line((0,y,1079,y),fill=(int(16-7*t),int(54-16*t),int(41-12*t)))
    logo=approved_logo()
    if logo is not None:
        mark=fit_logo(logo,480,84)
        im.paste(mark,(65,42+(84-mark.height)//2),mark)
    else:
        d.text((66,53),"FATO.VIA",font=font(36,bold=True),fill=CREAM)
    d.line((620,83,1010,83),fill=GOLD,width=2)
    civic=str(item.get("id","")).startswith("civic:")
    from .didactic import reviewed
    generic=not civic and reviewed(item) is None
    label=(("ENTENDA O CENÁRIO","O DADO OFICIAL","POLÍTICA PÚBLICA","NA PRÁTICA","O QUE ACOMPANHAR","LIMITES DO DADO","CONCLUSÃO E FONTES") if civic else (("ENTENDA O CENÁRIO","EMENTA OFICIAL","CONTEXTO DO TEXTO","TRAMITAÇÃO","LIMITES DA INFORMAÇÃO","O QUE ACOMPANHAR","CONCLUSÃO E FONTES") if generic else LABELS))[number-1]
    lf=font(25,bold=True)
    d.rounded_rectangle((66,150,86+int(d.textlength(label,font=lf)),207),radius=8,fill=SAGE)
    d.text((76,163),label,font=lf,fill="#103629")
    y=block(d,headline,66,250,944,350,79,57,serif=True,bold=True)
    y=max(445,y+30)
    d.line((66,y,205,y),fill=GOLD,width=7)
    y+=45
    if number==7:
        y=block(d,body,66,y,944,350,35,27)
        y+=22
        d.line([(71,y+8),(111,y+8),(111,y+64),(91,y+48),(71,y+64),(71,y+8)],fill=GOLD,width=4)
        y=block(d,"Salve este post para consultar os indicadores." if civic else "Salve este post para acompanhar a tramitação.",141,y,865,115,34,30,bold=True)+28
        d.line([(70,y+15),(119,y),(96,y+53),(87,y+31),(70,y+15)],fill=GOLD,width=4)
        d.line([(87,y+31),(119,y)],fill=GOLD,width=3)
        y=block(d,closing(item),141,y,865,150,34,30)
    else:
        y=block(d,body,66,y,944,1080-y,43,32)
        if number==1: cover_art(d,item,y)
    if y>1115: raise ValueError("footer_overlap")
    block(d,"Fonte: "+(item["source_name"] if civic else "Câmara dos Deputados")+" | "+item["title"],66,1154,944,60,26,24,color=SAGE)
    d.text((66,1261),"@fato.via",font=font(32),fill=CREAM)
    d.line((260,1280,855,1280),fill=GOLD,width=2)
    d.rounded_rectangle((880,1240,1014,1310),radius=30,outline=GOLD,width=3)
    d.text((915,1255),f"{number}/7",font=font(32),fill=CREAM)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    im.save(path,"JPEG",quality=91,optimize=True,subsampling=0)
    return str(path)
