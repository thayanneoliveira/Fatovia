"""FatoVia V4: free, locally rendered 2D cinematic pilot. Manual direction."""
from pathlib import Path
import math,json,subprocess,time,hashlib
from PIL import Image,ImageDraw
import visual_base as v
from kinetic_captions import KineticCaptions
ROOT=Path(__file__).parent
W,H,FPS,DUR=1080,1920,24,15
v.W,v.H,v.S=W,H,2
A=v.A;D,G,C,Y,T,R=v.D,v.G,v.C,v.Y,v.T,v.R
CAP=KineticCaptions(json.loads((ROOT/'caption_groups.json').read_text()),W,H)
AUDIO=ROOT/'narracao_piloto.wav' if (ROOT/'narracao_piloto.wav').exists() else ROOT.parent/'fatovia_santa_r/R_episodio.wav'
def ramp(t,a,b):return v.ease((t-a)/(b-a))
def mix(a,b,u):return a+(b-a)*u
def shadow(a,x,y,w,h):a.e(x-w/2,y-h/2,w,h,'#a1ab90')
def city(t,shift=0):
 a=A(v.bg('city').copy());a.e(426,105,66,66,'#ecd1a1')
 for i in range(3):
  x=(-120+i*220+t*3-shift*.15)%680-80;y=110+50*(i%2)
  for dx,dy,w,h in [(0,12,76,26),(18,0,45,38),(48,10,42,24)]:a.e(x+dx,y+dy,w,h,'#f3eee0')
 for j,(x,top,w) in enumerate([(-30,315,100),(75,370,73),(158,285,94),(260,330,72),(340,302,92),(442,270,105)]):
  x-=shift*.32;a.box(x,top,w,505-top,'#b4c7b6',3)
  for xx in range(int(x)+12,int(x+w)-6,24):
   for yy in range(top+20,495,36):a.box(xx,yy,10,15,'#dbe4d2',1)
 a.box(0,505,540,455,'#c0c6a6');a.box(0,665,540,295,'#d8ceb0');a.box(0,725,540,235,'#8fa492');a.box(0,720,540,7,'#eee5ce')
 for x in range(-80,600,100):a.box(x-shift*.7,765,42,4,C,1)
 for x,s in [(26,.80),(506,.90)]:v.tree(a,x-shift*.75,603,s)
 return a

def house(a,x,y,w,h,p=.42):
 shadow(a,x+w*.53,y+5,w+35,30)
 a.poly([(x+w,y-h),(x+w+23,y-h-15),(x+w+23,y-17),(x+w,y)],'#a18364')
 v.building(a,x,y,w,h,'house',p)
 if p<.9:
  a.box(x+w*.37,y-h*.51,w*.24,h*.51,'#243e35');a.box(x+w*.37+5,y-h*.51+5,10,h*.51-5,'#4c6253')
  a.line([(x,y),(x+w,y)],'#a48766',4)

def person(a,x,y,s,t,who='mom',mood='neutral',walk=0,gesture=0,direction=1):
 skin='#c78f6a' if who=='mom' else '#ad7955';hair='#42392f';shirt='#cfa15b' if who=='mom' else '#d7b66c';pants='#315344';b=math.sin(t*7)*walk;bob=abs(b)*3*s
 def xy(px,py):return (x+px*s*direction,y+(py-bob/s)*s)
 def line(points,col,width):a.line([xy(*p) for p in points],col,width*s)
 def oval(px,py,ww,hh,col):
  xx,yy=xy(px,py);a.e(xx-ww*s/2,yy-hh*s/2,ww*s,hh*s,col)
 shadow(a,x,y,54*s,12*s)
 for side in [-1,1]:
  hip=(side*11,-57);k=(side*12+side*b*11,-29-abs(b)*3);foot=(side*13-side*b*15,-4-max(0,side*b)*7)
  line([hip,k,foot],pants,11);line([foot,(foot[0]+7,foot[1])],D,7)
 top=y-(119*s+bob);a.box(x-23*s,top,46*s,70*s,shirt,12*s);a.box(x-22*s,top+43*s,44*s,8*s,'#b98d49',3*s)
 if who=='worker':
  for dx in [-19,13]:a.box(x+dx*s,top+10*s,6*s,44*s,C,2*s)
 for side in [-1,1]:
  g=gesture if side==1 else 0;shoulder=(side*20,-108);elbow=(side*(29+8*g),-86-12*g);hand=(side*(30+27*g),-67-35*g+side*b*7)
  line([shoulder,elbow],shirt,11);line([elbow,hand],skin,7);oval(*hand,9,10,skin)
 if who=='mom':oval(0,-153,54,52,hair);oval(-22,-137,14,52,hair);oval(22,-137,14,52,hair)
 oval(0,-125,15,23,skin)
 oval(0,-145,43,47,skin);oval(-2,-162,44,20,hair)
 if who=='worker':oval(0,-168,51,19,Y);line([(-27,-162),(27,-162)],'#b28a44',5)
 blink=(t%3.9)>3.77
 for side in [-1,1]:
  oval(side*8,-146,3.8,1 if blink else 4.7,D);yb=-155+(2 if mood=='sad' else -1 if mood=='curious' else 0)
  line([(side*12,yb+(-2 if mood=='sad' else 0)),(side*5,yb+(2 if mood=='sad' else 0))],hair,1.7)
 if mood=='sad':line([(-5,-133),(0,-136),(5,-133)],hair,1.8)
 elif mood=='curious':oval(0,-133,6,7,'#7a4e38')
 else:line([(-5,-136),(0,-132),(5,-136)],hair,1.8)

