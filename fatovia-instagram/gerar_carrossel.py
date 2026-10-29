from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
W,H=1080,1350
DEST=Path('fatovia-instagram/cards');DEST.mkdir(parents=True,exist_ok=True)
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
cards=[
  dict(k='01 / 07  |  APURAÇÃO CÍVICA',h='AUDITORIA,\nNÃO ACUSAÇÃO.',d='O que um cruzamento de dados públicos revela sobre o segundo turno de 2026.',fact='Dois estados analisados. Evidências abertas. Perguntas objetivas.'),
  dict(k='02 / 07  |  MÉTODO',h='12 PACOTES\nOFICIAIS.',d='Verificamos os hashes SHA-512 dos dados usados na comparação de MG e PE.',fact='Integridade do arquivo publicado não equivale à prova de todo o processo eleitoral.'),
  dict(k='03 / 07  |  ANTES DO VOTO',h='30 MUDANÇAS\nDE URNA PREVISTA.',d='Foram 15 em MG e 15 em PE entre as correspondências divulgadas em 24 e 25 de outubro.',fact='Mudança de equipamento planejado não significa alteração de votos.'),
  dict(k='04 / 07  |  CONTINGÊNCIA',h='268 DIFERENÇAS\nNO EQUIPAMENTO.',d='Entre a previsão de 25/10 e o uso efetivo: 169 seções em MG e 99 em PE.',fact='Substituições podem ser legítimas. O que importa é a rastreabilidade.'),
  dict(k='05 / 07  |  CRUZAMENTO',h='73.480 SEÇÕES.\n0 DIVERGÊNCIAS.',d='A identificação das urnas efetivadas coincidiu com a informada nos arquivos de boletins dessas seções.',fact='Este teste não compara votos com RDV nem com BUs fotografados na seção.'),
  dict(k='06 / 07  |  RASTREABILIDADE',h='2 EVENTOS\nA ESCLARECER.',d='Em uma estação GEDAI de PE, duas linhas operacionais presentes no arquivo de 24/10 não aparecem na versão de 25/10.',fact='Referem-se à exportação e ao envio de logs, não a registros de votos.'),
  dict(k='07 / 07  |  PRÓXIMOS CONTROLES',h='O QUE AINDA\nPRECISA DE PROVA?',d='Atas de contingência, horários, justificativas, RDVs e comparações com boletins impressos.',fact='A auditoria segue inconclusiva sobre a cadeia completa. Transparência exige evidências, não suposições.')]
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
