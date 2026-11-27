"""Episode-specific procedural art; no imported legacy character or scene functions."""
import math, random
from PIL import Image
from .v5_legacy import visual_base as v
v.W,v.H,v.S=1620,2880,3
D,C,G,Y=v.D,v.C,v.G,v.Y
PROPS={"economia":"money","saude":"health","educacao":"book","seguranca":"shield","ambiente":"leaf","tecnologia":"screen","infraestrutura":"transport"}
PALETTES=[("#c6d9cf","#355d68","#bb6e4e"),("#e6d4b2","#376959","#a05a69"),("#d9d7ea","#4d597f","#ad7543"),("#d3e4be","#4e6750","#8c5c8d")]
def prop(a,x,y,k,kind,t):
    a.e(x-60*k,y+45*k,120*k,15*k,"#a4b4a2")
    if kind=="money":
        for j in range(3):a.box(x-64*k+j*10*k,y-39*k-j*12*k,105*k,57*k,"#7ca98c",5*k);a.text(x-12*k+j*10*k,y-10*k-j*12*k,"R$",17*k,D)
    elif kind=="health":
        a.box(x-53*k,y-60*k,106*k,108*k,"#f3e9d3",9*k);a.box(x-10*k,y-39*k,20*k,66*k,"#b95a57",3*k);a.box(x-32*k,y-15*k,64*k,20*k,"#b95a57",3*k)
    elif kind=="book":
        a.poly([(x-67*k,y-42*k),(x,y-26*k),(x+67*k,y-42*k),(x+67*k,y+45*k),(x,y+30*k),(x-67*k,y+45*k)],"#e0b36b")
        a.line([(x,y-26*k),(x,y+30*k)],D,3*k)
        for s in (-1,1):
            for j in range(3):a.line([(x+s*12*k,y-12*k+j*16*k),(x+s*54*k,y-22*k+j*16*k)],D,2*k)
    elif kind=="shield":
        a.poly([(x-53*k,y-50*k),(x+53*k,y-50*k),(x+46*k,y+15*k),(x,y+55*k),(x-46*k,y+15*k)],"#547a85");a.line([(x-20*k,y),(x-6*k,y+15*k),(x+22*k,y-18*k)],C,5*k)
    elif kind=="leaf":
        a.e(x-50*k,y-48*k,100*k,88*k,"#6a9c67");a.line([(x-38*k,y+35*k),(x+35*k,y-29*k)],D,4*k)
    elif kind=="screen":
        a.box(x-66*k,y-47*k,132*k,88*k,D,8*k);a.box(x-56*k,y-37*k,112*k,64*k,"#a0d0c1",4*k);a.box(x-20*k,y+41*k,40*k,12*k,D,3*k);a.e(x-4*k+math.sin(t)*30*k,y-8*k,8*k,8*k,G)
    else:
        a.box(x-67*k,y-32*k,134*k,65*k,"#547a85",10*k)
        for j in range(3):a.box(x-54*k+j*38*k,y-23*k,29*k,23*k,C,3*k)
        for s in (-1,1):a.e(x+s*40*k-11*k,y+23*k,22*k,22*k,D)
def human(a,x,y,k,seed,role,t,walk=False):
    rng=random.Random(seed+str(role))
    skin=rng.choice(["#92563b","#c68d66","#e1b18b","#734b36"]);hair=rng.choice(["#2f2926","#624334","#9d9b92"]);shirt=rng.choice(["#a55250","#365c80","#56826b","#c49a4f","#795f88"])
    h=rng.choice([0,1,2]);s=math.sin(t*4)*10*k if walk else 2*math.sin(t*2)*k
    for sign in (-1,1):
        a.line([(x+sign*14*k,y-75*k),(x+sign*18*k+s*.4,y-36*k),(x+sign*(18*k+s),y)],D,16*k)
    a.poly([(x-32*k,y-151*k),(x+32*k,y-151*k),(x+25*k,y-71*k),(x-25*k,y-71*k)],shirt)
    for sign in (-1,1):
        a.line([(x+sign*30*k,y-140*k),(x+sign*44*k,y-105*k),(x+sign*(34*k+s),y-88*k)],skin,13*k)
    cy=y-180*k
    if h==0:a.e(x-32*k,cy-29*k,64*k,68*k,hair)
    if h==1:
        for j in range(7):a.e(x-31*k+j*8*k,cy-29*k,17*k,20*k,hair)
    a.e(x-25*k,cy-25*k,50*k,55*k,skin)
    a.e(x-26*k,cy-29*k,52*k,(13 if h==2 else 20)*k,hair)
    for sign in (-1,1):a.e(x+sign*10*k-2*k,cy,4*k,4*k,D)
    a.line([(x-5*k,cy+15*k),(x+5*k,cy+15*k)],D,2*k)
    if h==2:
        for sign in (-1,1):a.box(x+sign*11*k-10*k,cy-4*k,20*k,12*k,None,2*k,D)
