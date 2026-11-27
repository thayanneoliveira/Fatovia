"""New episode-specific art direction; no legacy people or scene assets."""
import math
from PIL import Image
from visual_base import A
W,H=1080,1920
INK='#203e36'; C='#f9efdc'; G='#366854'; S='#adc5ad'; Y='#e7b45f'; T='#b96650'; B='#39586b'; P='#cba986'; N='#f0dfc0'; WHITE='#fff7e8'
def canvas(bg):
    return A(Image.new('RGB',(1620,2880),bg))
def rect(a,x,y,w,h,c,r=0):a.box(x,y,w,h,c,r)
def oval(a,x,y,w,h,c):a.e(x,y,w,h,c)
def line(a,p,c,w=3):a.line(p,c,w)
def text(a,x,y,s,n=23,c=INK):a.text(x,y,s,n,c)
def bread(a,x,y,k=1):
    oval(a,x-38*k,y-16*k,76*k,35*k,'#a86334')
    oval(a,x-38*k,y-23*k,76*k,34*k,'#dc9c50')
    for i in (-18,0,18):line(a,[(x+(i-5)*k,y-15*k),(x+(i+5)*k,y-5*k)],'#f6d297',2.5*k)
def bag(a,x,y,k=1):
    a.poly([(x-42*k,y+55*k),(x-36*k,y-47*k),(x+35*k,y-52*k),(x+47*k,y+55*k)],'#c69860')
    line(a,[(x-35*k,y-35*k),(x+35*k,y-40*k)],'#9b7148',3*k)
    text(a,x,y+4*k,'PÃO',17*k,INK)
def wheel(a,x,y,r=21):
    oval(a,x-r,y-r,2*r,2*r,INK);oval(a,x-r*.48,y-r*.48,r*.96,r*.96,S)
def person(a,x,y,k,who,t,pose='stand',work=False):
    # Original faces, silhouettes, colours, hairstyles and attire for this episode.
    skin,hair,shirt,pants={'ana':('#965a40','#30271f',T,'#344e48'),'carlos':('#ca9b75','#a9aaa2',B,'#46554b'),'buyer':('#be8b62','#3b302b',Y,'#425665')}[who]
    if pose=='sit':
        line(a,[(x-15*k,y-65*k),(x+20*k,y-35*k),(x+18*k,y)],pants,18*k)
        line(a,[(x+15*k,y-65*k),(x+43*k,y-35*k),(x+43*k,y)],pants,18*k)
    else:
        step=math.sin(t*5)*13*k if pose=='walk' else 0
        for side in (-1,1):
            foot=x+side*(18*k+step)
            line(a,[(x+side*15*k,y-80*k),(x+side*19*k+step*.45,y-38*k),(foot,y-5*k)],pants,19*k)
            line(a,[(foot-8*k,y-4*k),(foot+12*k,y-4*k)],INK,8*k)
    yy=y-158*k
    a.poly([(x-34*k,yy),(x+34*k,yy),(x+28*k,y-72*k),(x-29*k,y-72*k)],shirt)
    if work:
        apron='#813e33' if who=='ana' else '#223d50'
        rect(a,x-20*k,yy+12*k,40*k,66*k,apron,4*k)
        line(a,[(x-15*k,yy+13*k),(x-10*k,yy-2*k),(x+10*k,yy-2*k),(x+15*k,yy+13*k)],C,2*k)
        rect(a,x-10*k,yy+45*k,20*k,16*k,shirt,2*k)
    for s in (-1,1):
        sh=(x+s*30*k,yy+10*k)
        if pose=='reach': el=(x+s*49*k,yy+30*k); hand=(x+s*65*k,yy+13*k+math.sin(t*3+s)*5*k)
        elif pose=='knead':el=(x+s*49*k,yy+39*k);hand=(x+s*19*k,yy+58*k+math.sin(t*5+s)*4*k)
        elif pose=='walk':el=(x+s*39*k,yy+38*k);hand=(x+s*(38+math.sin(t*5)*13)*k,yy+62*k)
        else:el=(x+s*39*k,yy+36*k);hand=(x+s*33*k,yy+61*k)
        line(a,[sh,el],shirt,16*k);line(a,[el,hand],skin,12*k);oval(a,hand[0]-6*k,hand[1]-6*k,12*k,12*k,skin)
    rect(a,x-9*k,yy-16*k,18*k,20*k,skin,4*k)
    cy=yy-41*k
    if who=='ana':
        for j in range(13):
            ang=math.pi+j*math.pi/12
            oval(a,x+math.cos(ang)*30*k-12*k,cy+math.sin(ang)*27*k-14*k,24*k,26*k,hair)
        oval(a,x-34*k,cy-28*k,68*k,65*k,hair)
    oval(a,x-26*k,cy-28*k,52*k,60*k,skin)
    if who=='ana':
        for j in range(6):oval(a,x-27*k+j*9*k,cy-29*k,15*k,14*k,hair)
        oval(a,x+22*k,cy+12*k,7*k,10*k,Y)
    elif who=='carlos':
        oval(a,x-28*k,cy-30*k,56*k,18*k,hair)
        a.poly([(x-24*k,cy+9*k),(x-14*k,cy+27*k),(x+12*k,cy+29*k),(x+24*k,cy+9*k),(x+10*k,cy+20*k),(x-11*k,cy+20*k)],hair)
    else:
        a.poly([(x-28*k,cy-8*k),(x-26*k,cy-29*k),(x+7*k,cy-35*k),(x+28*k,cy-19*k),(x+24*k,cy-4*k),(x+9*k,cy-19*k),(x-8*k,cy-11*k)],hair)
        for s in (-1,1):a.box(x+s*12*k-10*k,cy-3*k,20*k,12*k,skin,3*k,INK)
        line(a,[(x-2*k,cy+1*k),(x+2*k,cy+1*k)],INK,2*k)
    for s in (-1,1):oval(a,x+s*10*k-2*k,cy+1*k,4*k,4*k,INK)
    line(a,[(x-5*k,cy+15*k),(x+5*k,cy+15*k)],'#754535',2*k)