def coin(a,x,y,s=1):
 a.e(x-20*s,y-7*s,40*s,16*s,'#ad7e3e');a.e(x-20*s,y-12*s,40*s,16*s,Y);a.e(x-15*s,y-10*s,30*s,11*s,'#f0d18b');a.text(x,y-4*s,'R$',round(10*s),D)

def blueprint(a,x,y,w,h,q):
 a.box(x+6,y+8,w,h,'#b7ac91',12);a.box(x,y,w,h,'#f9f3e4',12)
 for i in range(1,8):a.line([(x+12,y+i*h/8),(x+w-12,y+i*h/8)],'#dce1ce',1)
 for i in range(1,9):a.line([(x+i*w/9,y+10),(x+i*w/9,y+h-10)],'#dce1ce',1)
 pts=[(x+w*.19,y+h*.76),(x+w*.19,y+h*.40),(x+w*.5,y+h*.2),(x+w*.81,y+h*.40),(x+w*.81,y+h*.76),(x+w*.19,y+h*.76)]
 for i,(p,n) in enumerate(zip(pts,pts[1:])):
  u=ramp(q,i/5,(i+1)/5);a.line([p,(mix(p[0],n[0],u),mix(p[1],n[1],u))],G,3)
 a.line([(x+w*.45,y+h*.76),(x+w*.45,y+h*.55),(x+w*.56,y+h*.55),(x+w*.56,y+h*.76)],G,2)

def opening(t):
 a=city(t,25*ramp(t,0,2.8));house(a,135,638,332,305);v.fence(a,130,665,335)
 person(a,101+16*ramp(t,0,1.4),700,2.05,t,mood='curious' if t<1.65 else 'sad',gesture=.82*(1-ramp(t,1.5,2.5)))
 for k in range(3):
  st=.34+k*.14
  if t>=st:
   p=ramp(t,st,st+.83);coin(a,mix(105,285+k*25,p),mix(487,650,p)-65*math.sin(math.pi*p),1.12)
 if t>=1.66:
  p=ramp(t,1.66,2.08);a.e(353-37*p,220-37*p,74*p,74*p,R);a.text(353,220,'?',max(8,round(46*p)),C)
 return a

