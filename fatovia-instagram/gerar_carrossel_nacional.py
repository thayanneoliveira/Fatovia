from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
W,H=1080,1350
DEST=Path('fatovia-instagram/cards_nacionais');DEST.mkdir(parents=True,exist_ok=True)
DEEP='#123D32';CREAM='#F4F0E6';MINT='#BCD8B8';INK='#1F342D';SUB='#5D6E64'
REG='/usr/share/fonts/truetype/lato/Lato-Regular.ttf'
BOLD='/usr/share/fonts/truetype/lato/Lato-Bold.ttf'
HEAVY='/usr/share/fonts/truetype/lato/Lato-Heavy.ttf'
def font(size,bold=False,heavy=False):return ImageFont.truetype(HEAVY if heavy else BOLD if bold else REG,size)
def wrap(draw,txt,f,maximum):
    out=[]
    for paragraph in txt.split('\n'):
        if not paragraph:out.append('');continue
        current=''
        for word in paragraph.split(' '):
            nxt=(current+' '+word).strip()
            if draw.textbbox((0,0),nxt,font=f)[2]<=maximum:current=nxt
            else:
                if current:out.append(current)
                current=word
        if current:out.append(current)
    return out
def multiline(draw,txt,x,y,f,color,max_width,space=12):
    lines=wrap(draw,txt,f,max_width)
    bounds=draw.textbbox((0,0),'Ag',font=f)
    step=bounds[3]-bounds[1]+space
    for line in lines:
        if line:draw.text((x,y),line,font=f,fill=color)
        y+=step
    return y
cards=[{"k":"01 / 07 | ESCOPO NACIONAL","h":"AGORA, O\nBRASIL INTEIRO.","d":"Atualizamos a auditoria do segundo turno: 27 UFs e os votos no exterior.","fact":"Não extrapolamos mais os dados de MG e PE."},{"k":"02 / 07 | ORIGEM","h":"168 PACOTES\nOFICIAIS.","d":"56 arquivos GEDAI e 112 arquivos de correspondências e BUs.","fact":"Os 168 hashes SHA-512 coincidiram com as referências oficiais."},{"k":"03 / 07 | CONFERÊNCIA","h":"499.207\nSEÇÕES.","d":"O identificador da urna efetivada coincidiu com o informado nos BUs publicados em todas as seções analisadas.","fact":"Zero divergências de IDENTIFICAÇÃO. Não é recontagem de votos."},{"k":"04 / 07 | PREPARAÇÃO","h":"350 MUDANÇAS\nNA PREVISÃO.","d":"Identificadores das urnas esperadas mudaram entre 24 e 25 de outubro nas 27 UFs e no exterior.","fact":"Mudança na previsão não significa voto adulterado."},{"k":"05 / 07 | CONTINGÊNCIA","h":"2.686 DIFERENÇAS\nNO EQUIPAMENTO.","d":"Entre o identificador previsto em 25/10 e o efetivamente publicado após a votação.","fact":"Precisamos dos registros e motivos de cada contingência."},{"k":"06 / 07 | LOGS","h":"675 ARQUIVOS\nGEDAI MUDARAM.","d":"O conteúdo de arquivos internos difere entre as versões de 24 e 25/10.","fact":"Diferença entre versões exige contexto. Não é prova de fraude."},{"k":"07 / 07 | PRÓXIMOS TESTES","h":"CONSISTÊNCIA\nNÃO É AUDITORIA\nCOMPLETA.","d":"Faltam confrontar RDVs, BUs impressos independentes, atas, logs e registros administrativos.","fact":"Metodologia, dados por UF e pedido ao TSE no GitHub do FatoVia."}]
for idx,c in enumerate(cards,1):
    im=Image.new('RGB',(W,H),CREAM);draw=ImageDraw.Draw(im)
    dark=idx in (1,7)
    if dark:draw.rectangle((0,0,W,H),fill=DEEP)
    txt=CREAM if dark else INK;sub=MINT if dark else SUB;accent=MINT if dark else DEEP
    draw.rectangle((60,60,1020,69),fill=accent)
    draw.text((65,109),'FATOVIA',font=font(43,heavy=True),fill=txt)
    draw.text((65,193),c['k'],font=font(23,bold=True),fill=sub)
    y=285
    if idx in (3,4,5):
        digit,label=({3:('30','correspondências alteradas'),4:('268','diferenças previsto × efetivado'),5:('0','divergências de identificação no BU')})[idx]
        draw.text((64,281),digit,font=font(173,heavy=True),fill=accent)
        draw.text((70,476),label.upper(),font=font(22,bold=True),fill=sub)
        y=554
    y=multiline(draw,c['h'],64,y,font(68 if idx not in (3,4,5) else 57,heavy=True),txt,W-128,17)+38
    multiline(draw,c['d'],66,y,font(34),txt,W-140,15)
    draw.rounded_rectangle((61,1078,1019,1226),radius=22,outline=accent,width=3)
    multiline(draw,c['fact'],91,1113,font(27,bold=True),txt,W-183,12)
    draw.rectangle((62,1266,1018,1268),fill=accent)
    draw.text((64,1287),'FONTE: DADOS ABERTOS DO TSE + ANÁLISE REPRODUZÍVEL',font=font(17,bold=True),fill=sub)
    draw.text((822,1287),'@fato.via',font=font(20,bold=True),fill=sub)
    im.save(DEST/f'card_{idx:02}.jpg',quality=91,subsampling=0,optimize=True)
print('Gerados',len(cards),'arquivos JPEG')
