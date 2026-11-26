import os,sys,math,json,subprocess as sp,functools,random,bisect
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
W,H,FPS=720,1280,24; S=W/540
D='#142f29'; G='#245342'; L='#a8c2a4'; C='#faf1df'; Y='#e7bc69'; T='#719783'; R='#b85e4e'; P='#cbbb9e'; SKY='#e3ead8'; INK='#233e35'
ROOT=Path(__file__).resolve().parent
@functools.lru_cache(100)
def ft(n,b=True):return ImageFont.truetype('/usr/share/fonts/truetype/lato/Lato-'+('Black' if b else 'Regular')+'.ttf',round(n*S))
@functools.lru_cache(1024)
def sprite(t,z,f,b,anchor):
 font=ft(z,b); bounds=font.getbbox(t,anchor=anchor); l,top,r,bot=bounds; im=Image.new("RGBA",(max(1,r-l+4),max(1,bot-top+4))); ImageDraw.Draw(im).text((2-l,2-top),t,font=font,fill=f,anchor=anchor);return im,l-2,top-2
@functools.lru_cache(1024)
def wrap_cache(t,z,maxw):
 lines=[];l=""
 for word in t.split():
  new=(l+" "+word).strip()
  if ft(z).getlength(new)>maxw*S and l:lines.append(l);l=word
  else:l=new
 return lines+[l]
def ease(u):u=min(1,max(0,u));return u*u*(3-2*u)
class A:
 def __init__(self,im):self.im=im;self.d=ImageDraw.Draw(im)
 def xy(self,arr):return tuple(round(x*S) for x in arr)
 def box(self,x,y,w,h,f,r=0,outline=None):
  p=self.xy((x,y,x+w,y+h)); self.d.rounded_rectangle(p,round(r*S),fill=f,outline=outline,width=max(1,round(S))) if r else self.d.rectangle(p,fill=f,outline=outline)
 def e(self,x,y,w,h,f):self.d.ellipse(self.xy((x,y,x+w,y+h)),fill=f)
 def poly(self,p,f):self.d.polygon([self.xy(x) for x in p],fill=f)
 def line(self,p,f,w=2):self.d.line([self.xy(x) for x in p],fill=f,width=max(1,round(w*S)),joint='curve')
 def text(self,x,y,t,z=24,f=D,b=True,anchor='mm'):
  im,l,top=sprite(t,z,f,b,anchor);self.im.paste(im,(round(x*S)+l,round(y*S)+top),im)
 def wrap(self,t,z,maxw):return wrap_cache(t,z,maxw)
 def headline(self,k,t,dark=False):
  self.text(32,112,k,13,Y if dark else G,anchor='lm'); self.line([(32,131),(78,131)],Y,3)
  lines=self.wrap(t,35,465)
  for i,l in enumerate(lines):self.text(32,167+i*39,l,35,C if dark else D,anchor='lm')
 def tag(self,x,y,t,f=D,bg=Y,z=17):
  w=ft(z).getlength(t)/S+26;self.box(x-w/2,y-19,w,38,bg,10);self.text(x,y,t,z,f)
@functools.lru_cache(8)
def bg(kind):
 top,bottom=({'city':('#f8edda','#c4d9c4'),'dark':('#315743','#102c26'),'room':('#f9ecda','#e2c8a0'),'paper':('#f7f1e2','#d5e1cb')})[kind]
 from PIL.ImageColor import getrgb
 a,b=np.array(getrgb(top)),np.array(getrgb(bottom));x=np.linspace(0,1,H)[:,None,None];ar=np.broadcast_to(a*(1-x)+b*x,(H,W,3)).copy();ar+=np.random.default_rng(4).normal(0,.6,(H,W,1));return Image.fromarray(np.uint8(np.clip(ar,0,255)))
def ground(a):
 a.box(0,692,540,268,'#c0c6a6'); a.box(0,718,540,26,'#ded9ba'); a.box(0,744,540,59,'#8a9c8c');a.line([(0,773),(540,773)],'#e5e2cb',2)
 for x in range(-10,540,86):a.box(x,772,35,3,C,1)
def skyline(a):
 for i,(x,y,w) in enumerate([(-12,448,82),(70,400,78),(156,468,95),(261,420,65),(334,460,79),(425,388,105)]):
  a.box(x,y,w,245,'#a7bcaa',2)
  for xx in range(x+12,x+w-8,20):
   for yy in range(y+18,673,32):a.box(xx,yy,9,14,'#d8e4d1',1)
 ground(a)