def savings(t):
 a=A(v.bg('room').copy());a.box(0,615,540,345,'#d1b38c');a.box(0,615,540,7,'#b99c78');a.box(22,170,182,257,'#e6d1b1',8);a.box(32,180,162,237,'#b8d0c0',5);a.line([(112,180),(112,417)],C,5);a.line([(32,294),(194,294)],C,5)
 a.poly([(194,180),(194,417),(465,615),(335,615)],'#e9d9b6');a.box(30,622,480,30,'#84674b',7);a.box(55,649,17,109,'#9d7b57',3);a.box(468,649,17,109,'#9d7b57',3)
 person(a,120,677,2.05,t,gesture=.72)
 x=310;y=412;a.e(x-85,601,170,26,'#bba98c');a.box(x-65,y,130,204,'#8fae98',27,outline=G);a.box(x-55,y+10,110,184,'#dce7d3',23);a.box(x-69,y-10,138,22,G,5);a.box(x-47,y+32,5,119,'#f6f4de',3)
 for k in range(9):
  st=3.92+k*.16
  if t>=st:
   q=ramp(t,st,st+.54);coin(a,mix(444,x-34+(k%3)*32,q),mix(294,592-(k//3)*15,q)-45*math.sin(math.pi*q),.88)
 q=ramp(t,5.42,6.15)
 if q>0:blueprint(a,257,151+36*(1-q),229,176,q)
 return a

def contract(t):
 a=city(t,12);house(a,198,586,300,248);person(a,100,699,1.74,t,gesture=.9);person(a,426,699,1.74,t+.2,'worker',gesture=.75,direction=-1)
 p=ramp(t,7.0,7.48);x=152;y=180+70*(1-p);v.doc(a,x,y,236,255,'CONTRATO',[('',''),('',''),('','')],t)
 q=ramp(t,7.55,8.16)
 if q>0:
  pts=[(x+44,y+201),(x+68,y+184),(x+82,y+207),(x+113,y+188),(x+155,y+200)]
  for i,(f,g) in enumerate(zip(pts,pts[1:])):
   u=ramp(q,i/4,(i+1)/4);a.line([f,(mix(f[0],g[0],u),mix(f[1],g[1],u))],G,3)
 return a

def construction(t,abandoned=False):
 a=city(t,15*ramp(t,8.47,11.12));house(a,140,638,330,305);v.crane(a,65,655,t*3 if not abandoned else 0)
 for j in range(12):
  st=8.48+j*.095
  if t>=st:
   p=ramp(t,st,st+.39);xx=337+(j%4)*33+85*(1-p);yy=689-(j//4)*17-180*(1-p);a.box(xx,yy,30,15,'#aa7254',2);a.line([(xx+2,yy+2),(xx+28,yy+2)],'#c28f6c',2)
 if not abandoned:
  person(a,116+25*ramp(t,8.47,10.6),710,1.7,t,'worker',walk=.75,gesture=.2);person(a,419-45*ramp(t,9.6,10.8),710,1.65,t+.7,'worker',walk=.7,gesture=.45,direction=-1)
 else:
  v.fence(a,139,660,333);p=ramp(t,11.12,11.58);cx=270;cy=213
  a.e(cx-76*p,cy-76*p,152*p,152*p,G);a.e(cx-68*p,cy-68*p,136*p,136*p,C)
  for j in range(12):
   ang=j*math.tau/12;a.line([(cx+math.sin(ang)*58*p,cy-math.cos(ang)*58*p),(cx+math.sin(ang)*64*p,cy-math.cos(ang)*64*p)],T,2)
  ang=(t-11.12)*4.6;a.line([(cx,cy),(cx+45*p*math.sin(ang),cy-45*p*math.cos(ang))],D,4);a.line([(cx,cy),(cx+30*p*math.sin(ang/4),cy-30*p*math.cos(ang/4))],D,6)
  if t<14.5:
   person(a,130-270*ramp(t,13.05,14.42),710,1.65,t,'worker',walk=.9,direction=-1);person(a,416+240*ramp(t,13.2,14.5),710,1.65,t+.6,'worker',walk=.9)
  person(a,103,732,1.88,t,mood='sad',gesture=.13)
 return a

def camera(im,z,focus):
 w,h=round(W/z),round(H/z);x=max(0,min(W-w,round(focus[0]*2-w/2)));y=max(0,min(H-h,round(focus[1]*2-h/2)))
 return im.crop((x,y,x+w,y+h)).resize((W,H),Image.Resampling.BICUBIC)

def shot(t):
 if t<3.05:a=opening(t);p=ramp(t,0,2.8);z=mix(1.03,1.21,p);f=(mix(270,231,p),mix(480,510,p))
 elif t<6.95:a=savings(t);p=ramp(t,3.05,6.65);z=mix(1.03,1.18,p);f=(mix(270,310,p),mix(480,508,p))
 elif t<8.47:a=contract(t);p=ramp(t,6.95,8.4);z=mix(1.02,1.16,p);f=(270,510)
 elif t<11.12:a=construction(t);p=ramp(t,8.47,11.12);z=mix(1.12,1.02,p);f=(mix(315,270,p),505)
 else:a=construction(t,True);p=ramp(t,11.12,15);z=mix(1.02,1.17,p);f=(mix(270,235,p),520)
 return camera(a.im,z,f)

def frame(t):
 im=shot(t)
 for edge in (3.05,6.95):
  if edge<=t<edge+.20:im=Image.blend(shot(edge-1/FPS),im,ramp(t,edge,edge+.20))
 d=ImageDraw.Draw(im);d.text((54,124),'FATOVIA',font=v.ft(16),fill=D,stroke_width=1,stroke_fill=C);CAP.draw(im,t)
 d.text((W//2,round(H*.852)),'EXEMPLO FICTÍCIO',font=v.ft(11),fill=C,stroke_width=2,stroke_fill=D,anchor='mm')
 return im

def main():
 out=ROOT/'piloto_V4.mp4';start=time.monotonic();p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(AUDIO),'-t',str(DUR),'-c:v','libx264','-preset','veryfast','-threads','4','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
 for i in range(FPS*int(DUR)):
  p.stdin.write(frame(i/FPS).tobytes())
  if i%72==0:print(i,flush=True)
 p.stdin.close();assert p.wait()==0
 subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
 sheet=Image.new('RGB',(216*4,384*2),D)
 for i,t in enumerate([.8,2.5,4.6,6.4,7.9,10.1,12.4,14.4]):sheet.paste(frame(t).resize((216,384),Image.Resampling.LANCZOS),(i%4*216,i//4*384))
 sheet.save(ROOT/'storyboard_v4.jpg',quality=94);frame(2.5).save(ROOT/'capa_v4.png')
 report={'duration':DUR,'width':W,'height':H,'fps':FPS,'generated_frames':FPS*DUR,'seconds':round(time.monotonic()-start,2),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source_audio_sha256':hashlib.sha256(AUDIO.read_bytes()).hexdigest(),'scope':'manual direction; no paid API; no production integration','caption_timing':'unchanged V3 estimated ASR timings','publish_allowed':False};(ROOT/'report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
if __name__=='__main__':main()