def document(a,x,y,w,h,title,seed):
    a.box(x+7,y+9,w,h,"#a4b4a2",8);a.box(x,y,w,h,C,8);a.box(x,y,w,50,G,8);a.text(x+w/2,y+25,title,19,C)
    for j in range(5):a.line([(x+20,y+78+j*33),(x+w-20-(j%3)*20,y+78+j*33)],"#b0baad",3)
def scene(plan,i,t):
    seed=plan["seed"];bg,accent,contrast=PALETTES[int(seed[:3],16)%len(PALETTES)]
    kind=PROPS[plan["topic"]];a=v.A(Image.new("RGB",(1620,2880),bg));q=min(1,t/2)
    def p(x,y,k=1):prop(a,x,y,k,kind,t)
    def h(x,y,k=1,role=0,walk=False):human(a,x,y,k,seed,role,t,walk)
    if i==0:
        a.box(0,525,540,225,accent);h(250,665,2.2,0);p(380,375,1.25)
    elif i==1:
        a.box(0,580,540,170,contrast);p(270,440,2.3);a.line([(540,650),(382,544),(345,495+math.sin(t)*5)],"#bd8b68",25)
    elif i==2:
        for j in range(5):
            x=j*112;ht=155+int(seed[j],16)*9;a.box(x,565-ht,105,ht,accent,3)
            for k in range(3):a.box(x+12+k*27,500-ht,15,35,C)
        a.box(0,565,540,180,"#aeb9a3");h(95+70*q,710,1.5,0,True);h(435-55*q,710,1.5,1,True)
    elif i==3:
        document(a,80,240,380,420,plan["source"]["title"],seed);p(400,630,.65)
    elif i==4:
        document(a,35,220,315,420,"PROPOSTA",seed);a.e(220,360,190,190,D);a.e(230,370,170,170,C);a.line([(384,520),(475,610)],D,25);p(315,448,.65)
    elif i==5:
        a.box(40,305,180,215,C,15);a.box(320,305,180,215,C,15);p(130,408,.9);p(410,408,.9)
        a.line([(230,414),(310,414)],G,6);a.poly([(310,414),(292,399),(292,429)],G);a.e(230+60*q,410,8,8,Y)
        a.text(130,560,"ANTES",18);a.text(410,560,"HIPÓTESE",18)
    elif i==6:
        a.box(0,565,540,175,accent);p(110,500,.95);p(405,500,.95);h(270,600,1.7,1)
        a.line([(115,375),(270,300),(405,375)],D,4)
    elif i==7:
        a.box(0,540,540,200,"#aabca8");a.box(45,240,450,60,C,12);a.text(270,270,"PROPOSTA ≠ LEI EM VIGOR",20);h(150,690,1.65,0);h(385,690,1.65,1)
    elif i==8:
        for j in range(3):a.box(37+j*165,310,136,230,C,9);p(105+j*165,415,.65);a.text(105+j*165,575,["CUSTO","ACESSO","EXECUÇÃO"][j],17)
        a.line([(105,615),(270,670),(435,615)],D,3)
    elif i==9:
        a.box(0,300,260,375,accent,8);a.box(280,250,260,425,contrast,8);h(130,630,1.4,0);h(410,630,1.7,2);p(130,345,.6);p(410,305,.6)
    elif i==10:
        a.box(40,240,460,330,C,15);a.text(270,320,"O QUE FALTA SABER?",25)
        a.e(190,380,160,160,accent);a.text(270,460,"?",65,C);h(112,715,1.25,0)
    elif i==11:
        for j in range(3):
            x=22+j*173;a.box(x,265,150,390,[accent,contrast,G][j],12);h(x+75,605,1.1,j)
        p(270,720,.55)
    else:raise ValueError("unknown scene")
    return a.im.resize((1080,1920),Image.Resampling.LANCZOS)