def tree(a,x,y,s=1):
 a.box(x-4*s,y-65*s,8*s,65*s,'#98724c',2);a.e(x-31*s,y-108*s,62*s,63*s,T);a.e(x-20*s,y-125*s,55*s,58*s,'#89ad85')
def building(a,x,y,w,h,kind='creche',p=1,t=0):
 # y is baseline. Shared silhouette for a coherent recurring location.
 a.e(x-15,y-14,w+30,30,'#a0ae94'); wall='#e8d3aa' if kind=='house' else '#e8d6b2'; roof=R if kind=='house' else G
 a.box(x,y-h,w,h,wall,3)
 if p<.9:
  a.box(x,y-h,w,h,'#c7a17c',2)
  for yy in range(round(y-h+13),round(y),16):
   a.line([(x,yy),(x+w,yy)],'#aa8364',1)
   for xx in range(round(x+(yy%3)*6),round(x+w),35):a.line([(xx,yy),(xx,yy+15)],'#aa8364',1)
  a.box(x+w*.36,y-h*.52,w*.27,h*.52,D)
  for j in [0,1]:a.box(x+w*(.07+.69*j),y-h*.72,w*.21,h*.28,'#556c5e')
  for j in range(4):a.line([(x+j*w/3,y-h-40),(x+j*w/3,y-h+2)],'#9a7760',3)
  a.line([(x-6,y-h),(x+w+6,y-h)],'#775d4e',6)
  if p>.45:a.poly([(x-12,y-h),(x+w*.43,y-h-64),(x+w*.66,y-h-64),(x+w+10,y-h)],roof)
  return
 if kind=='house':a.poly([(x-16,y-h),(x+w*.5,y-h-82),(x+w+16,y-h)],roof)
 else:a.box(x-9,y-h-12,w+18,27,roof,4)
 a.box(x+w*.39,y-h*.58,w*.22,h*.58,'#426455',3)
 for f in [.07,.70]:
  xx=x+w*f; a.box(xx,y-h*.77,w*.23,h*.35,'#668e88',3);a.line([(xx,y-h*.6),(xx+w*.23,y-h*.6)],C,3);a.line([(xx+w*.115,y-h*.77),(xx+w*.115,y-h*.42)],C,3)
 if kind!='house':a.box(x+w*.22,y-h-37,w*.56,44,Y,7);a.text(x+w*.5,y-h-15,'CRECHE',20,D)
 else:a.e(x+w*.39+7,y-45,6,6,Y)
def fence(a,x,y,w):
 for xx in range(int(x),int(x+w),24):a.box(xx,y-64,5,64,'#766745',1)
 a.box(x,y-54,w,5,'#766745');a.box(x,y-16,w,5,'#766745')