def counter(a,y=590):
    rect(a,0,y,540,25,'#ad794e');rect(a,0,y+25,540,145,G)
    for x in range(0,540,72):line(a,[(x,y+29),(x,y+165)],'#315848',2)
def window(a,x,y,w,h,sky='#c6dbcc'):
    rect(a,x-7,y-7,w+14,h+14,WHITE,8);rect(a,x,y,w,h,sky,4)
    line(a,[(x+w/2,y),(x+w/2,y+h)],WHITE,6)
def shop(a,x,y,w,h,label,color=G):
    rect(a,x,y,w,h,N,4);rect(a,x,y,w,42,color,4);text(a,x+w/2,y+21,label,15,WHITE)
    rect(a,x+14,y+60,w*.48,h-72,'#8dada5',3)
    rect(a,x+w*.67,y+60,w*.23,h-60,INK,3)
    for i in range(5):rect(a,x+i*w/5,y+45,w/5,14,T if i%2==0 else C)
def street(a,t):
    rect(a,0,520,540,240,'#d1c7a7');rect(a,0,650,540,110,'#7b8882')
    for x in range(0,540,110):rect(a,x,705,55,4,C)
    for x,h in [(0,180),(108,240),(235,160),(352,205),(450,170)]:
        rect(a,x,520-h,100,h,'#afc5b5',3)
        for yy in range(540-h,480,40):rect(a,x+14,yy,17,23,'#e4e9d7')
def calendar(a,n,y):
    for j in range(7):
        x=25+71*j;rect(a,x,y,64,98,G if j<n else Y,7)
        text(a,x+32,y+24,['S','T','Q','Q','S','S','D'][j],16,WHITE if j<n else INK)
        text(a,x+32,y+64,'T' if j<n else 'F',25,WHITE if j<n else INK)
def token(a,x,y,c=Y):oval(a,x-25,y-12,50,25,'#a67a43');oval(a,x-25,y-16,50,25,c);text(a,x,y-4,'R$',12,INK)
def clock(a,x,y,t,r=62):
    oval(a,x-r,y-r,2*r,2*r,INK);oval(a,x-r+6,y-r+6,2*r-12,2*r-12,C)
    for j in range(12):
        z=j*math.pi/6;oval(a,x+(r-15)*math.sin(z)-2,y+(r-15)*math.cos(z)-2,4,4,INK)
    for length,z in [(r*.48,t*.15),(r*.72,t*.8)]:line(a,[(x,y),(x+length*math.sin(z),y-length*math.cos(z))],INK,4)
