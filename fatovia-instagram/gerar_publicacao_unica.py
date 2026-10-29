from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W,H=1080,1350
OUT=Path("fatovia-instagram/publicacao_unica_2026")
OUT.mkdir(parents=True,exist_ok=True)
VERDE="#123D32"
CREME="#F4F0E6"
CLARO="#BED9C0"
TEXTO="#1F342D"
SECUNDARIO="#557266"
FNT="/usr/share/fonts/truetype/lato/"
REG=FNT+"Lato-Regular.ttf"
BOLD=FNT+"Lato-Bold.ttf"
HEAVY=FNT+"Lato-Heavy.ttf"
CARDS=[
 {"id":1,"mode":"cover","kicker":"AUDITORIA DOCUMENTAL • 2º TURNO 2026",
  "title":"O QUE OS DADOS\nDAS URNAS\nMOSTRAM?",
  "body":"Uma análise independente de dados públicos das 27 UFs e da votação no exterior.",
  "note":"O objetivo é verificar evidências, não apontar culpados."},
 {"id":2,"mode":"metric","kicker":"BASES UTILIZADAS",
  "metric":"168","title":"PACOTES OFICIAIS",
  "body":"56 pacotes GEDAI e 112 pacotes com correspondências de urnas e boletins publicados.",
  "note":"Os 168 hashes SHA-512 coincidiram com as referências oficiais."},
 {"id":3,"mode":"metric","kicker":"CRUZAMENTO NACIONAL",
  "metric":"499.207","title":"SEÇÕES ANALISADAS",
  "body":"Em todas elas, a identificação da urna efetivada coincidiu com a registrada na base de boletins.",
  "note":"0 divergências de IDENTIFICAÇÃO. Não é recontagem de votos."},
 {"id":4,"mode":"metric","kicker":"COMPARAÇÃO ENTRE VERSÕES",
  "metric":"350","title":"MUDANÇAS NA PREVISÃO",
  "body":"A identificação da urna prevista mudou entre as versões de 24 e 25 de outubro.",
  "note":"Mudança da urna prevista não demonstra alteração de votos."},
 {"id":5,"mode":"metric","kicker":"PREVISÃO × EFETIVAÇÃO",
  "metric":"2.686","title":"IDENTIFICADORES DIFERENTES",
  "body":"Urnas efetivamente utilizadas não coincidiram com as previstas em 25/10 nessas seções.",
  "note":"As causas exigem confronto com registros de contingência."},
 {"id":6,"mode":"metric","kicker":"RASTREABILIDADE DA PREPARAÇÃO",
  "metric":"675","title":"ARQUIVOS GEDAI ALTERADOS",
  "body":"Arquivos internos tiveram conteúdo diferente entre os pacotes publicados em 24 e 25/10.",
  "note":"Diferenças entre versões não são, por si, evidência de fraude."},
 {"id":7,"mode":"closing","kicker":"O QUE FALTA INVESTIGAR?",
  "title":"CONSISTÊNCIA\nNÃO É AUDITORIA\nCOMPLETA.",
  "body":"Faltam conferir RDVs, boletins impressos independentes, atas, justificativas de contingência e registros de totalização.",
  "note":"Nenhuma fraude foi demonstrada por estes cruzamentos. Os limites da análise estão documentados."}
]
def ft(size,style="regular"):
    return ImageFont.truetype({"regular":REG,"bold":BOLD,"heavy":HEAVY}[style],size)
def break_lines(draw,txt,f,maxw):
    result=[]
    for paragraph in txt.split("\n"):
        if not paragraph:
            result.append("")
            continue
        current=""
        for word in paragraph.split(" "):
            alt=(current+" "+word).strip()
            if draw.textbbox((0,0),alt,font=f)[2]<=maxw: current=alt
            else:
                if current: result.append(current)
                current=word
        if current:result.append(current)
    return result
def write_block(draw,txt,xy,size,maxw,color,style="regular",spacing=13,maxh=None):
    x,y=xy
    while True:
        f=ft(size,style)
        lines=break_lines(draw,txt,f,maxw)
        bbox=draw.textbbox((0,0),"Ág",font=f)
        height=bbox[3]-bbox[1]
        step=height+spacing
        if maxh is None or len(lines)*step<=maxh or size<=23:break
        size-=2
    for line in lines:
        if line:draw.text((x,y),line,font=f,fill=color)
        y+=step
    return y
for c in CARDS:
    i=c["id"]
    dark=i in (1,7)
    bg=VERDE if dark else CREME
    ink=CREME if dark else TEXTO
    accent=CLARO if dark else VERDE
    muted=CLARO if dark else SECUNDARIO
    im=Image.new("RGB",(W,H),bg)
    d=ImageDraw.Draw(im)
    d.rectangle((67,65,1013,71),fill=accent)
    d.text((70,117),"FATOVIA",font=ft(43,"heavy"),fill=ink)
    d.text((812,132),"DOSSIÊ 2026",font=ft(22,"bold"),fill=muted)
    d.text((70,218),c["kicker"],font=ft(25,"bold"),fill=muted)
    d.ellipse((959,228,981,250),fill=accent)
    if c["mode"]=="cover":
        y=write_block(d,c["title"],(65,324),86,940,ink,"heavy",15,maxh=430)
        d.rectangle((70,y+28,291,y+34),fill=accent)
        write_block(d,c["body"],(70,y+82),39,910,ink,"regular",14,maxh=260)
    elif c["mode"]=="metric":
        met=c["metric"]
        size=161 if len(met)<=3 else (138 if len(met)<=5 else 131)
        d.text((66,310),met,font=ft(size,"heavy"),fill=accent)
        d.rectangle((70,508,1012,512),fill=accent)
        title_y=554
        title_end=write_block(d,c["title"],(69,title_y),56,940,ink,"heavy",11,maxh=176)
        write_block(d,c["body"],(71,max(title_end+33,743)),37,930,ink,"regular",16,maxh=282)
    else:
        end=write_block(d,c["title"],(68,331),73,936,ink,"heavy",17,maxh=415)
        d.rectangle((70,end+27,323,end+33),fill=accent)
        write_block(d,c["body"],(70,end+85),37,933,ink,"regular",18,maxh=318)
    d.rounded_rectangle((65,1074,1013,1230),radius=24,outline=accent,width=3)
    write_block(d,c["note"],(94,1114),29,875,ink,"bold",12,maxh=102)
    d.rectangle((66,1276,1014,1279),fill=accent)
    d.text((68,1301),"FONTES: DADOS ABERTOS DO TSE • MÉTODO REPRODUZÍVEL",font=ft(19,"bold"),fill=muted)
    d.text((899,1301),"@fato.via",font=ft(18,"bold"),fill=muted)
    fn=OUT/f"card_{i:02d}.jpg"
    im.save(fn,quality=93,optimize=True,subsampling=0)
    print(fn,fn.stat().st_size,flush=True)