def person(a,x,y,s=1,who='mom',t=0,pose='stand'):
 # baseline y; articulated limbs, independent head, eyes & brows.
 child=who=='pedro'; skin='#c88c66' if who!='worker' else '#a8724f';hair='#3c342b'; shirt={'mom':'#cf9d55','pedro':'#7da78b','worker':'#d8b35e','official':'#3d6954'}.get(who,T)
 h=115*s if child else 176*s; leg=h*.34; body=h*.38; head=h*.29; swing=math.sin(t*5)*s*6 if pose=='walk' else math.sin(t*2.1)*s*2
 a.e(x-26*s,y-7*s,52*s,11*s,'#9bad92')
 for side in [-1,1]:
  hip=(x+side*10*s,y-leg);k=(x+side*12*s+side*swing,y-leg*.48);foot=(x+side*13*s-side*swing,y-3*s);a.line([hip,k,foot],'#355045',11*s);a.line([foot,(foot[0]+9*s,foot[1])],D,7*s)
 top=y-leg-body; a.box(x-22*s,top,44*s,body+7*s,shirt,11*s)
 for side in [-1,1]:
  shoulder=(x+side*19*s,top+10*s); elbow=(x+side*31*s,top+body*.48); hand=(x+side*27*s,top+body*.92+swing*side)
  if pose=='point' and side==1:elbow=(x+38*s,top+body*.12); hand=(x+59*s,top+body*.02+math.sin(t*2)*3*s)
  if pose=='sad':elbow=(x+side*27*s,top+body*.64);hand=(x+side*17*s,top+body*.96)
  a.line([shoulder,elbow],shirt,12*s);a.line([elbow,hand],skin,8*s);a.e(hand[0]-4*s,hand[1]-4*s,8*s,8*s,skin)
 cy=top-head*.46+math.sin(t*1.8)*1.3*s; r=head*.47
 if who=='mom':
  a.e(x-r*1.18,cy-r*1.10,r*.72,head*1.42,hair);a.e(x+r*.48,cy-r*1.10,r*.72,head*1.42,hair);a.e(x-r*1.12,cy-r*1.14,r*2.24,r*1.4,hair)
 a.e(x-r,cy-r,r*2,r*2,skin);a.e(x-r,cy-r,r*2,r*.84,hair)
 if who=='worker':a.box(x-r-3*s,cy-r-3*s,r*2+6*s,9*s,Y,4*s);a.e(x-r,cy-r-10*s,r*2,17*s,Y)
 blink=(t%4.1)>3.95
 for xx in [-.34,.34]:a.e(x+r*xx-1.6*s,cy-1*s,3.2*s,(1 if blink else 4)*s,D)
 if pose=='sad':a.line([(x-5*s,cy+9*s),(x,cy+6*s),(x+5*s,cy+9*s)],hair,1.5*s)
 else:a.line([(x-5*s,cy+7*s),(x,cy+9*s),(x+5*s,cy+7*s)],hair,1.5*s)
 if child:a.box(x-23*s,top+8*s,8*s,body*.65,'#b05f4d',3*s)
def coin(a,x,y,s=1):
 a.e(x-20*s,y-9*s,40*s,18*s,'#ad7e3e');a.e(x-20*s,y-13*s,40*s,17*s,Y);a.text(x,y-4*s,'R$',10*s,D)
def stack(a,x,y,n,t=0):
 for i in range(n):coin(a,x,y-i*9,1.25)
def doc(a,x,y,w,h,title,lines,t=0):
 a.box(x+6,y+9,w,h,'#b0bdab',10);a.box(x,y,w,h,C,10);a.box(x,y,w,44,G,10);a.text(x+15,y+22,title,17,C,anchor='lm')
 for i,(label,val) in enumerate(lines):
  yy=y+75+i*58;a.text(x+16,yy,label,14,G,anchor='lm');a.text(x+w-16,yy+18,val,18,D,anchor='rm');a.line([(x+15,yy+38),(x+w-15,yy+38)],'#d5ddcf',1)
def crane(a,x,y,t):
 a.line([(x,y),(x,y-238),(x+190,y-238)],'#b48a47',8);a.line([(x-50,y-238),(x+135,y-238)],Y,8)
 for j in range(10):a.line([(x-10,y-j*22),(x+10,y-(j+1)*22)],'#96753d',2)
 a.line([(x+124,y-237),(x+124,y-125+8*math.sin(t))],D,2);a.box(x+105,y-125+8*math.sin(t),38,16,'#9b7653',2)