NAMES=['esteira','balanca','pagamento','despertador','onibus','massa','lavanderia','calendario','abertura','escala','contas','equipamento','troca_turnos','custos','etiqueta','carteira','descanso','producao','comercio','comparacao','folga','gestao','casa','convergencia']
def scene(i,t):
    a=canvas([C,N,'#e5d8c0','#e5d6c0','#c6d8c7',N,'#dbe3d0',C,'#cadac5',C,'#dfcfb6','#c7d7ce','#e8d7b8',C,'#d7e1cc',N,'#cedec9','#d3ddd1','#c2d9c3','#e2e7d4','#c6dfca','#e6d4b9',C,'#d5e1d0'][i])
    q=min(1,t/2);w=math.sin(t*3)
    if i==0: # macro conveyor
        rect(a,0,250,540,70,'#b3b9a7');rect(a,0,510,540,132,INK,5)
        for j in range(9):
            x=(j*70+t*42)%630-45;wheel(a,x,584,23);bread(a,x,490,1.05)
        rect(a,20,640,22,100,B);rect(a,478,640,22,100,B)
    elif i==1:
        rect(a,0,596,540,180,'#c28c60');rect(a,110,480,320,116,G,20);rect(a,145,445,250,40,'#97b4aa',8)
        bread(a,215,420,1.6);bread(a,320,416,1.5)
        rect(a,180,512,180,55,INK,6);text(a,270,540,'0,250 kg',28,'#b2dfbe')
        line(a,[(525,365),(405,409),(365,425+5*w)],'#be8b62',25)
    elif i==2:
        counter(a,650);rect(a,140,330,250,260,INK,18);rect(a,165,355,200,95,'#a7cfb9',8);text(a,265,405,'APROXIME',22)
        for j in range(12):rect(a,180+(j%3)*58,470+(j//3)*22,38,15,S,3)
        x=440-125*q;line(a,[(540,530),(x+70,485),(x+25,470)],'#be8b62',42);rect(a,x-68,432,120,70,B,8);rect(a,x-55,445,25,20,Y,3)
        if q>.8:text(a,265,405,'✓',35)
    elif i==3:
        window(a,24,180,200,270,'#708a96');oval(a,52,211,45,45,C)
        rect(a,0,570,540,185,'#bda789');rect(a,28,485,260,116,G,18);rect(a,40,476,103,45,C,10)
        person(a,160,550,1.15,'ana',t,'sit');rect(a,337,460,150,20,'#966e4c');clock(a,410,400,t,54)
        if int(t*3)%2==0:line(a,[(349,344),(333,325)],T,4);line(a,[(469,344),(484,325)],T,4)
    elif i==4:
        rect(a,0,190,540,490,B);rect(a,25,220,490,300,'#a8c5bf',12)
        for j in range(6):
            x=(j*100-t*65)%660-80;rect(a,x,345,75,172,'#74958e',3);rect(a,x+12,370,24,30,C)
        for x in (25,250,515):rect(a,x,220,12,315,INK)
        rect(a,0,520,540,250,'#9fae9e');rect(a,22,490,170,180,'#527669',12);person(a,125,712,1.55,'ana',t,'sit')
        line(a,[(380,210),(380,430)],Y,6)
    elif i==5:
        rect(a,0,190,540,530,'#ddd4bd')
        for x in range(0,540,90):line(a,[(x,190),(x,570)],'#bfbca8',1)
        person(a,270,650,2.25,'ana',t,'knead',True);counter(a,535)
        oval(a,130,518,270,56,'#d7b28a');oval(a,190,515,160+6*w,42-3*w,'#f4dfb3')
        rect(a,32,455,65,80,C,8);text(a,64,493,'FARINHA',10)
    elif i==6:
        rect(a,0,590,540,180,'#b8c8b5');rect(a,230,280,245,340,'#f3efdf',15);rect(a,250,298,200,55,S,5)
        oval(a,270,390,170,170,INK);oval(a,282,402,146,146,'#91b9b6')
        for j,c in enumerate([C,T,B]):z=t*2+j*2.1;oval(a,340+42*math.sin(z),464+42*math.cos(z),33,26,c)
        person(a,112,688,1.65,'ana',t,'reach');rect(a,30,600,120,60,'#b48e67',10)
    elif i==7:
        text(a,270,245,'DIAS DE TRABALHO E FOLGA',21);calendar(a,6,315);calendar(a,5,515)
        text(a,270,446,'6 × 1',32);text(a,270,650,'5 × 2',32);oval(a,465-71*q,522,60,84,'#f2cf83') if False else None
        line(a,[(270,468),(270,500)],T,5)
    elif i==8:
        street(a,t);shop(a,42,300,456,350,'PADARIA DO BAIRRO')
        rect(a,340,385,108,210,INK,3);rect(a,341,386,105*(1-q),209,'#9eb2a3')
        person(a,285,704,1.55,'carlos',t,'reach',True)
    elif i==9:
        rect(a,30,220,480,385,WHITE,15);text(a,270,256,'ESCALA DA EQUIPE',27)
        for row in range(3):
            text(a,68,325+row*90,['A','B','C'][row],20)
            for j in range(7):
                c=G if (j+row)%7<5 else Y
                rect(a,100+j*54,307+row*90,45,48,c,5)
        x=100+54*(int(t*1.8)%7);line(a,[(x,390),(x+44,390)],T,5)
        person(a,430,742,1.25,'carlos',t,'reach',True)
    elif i==10:
        rect(a,0,220,540,520,'#b58a62')
        for j,txt in enumerate(['FARINHA','ENERGIA','EQUIPE']):
            x=45+j*150;rect(a,x,300,130,210,C,5);text(a,x+65,335,txt,16)
            for k in range(5):line(a,[(x+15,366+k*23),(x+112,366+k*23)],S,2)
        rect(a,200,540,160,110,INK,9)
        for j in range(12):rect(a,216+j%4*33,554+j//4*29,24,20,Y if j==int(t*3)%12 else S,3)
        line(a,[(530,670),(362,617),(340,586+5*w)],'#ca9b75',33)
    elif i==11:
        rect(a,30,270,480,330,'#a7bdb5',16);rect(a,48,288,444,135,B,9);text(a,270,349,'FORNO',30,WHITE)
        rect(a,80,445,380,110,INK,6);rect(a,95,460,350,80,'#c28a51',4)
        for j in range(4):bread(a,130+j*88,500,.85)
        for j in range(3):line(a,[(160+j*100,445),(151+j*100+4*w,431),(160+j*100,417)],Y,3)
        oval(a,438,310,22,22,Y)
    elif i==12:
        rect(a,0,560,540,180,'#b6c9b6');rect(a,200,260,140,300,INK,5);rect(a,212,270,116,286,'#9db8af',4)
        person(a,110+65*q,710,1.6,'ana',t,'walk',True);person(a,430-60*q,710,1.6,'carlos',t,'walk',True)
        clock(a,270,180,t,48)
    elif i==13:
        for j,(lab,c) in enumerate([('INSUMOS',Y),('SALÁRIOS',G),('ENERGIA',T)]):
            x=95+j*175;text(a,x,620,lab,16);height=110+j*30
            rect(a,x-45,580-height,90,height,c,6)
            for n in range(3):token(a,x,580-height-18*n)
        line(a,[(50,640),(490,640)],INK,3)
    elif i==14:
        bread(a,270,300,2.6);a.poly([(75,435),(385,435),(468,520),(385,605),(75,605)],WHITE);oval(a,408,507,25,25,S)
        text(a,240,479,'PREÇO DO PÃO',22);text(a,240,548,'CUSTO + MARGEM',23)
        for j in range(5):token(a,135+65*j,662-4*math.sin(t+j))
    elif i==15:
        rect(a,0,240,540,500,'#c9b08a');rect(a,68,340,400,270,'#714d3d',18)
        for j in range(3):rect(a,105+j*28,370-j*16,220,110,'#92b3a1',5);text(a,175+j*28,410-j*16,'R$',25)
        rect(a,68,465,400,145,'#815a43',12);rect(a,375,510,110,55,'#543c33',6);oval(a,415,528,19,19,Y)
        line(a,[(530,640),(475,586),(444,561+5*w)],'#be8b62',34)
    elif i==16:
        window(a,300,205,190,300);rect(a,0,590,540,170,'#b9c7a9')
        rect(a,40,450,270,170,G,30);rect(a,35,520,310,110,G,20)
        person(a,175,653,1.55,'ana',t,'sit');rect(a,380,560,110,14,'#96724e');rect(a,400,505,44,53,C,6)
        for j in range(2):line(a,[(412+j*15,499),(406+j*15+w*3,481),(414+j*15,465)],'#9ea99a',3)
    elif i==17:
        rect(a,0,250,540,490,'#bccbc0');rect(a,26,475,488,120,B,12)
        for j in range(6):
            x=(j*100+35*t)%600-30;bread(a,x,455,1.05);wheel(a,x,540,18)
        person(a,115,470,1.25,'ana',t,'reach',True);person(a,422,470,1.25,'carlos',t,'reach',True)
        rect(a,365,620,130,80,G,9);text(a,430,660,'✓',43,WHITE)
    elif i==18:
        street(a,t);shop(a,20,360,150,190,'CAFÉ',T);shop(a,185,330,170,220,'LOJA',G);shop(a,370,370,150,180,'FEIRA',B)
        person(a,85+45*q,710,1.25,'buyer',t,'walk');person(a,400-40*q,710,1.25,'ana',t+.5,'walk');bag(a,150+45*q,635,.48)
    elif i==19:
        rect(a,0,570,540,170,'#b3c6b1');shop(a,22,365,200,205,'PADARIA');shop(a,280,280,238,290,'SUPERMERCADO',B)
        for j in range(3):rect(a,300+j*65,320,48,40,'#a5c1bb',4)
        text(a,122,640,'PEQUENA',18);text(a,400,640,'GRANDE',18)
        person(a,120,578,1.1,'carlos',t,'stand',True)
    elif i==20:
        rect(a,0,580,540,190,'#a9c8a0')
        for x in (45,450):
            rect(a,x,300,24,290,'#876950',8);oval(a,x-74,210,170,190,G);oval(a,x-37,185,135,145,S)
        rect(a,140,530,240,24,'#95704b',6);rect(a,160,552,12,75,INK);rect(a,350,552,12,75,INK)
        person(a,265,680,1.75,'ana',t,'sit')
        for j in range(3):x=170+j*90+t*15;line(a,[(x%540,240),(x%540+8,235),(x%540+16,240)],INK,2)
    elif i==21:
        rect(a,0,210,540,470,'#d2c4a4')
        for j in range(4):rect(a,20,285+j*70,500,10,'#a17b53');bread(a,95+j*100,260+j*70,.8)
        person(a,280,730,2.0,'carlos',t,'reach',True);counter(a,600)
        rect(a,365,510,110,90,B,8);rect(a,380,523,80,35,S,4)
    elif i==22:
        window(a,42,205,160,240);rect(a,0,590,540,180,'#c5b59a');person(a,190,700,1.8,'buyer',t,'walk')
        rect(a,285,480,230,20,'#987147');rect(a,300,500,14,195,'#987147');rect(a,482,500,14,195,'#987147')
        bag(a,395,424+4*math.sin(t),1.15);bread(a,440,470,1)
    elif i==23:
        for j,(who,lab,c) in enumerate([('ana','TEMPO',T),('carlos','NEGÓCIO',B),('buyer','PREÇO',G)]):
            x=20+j*174;rect(a,x,245,154,390,c,12);person(a,x+77,590,1.15,who,t,'stand',who=='carlos')
            text(a,x+77,665,lab,18)
        line(a,[(97,710),(270,740),(445,710)],INK,3);oval(a,250,720,40,40,Y)
    else:raise ValueError('unknown scene')
    return a.im.resize((W,H),Image.Resampling.LANCZOS)
