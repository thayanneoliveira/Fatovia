from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W,H=1080,1350
OUT=Path('fatovia-instagram/promessas_e_entregas_2026')
OUT.mkdir(parents=True,exist_ok=True)
DARK='#123D32';LIGHT='#F5F0E5';MINT='#C7E0CA';INK='#193A30';MUTED='#61776C';LINE='#A9C7B5'
SER='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
SANS='/usr/share/fonts/truetype/lato/Lato-Regular.ttf'
HEAVY='/usr/share/fonts/truetype/lato/Lato-Heavy.ttf'
MED='/usr/share/fonts/truetype/lato/Lato-Semibold.ttf'
def ft(n,kind='regular'):return ImageFont.truetype({'regular':SANS,'heavy':HEAVY,'medium':MED,'serif':SER}[kind],n)
def write(d,t,x,y,n,fg,width=925,lead=14,kind='regular',limit=None):
    while True:
        font=ft(n,kind)
        lines=[]
        for para in t.split('\n'):
            if not para:lines.append('');continue
            s=''
            for word in para.split(' '):
                candidate=(s+' '+word).strip()
                if d.textbbox((0,0),candidate,font=font)[2]<=width or not s:s=candidate
                else:lines.append(s);s=word
            if s:lines.append(s)
        step=n+lead
        if limit is None or step*len(lines)<=limit or n<=20:break
        n-=2
    for line in lines:
        if line:d.text((x,y),line,font=font,fill=fg)
        y+=step
    return y

cards=[
 dict(k='O JOGO COMEÇA DEPOIS DO VOTO',title='GANHOU.\nE AGORA?',body='A promessa de campanha não se transforma automaticamente em política pública.',note='O presidente foi eleito. Mas quem realmente decide o que ele pode entregar?',dark=True),
 dict(k='A MECÂNICA DAS PROMESSAS',title='UMA PROMESSA.\nTRÊS PERGUNTAS.',body='01  Quem pode decidir?\n02  Precisa de lei?\n03  De onde vem a verba?',note='Uma proposta pode precisar de uma, duas ou três dessas etapas.',dark=False),
 dict(k='O QUE CABE AO PRESIDENTE',title='EXISTE PODER\nDE DECISÃO.\nMAS TEM LIMITE.',body='DIRIGIR: a administração federal.\nNOMEAR: ministros de Estado.\nREGULAMENTAR: leis, dentro dos limites legais.',note='Base legal: Constituição Federal, art. 84.',dark=False),
 dict(k='O PAPEL DO CONGRESSO',title='PROPOR NÃO\nÉ APROVAR.',body='O governo pode apresentar projetos de lei. Deputados e senadores podem discutir, modificar e votar.\n\nMedidas provisórias exigem relevância e urgência e dependem do Congresso para continuar valendo.',note='Base legal: Constituição, arts. 61, 62 e 84.',dark=True),
 dict(k='A PERGUNTA SOBRE DINHEIRO',title='SEM RECURSOS,\nNÃO HÁ ENTREGA.',body='O Executivo propõe PPA, LDO e LOA. O Congresso analisa e aprova. O Executivo executa conforme a lei e as regras fiscais.',note='Ter dotação orçamentária não significa execução automática.',dark=False),
 dict(k='COMO COBRAR DE VERDADE',title='DESCULPA OU\nOBSTÁCULO REAL?',body='01  Houve proposta formal?\n02  Foi aprovada?\n03  Havia recursos?\n04  Foi executada?\n05  O que mudou na prática?',note='Projeto apresentado não é serviço entregue. Resultado exige evidência.',dark=False),
 dict(k='O CRITÉRIO VALE PARA TODOS',title='SEM TORCIDA.\nCOM COBRANÇA.',body='Promessa registrada.\nDecisão identificada.\nOrçamento conferido.\nResultado comprovado.',note='Salve este roteiro. Ele vale para qualquer governo.',dark=True)
]
for i,c in enumerate(cards,1):
    dark=c['dark']
    bg=DARK if dark else LIGHT
    fg=LIGHT if dark else INK
    accent=MINT if dark else DARK
    sub=MINT if dark else MUTED
    im=Image.new('RGB',(W,H),bg)
    d=ImageDraw.Draw(im)
    d.rectangle((64,62,1016,70),fill=accent)
    d.text((67,112),'FATOVIA',font=ft(48,'heavy'),fill=fg)
    d.text((782,127),'PÓS-ELEIÇÃO 2026',font=ft(20,'heavy'),fill=sub)
    d.text((67,218),c['k'],font=ft(23,'heavy'),fill=sub)
    d.rounded_rectangle((892,204,1016,261),radius=25,outline=accent,width=2)
    d.text((909,224),f'{i:02d}/07',font=ft(21,'heavy'),fill=fg)
    title=write(d,c['title'],65,327,76,fg,925,16,'serif',315)
    d.rectangle((69,max(640,title+22),300,max(646,title+28)),fill=accent)
    body_y=max(708,title+86)
    body_size=39 if i in (1,4,5) else (36 if i in (2,3,6) else 43)
    write(d,c['body'],69,body_y,body_size,fg,915,16,'regular',330)
    d.rounded_rectangle((64,1092,1016,1230),radius=24,outline=accent,width=3)
    write(d,c['note'],91,1125,29,fg,890,12,'medium',100)
    d.rectangle((64,1276,1016,1279),fill=accent)
    d.text((67,1300),'FONTES: CONSTITUIÇÃO E CÂMARA DOS DEPUTADOS',font=ft(20,'heavy'),fill=sub)
    d.text((899,1300),'@fato.via',font=ft(20,'heavy'),fill=sub)
    out=OUT/f'card_{i:02d}.jpg'
    im.save(out,quality=92,optimize=True,subsampling=0)
    print(out,out.stat().st_size,flush=True)