# 22 scenes aligned with the approved groups, in sequence.
HEADS=[('01 / UMA PERGUNTA','Você pagaria por isso?'),('02 / O SEU DINHEIRO','O sonho da casa própria'),('03 / OBRA PARADA','E se a obra parar?'),('04 / DINHEIRO PÚBLICO','Agora, imagine uma cidade'),('05 / A HISTÓRIA DE PEDRO','Pedro precisa de uma vaga'),('06 / A PROMESSA','Uma nova creche'),('07 / O TEMPO PASSA','A infância não espera'),('08 / O PROBLEMA','Por que uma obra para?'),('09 / O PLANEJAMENTO','Antes do primeiro tijolo'),('10 / IMPREVISTOS','O custo cresce'),('11 / POSSÍVEIS CAUSAS','Nem toda paralisação é igual'),('12 / NÃO CONFUNDA','Suspeita não é prova'),('13 / CUSTO INVISÍVEL','O prejuízo que ninguém vê'),('14 / CONSEQUÊNCIA','Uma família também perde'),('15 / O QUE NÃO FOI ENTREGUE','O serviço que faltou'),('16 / PREVENÇÃO','Planejar antes de construir'),('17 / FISCALIZAÇÃO','Você pode investigar'),('18 / QUATRO PERGUNTAS','O que procurar?'),('19 / FONTE PÚBLICA','Consulte as obras do MEC'),('20 / REFLEXÃO','Progresso ou promessa?'),('21 / RESULTADO','Entregar muda vidas'),('22 / FATOVIA','Entender é fiscalizar')]
# Each visual group includes count of sentence-level narration units. Derived from approved text.
COUNTS=[1,2,2,2,3,2,3,1,1,3,1,2,1,2,3,2,2,1,1,1,2,2]
def scene(i,t,d):
 u=min(1,t/max(d,.1)); q=ease(u); dark=i in (7,10,11,12,14,17,19,21);kind='dark' if dark else 'room' if i in (1,13) else 'paper' if i in (8,9,15,16,18) else 'city';a=A(bg(kind).copy());a.headline(*HEADS[i],dark)
 if i in (0,1,2,3):
  if i!=1:skyline(a)
  if i==0:building(a,107,683,326,234,'house',.45);fence(a,88,702,360);person(a,90,725,1.13,'mom',t,'sad');a.tag(270,339,'PAGA. NÃO ENTREGUE.',D,Y)
  elif i==1:
   a.box(36,300,468,395,'#e4d2b2',20);building(a,189,595,250,169,'house',1);person(a,100,690,1.45,'mom',t,'point');stack(a,275,693,4+int(q*9));a.tag(350,690,'ECONOMIAS')
  elif i==2:building(a,105,685,330,235,'house',.64);fence(a,85,709,350);person(a,83,728,1.1,'mom',t,'sad');a.tag(275,340,'OBRA INTERROMPIDA',C,R)
  else:
   building(a,90,680,170,142,'house',.6);building(a,302,680,170,145,'creche',.55);stack(a,270,742,9);a.tag(270,326,'DINHEIRO DE TODOS');a.line([(270,365),(270,480)],G,3)
 elif i in (4,5,6,14,20):
  skyline(a);tree(a,34,695,1);tree(a,502,695,.9)
  if i==4:building(a,193,685,280,200,'creche',1);fence(a,186,708,290);person(a,92,743,1.65,'mom',t,'sad');person(a,166,743,1.5,'pedro',t,'sad');a.tag(330,381,'SEM VAGA',C,R)
  elif i==5:building(a,128,685,284,200,'creche',1);person(a,83,733,1.25,'official',t,'point');person(a,448,729,1.25,'mom',t,'stand');a.tag(270,347,'100 VAGAS PREVISTAS');
  elif i==6:building(a,125,690,300,198,'creche',.55);fence(a,111,707,330);person(a,80,743,1.1,'mom',t,'sad');person(a,174,743,1.15+q*.8,'pedro',t,'sad');a.tag(270,347,'MESES  →  ANOS');a.box(210,402,120,7,P,3);a.box(210,402,120*q,7,R,3)
  elif i==14:building(a,140,690,265,190,'creche',.55);fence(a,125,711,300);person(a,82,741,1.35,'mom',t,'sad');person(a,459,740,1.35,'pedro',t,'sad');a.tag(270,374,'SERVIÇO NÃO ENTREGUE',C,R)
  else:building(a,120,690,300,205,'creche',1);person(a,70,746,1.3,'mom',t,'walk');person(a,195+25*q,733,1.15,'pedro',t,'walk');person(a,344,730,1.1,'pedro',t+.6,'walk');person(a,464,740,1.2,'mom',t+.8,'stand');a.tag(270,361,'SERVIÇO EM FUNCIONAMENTO')
 elif i==7:
  building(a,130,697,280,220,'creche',.5);a.tag(270,338,'?');a.text(270,745,'O QUE ACONTECEU?',20,C)
 elif i in (8,9):
  a.box(35,300,470,408,'#d6e0cc',12);a.box(59,323,422,247,'#edf1dc',9)
  for xx in range(75,477,22):a.line([(xx,333),(xx,550)],'#d5decb',1)
  for yy in range(333,560,22):a.line([(75,yy),(465,yy)],'#d5decb',1)
  a.line([(95,527),(95,392),(269,350),(440,392),(440,527),(95,527)],G,3);a.line([(269,350),(269,527)],G,3);a.line([(95,445),(440,445)],G,3)
  if i==9:
   for k,st in enumerate(['DINHEIRO','MATERIAL','TEMPO']):a.tag(110+159*k,630+12*(1-ease((u-k*.1)/.5)),st,C,R,14)
  else:a.tag(270,626,'PROJETO + TERRENO');person(a,78,740,1.05,'worker',t,'point')
 elif i==10:
  for j,(head,description) in enumerate([('RECURSOS','Dinheiro insuficiente'),('EMPRESA','Problemas no contrato'),('IRREGULARIDADES','Possível desvio')]):
   y=307+123*j+15*(1-ease((u-j*.12)/.45));a.box(44,y,452,102,'#345b4a',12);a.e(61,y+20,56,56,Y);a.text(89,y+48,str(j+1),25,D);a.text(135,y+32,head,19,C,anchor='lm');a.text(135,y+66,description,18,L,False,'lm')
 elif i==11:
  doc(a,86,326,305,330,'DOCUMENTOS',[('Contrato','Verificar'),('Pagamentos','Conferir'),('Motivo da pausa','Investigar')]);x=389+8*math.sin(t*1.6);y=570+8*math.cos(t*1.6);a.e(x-55,y-55,110,110,Y);a.e(x-43,y-43,86,86,'#496c59');a.line([(x+35,y+35),(x+92,y+93)],Y,18);a.tag(270,717,'SUSPEITA ≠ PROVA')
 elif i==12:
  a.box(65,335,410,340,'#42634f',18);a.text(270,377,'PREJUÍZO VISÍVEL',19,C);stack(a,270,540,12);a.line([(89,569),(451,569)],L);a.text(270,610,'E O PREJUÍZO INVISÍVEL?',23,Y);a.tag(270,728,'O SERVIÇO QUE NÃO CHEGOU')
 elif i==13:
  a.box(0,598,540,174,'#e0c39c');a.box(30,323,172,173,'#b8cfc1',6);a.line([(30,408),(202,408)],C,5);a.line([(116,323),(116,496)],C,5);a.box(274,514,233,12,'#846648',3);a.box(289,526,12,151,'#846648');a.box(480,526,12,151,'#846648');a.box(319,444,102,68,G,8);a.box(331,455,78,47,'#a6c4b2',3);person(a,133,723,1.7,'mom',t,'sad');person(a,240,724,1.45,'pedro',t,'stand');a.tag(374,369,'TRABALHO E RENDA',C,R)
 elif i==15:
  doc(a,61,292,418,400,'ANTES DA OBRA',[('Necessidade','É prioridade?'),('Orçamento','Quanto custa?'),('Recursos','Há verba até o fim?'),('Manutenção','Como vai funcionar?')]);
  for j in range(4):
   if u>(j+1)*.13:a.text(69,370+j*58,'✓',18,G)
 elif i in (16,18):
  label='PORTAL DA TRANSPARÊNCIA' if i==16 else 'PAINEL DE OBRAS DO MEC';a.box(49,297,442,371,D,18);a.box(65,319,410,320,C,8);a.box(65,319,410,49,G,7);a.text(270,344,label,17,C);a.box(86,387,368,39,'#d9e2d1',8);a.text(102,406,'Buscar obra, município...',16,G,False,'lm');
  for j,l in enumerate(['Obra: creche (exemplo)','Situação: consultar','Valor: consultar','Prazo: consultar']):
   yy=452+j*42;a.text(102,yy,l,17,D,False,'lm');a.line([(92,yy+19),(448,yy+19)],'#d4dccd')
  a.box(200,670,140,14,G,4);a.tag(270,721,'PÁGINA ILUSTRATIVA')
 elif i==17:
  for j,(n,l) in enumerate(enumerate(['Quanto deveria custar?','Quanto já foi pago?','Quem foi contratado?','Quando seria entregue?'],1)):
   y=315+96*j;a.box(36,y,468,78,'#365e4b',12);a.e(48,y+15,48,48,Y);a.text(72,y+39,str(n),23,D);a.text(110,y+39,l,23,C,anchor='lm')
 elif i==19:
  for j in range(10):
   x=72+(j%5)*88;y=365+(j//5)*83;a.box(x-28,y-23,56,46,L,4);a.poly([(x-34,y-22),(x,y-45),(x+34,y-22)],Y);a.box(x-7,y-4,14,27,G)
  a.text(270,508,'10 ANUNCIADAS',23,C)
  for j in range(10):
   x=72+(j%5)*88;y=571+(j//5)*68;a.box(x-26,y-20,52,40,'#9b8871',3);a.line([(x-22,y-10),(x+22,y+14)],R,4);a.line([(x-22,y+14),(x+22,y-10)],R,4)
  a.text(270,696,'10 INACABADAS',23,Y)
 elif i==21:
  a.box(207,314,126,126,Y,22);a.text(270,377,'F',96,D);a.text(270,487,'FATOVIA',48,C);a.text(270,546,'COMPREENDER. QUESTIONAR.',17,L);a.text(270,578,'VERIFICAR. FISCALIZAR.',17,L);a.text(270,671,'O resultado importa.',28,Y);a.text(270,722,'FONTES PARA CONSULTA',12,L);a.text(270,747,'Portal da Transparência • MEC',16,C)
 return a.im

def overlay(im,now,duration,caption):
 a=A(im);a.box(0,0,540,77,D);a.box(28,19,34,35,Y,7);a.text(45,36,'F',24,D);a.text(72,36,'FATOVIA',24,C,anchor='lm');a.text(508,36,'CIDADANIA / 02',12,L,anchor='rm');a.box(28,66,484,3,T,1);a.box(28,66,484*now/duration,3,Y,1)
 if caption:
  z=26;lines=a.wrap(caption,z,448)
  while len(lines)>4 and z>20:z-=1;lines=a.wrap(caption,z,448)
  boxh=max(88,len(lines)*(z+5)+28);y=831-boxh/2
  a.box(24,y,492,boxh,D,14)
  for j,l in enumerate(lines):a.text(270,y+17+z/2+j*(z+5),l,z,C if j<len(lines)-1 else Y)
 a.text(30,930,'EXEMPLO FICTÍCIO • FISCALIZAÇÃO CIDADÃ',11,C if im.getpixel((0,int(910*S)))[0]<100 else D,anchor='lm')
 return im

@functools.lru_cache(128)
def split_caption(s):
 words=s.split(); chunks=[]; current=[]
 for w in words:
  current.append(w)
  if len(current)>=11 or (len(current)>=6 and w.endswith((',',':',';'))):
   chunks.append(' '.join(current));current=[]
 if current:chunks.append(' '.join(current))
 if len(chunks)>1 and len(chunks[-1].split())<4:
  tail=chunks.pop();chunks[-1]+=' '+tail
 weights=[max(1,len(x)) for x in chunks];total=sum(weights);edges=np.cumsum(weights)/total
 return chunks,edges

def active_caption(phrase,now):
 if now>phrase['end']+.08:return ''
 chunks,edges=split_caption(phrase['caption']);u=(now-phrase['start'])/max(.01,phrase['end']-phrase['start']);return chunks[min(len(chunks)-1,bisect.bisect_right(edges,u))]

def main():
 data=json.loads((ROOT/'narracao.json').read_text());phr=data['phrases'];dur=data['duration'];print('phrases',len(phr),'counts',sum(COUNTS),'duration',dur,flush=True)
 assert len(phr)==sum(COUNTS),(len(phr),sum(COUNTS))
 starts=[x['start'] for x in phr];groups=[];cur=0
 for count in COUNTS:groups.append(phr[cur]['start']);cur+=count
 groups.append(dur)
 # render once at full frame-rate with animated positions, synchronized to lossless narration
 target=ROOT/'fatovia_creche.mp4';frames=math.ceil(dur*FPS)
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(ROOT/'narracao.wav'),'-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-shortest',str(target)]
 p=sp.Popen(cmd,stdin=sp.PIPE);prev=-1;thumbs=[]
 for f in range(frames):
  now=f/FPS;i=min(len(COUNTS)-1,bisect.bisect_right(groups,now)-1);j=max(0,bisect.bisect_right(starts,now)-1);caption=active_caption(phr[j],now);im=scene(i,now-groups[i],groups[i+1]-groups[i]);im=overlay(im,now,dur,caption)
  if i!=prev:
   thumb=im.copy();thumb.thumbnail((180,320));thumbs.append(thumb);print('scene',i+1,'/',len(COUNTS),flush=True);prev=i
   if i==0:im.save(ROOT/'capa.png')
  p.stdin.write(im.tobytes())
 p.stdin.close();assert p.wait()==0
 sheet=Image.new('RGB',(180*5,320*math.ceil(len(thumbs)/5)),D)
 for i,im in enumerate(thumbs):sheet.paste(im,((i%5)*180,(i//5)*320))
 sheet.save(ROOT/'storyboard.jpg',quality=90)
if __name__=='__main__':main()