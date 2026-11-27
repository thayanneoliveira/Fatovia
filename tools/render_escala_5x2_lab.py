"""Isolated V5-derived bakery Reel; no publication, no voice substitution."""
import sys, math, json, re, bisect, subprocess, hashlib, difflib, unicodedata, wave
from pathlib import Path
from PIL import Image
import numpy as np
from faster_whisper import WhisperModel
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'fatovia'/'v5_legacy'))
import visual_base as v
from kinetic_captions import KineticCaptions
W,H,FPS=1080,1920,24
# Supersampled vector geometry; camera remains fixed inside each shot.
v.W,v.H,v.S=1620,2880,3
D,G,C,Y,T,R,L=v.D,v.G,v.C,v.Y,v.T,v.R,v.L
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',s.casefold()) if c.isalnum() and not unicodedata.combining(c))
def bread(a,x,y,s=1):
    a.e(x-35*s,y-16*s,70*s,32*s,'#b97937')
    a.e(x-33*s,y-20*s,66*s,29*s,'#dfaa5d')
    for dx in (-16,0,16):a.line([(x+(dx-4)*s,y-12*s),(x+(dx+5)*s,y-3*s)],C,2*s)
def bakery(a):
    a.box(0,610,540,350,'#d8c49f')
    a.box(28,202,484,345,'#e9d9b7',12)
    for yy in (292,387,482):
        a.box(45,yy,450,11,'#816649',3)
        for j in range(5):bread(a,85+j*90,yy-18,.85)
    a.box(0,660,540,108,G,5);a.box(0,648,540,20,'#a5875e',3)
def room(a):
    a.box(0,620,540,340,'#cdb18e')
    a.box(45,245,200,250,'#a9c5bc',8)
    a.line([(145,245),(145,495)],C,6);a.line([(45,370),(245,370)],C,6)
def clock(a,x,y,t):
    a.e(x-64,y-64,128,128,G);a.e(x-56,y-56,112,112,C)
    for k in range(12):
        z=k*math.pi/6;a.e(x+48*math.sin(z)-2,y-48*math.cos(z)-2,4,4,D)
    for length,z in [(32,t*.18),(46,t*1.15)]:
        a.line([(x,y),(x+length*math.sin(z),y-length*math.cos(z))],D,4)
def cal(a,days,other=False):
    for i in range(7):
        x=22+72*i; a.box(x,365,65,100,G if i<days else Y,7)
        a.text(x+32,388,['S','T','Q','Q','S','S','D'][i],17,C if i<days else D)
        a.text(x+32,430,'T' if i<days else 'F',28,C if i<days else D)
def scene(i,t):
    q=v.ease(min(1,t/4))
    a=v.A(v.bg('room' if i in (2,3,4,18) else 'paper').copy())
    if i in (0,1,5,6,7,8,10,11,12,13,14,19,20,21,22):
        bakery(a)
        if i in (0,1,10,11,12,13,20):
            for j in range(3):bread(a,90+j*150+20*math.sin(t*.6+j),620,1.3)
            v.person(a,125,650,1.8,'mom',t,'point')
            v.person(a,414,820,1.65,'official',t,'stand')
            if i in (11,12,13,20):
                v.coin(a,340,598,1.6);v.coin(a,380,598,1.6)
        elif i in (5,6,7,8,19):
            v.person(a,375,650,1.8,'official',t,'point')
            if i in (7,8):
                v.doc(a,44,280,230,255,'TURNOS',[('Equipe','Organizar'),('Horários','Cobrir')],t)
        else:
            v.person(a,120,650,1.8,'mom',t,'point');v.person(a,395,650,1.8,'official',t,'stand')
            if i==14:
                for j in range(4):bread(a,65+j*135+(t*12)%20,615,1.05)
    elif i in (2,3,4,18):
        room(a)
        if i==2:
            clock(a,375,330,t);v.person(a,148+15*q,760,2,'mom',t,'walk')
        elif i==3:
            a.box(285,490,190,205,'#d3d9cd',9);a.e(315,535,130,130,D);a.e(325,545,110,110,'#73928c')
            for k in range(3):
                z=t*2+k*2.09;a.e(369+36*math.sin(z)-10,599+36*math.cos(z)-8,20,16,C)
            v.person(a,128,758,1.9,'mom',t,'point');clock(a,385,330,t)
        elif i==4:
            cal(a,6 if t<2 else 5);v.person(a,270,740,1.8,'mom',t,'stand')
            a.text(270,530,'6 × 1' if t<2 else '5 × 2',35,D)
        else:
            a.box(200,574,245,16,'#826445',3);a.box(221,590,10,135,'#826445');a.box(425,590,10,135,'#826445')
            a.box(290,540,44,35,C,6);v.person(a,130,745,1.9,'mom',t,'stand')
    elif i in (9,16):
        v.doc(a,80,260,380,370,'GESTÃO',[('Equipe','Turnos'),('Equipamentos','Investimento'),('Despesas','Custos')],t)
        v.person(a,110,745,1.5,'official',t,'point')
    elif i==15:
        v.skyline(a);v.tree(a,65,700);v.tree(a,475,700)
        for j in range(3):v.person(a,110+j*145+10*q,735,1.35,'mom' if j==0 else 'official',t+j,'walk')
    elif i==17:
        v.skyline(a)
        v.building(a,35,690,180,125,'house',1)
        a.box(30,535,190,35,G,6);a.text(125,552,'PADARIA',19,C)
        a.box(280,420,230,270,'#d9ceb0',6);a.box(280,420,230,45,G,5);a.text(395,443,'SUPERMERCADO',18,C)
        for j in range(3):a.box(300+j*65,515,45,130,'#84a39a',3)
        v.person(a,240,748,1.2,'official',t,'stand')
    return a.im.resize((W,H),Image.Resampling.LANCZOS)
def main():
    audio=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
    lines=(ROOT/'data'/'reel_lab_escala_5x2.txt').read_text().strip().splitlines()
    with wave.open(str(audio)) as w:duration=w.getnframes()/w.getframerate()
    if not 20<=duration<=118.4:raise ValueError('Narração fora do limite; não acelerar, truncar ou substituir.')
    model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
    pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(audio),'-ac','1','-ar','16000','-f','f32le','-'])
    waveform=np.frombuffer(pcm,dtype='<f4').copy()
    segments,_=model.transcribe(waveform,language='pt',word_timestamps=True,beam_size=5)
    words=[dict(text=w.word.strip(),start=float(w.start),end=float(w.end),probability=float(w.probability)) for seg in segments for w in seg.words if norm(w.word) and w.end>w.start]
    ref=[];owners=[]
    for i,line in enumerate(lines):
        for s in line.split():
            if norm(s):ref.append(norm(s));owners.append(i)
    observed=[norm(w['text']) for w in words]
    match=difflib.SequenceMatcher(a=ref,b=observed,autojunk=False)
    ratio=match.ratio()
    if ratio<.94:raise ValueError(f'ASR sem correspondência suficiente: {ratio:.3f}')
    mapped={}
    for a,b,n in match.get_matching_blocks():
        for j in range(n):mapped[b+j]=owners[a+j]
    starts=[]
    for i in range(len(lines)):
        hits=[words[j]['start'] for j,k in mapped.items() if k==i]
        if not hits:raise ValueError('Cena sem correspondência ASR')
        starts.append(min(hits))
    starts[0]=0.
    groups=[];run=[]
    for w in words:
        if run and (len(run)>=3 or len(' '.join(x['text'] for x in run+[w]))>24):
            groups.append(([x['text'] for x in run],run));run=[]
        run.append(w)
        if w['text'].endswith(('.',',','?','!',':',';')):
            groups.append(([x['text'] for x in run],run));run=[]
    if run:groups.append(([x['text'] for x in run],run))
    cap=KineticCaptions(groups,W,H)
    logo_path=ROOT/'assets'/'fatovia-approved.png'
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if digest(logo_path)!='df41d13bb11db469d2850c69c0ece41eeb7e33a262e7622b59afb21ef81c7ce6':raise ValueError('Logo divergente')
    logo=Image.open(logo_path).convert('RGBA');logo.thumbnail((460,460),Image.Resampling.LANCZOS)
    closing=Image.new('RGB',(W,H),D);closing.paste(logo,((W-logo.width)//2,(H-logo.height)//2),logo)
    target=out/'FatoVia_Escala_5x2_Algenib_V5_Teste.mp4'
    frames=math.ceil((duration+1.5)*FPS)
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(audio),'-map','0:v','-map','1:a','-af','loudnorm=I=-16:TP=-1.5:LRA=11,apad','-t',str(frames/FPS),'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-threads','4','-c:a','aac','-ar','48000','-ac','2','-b:a','160k','-movflags','+faststart',str(target)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    thumb=[];old=-1
    for f in range(frames):
        t=f/FPS;i=min(len(lines)-1,max(0,bisect.bisect_right(starts,t)-1))
        if t>=duration:im=closing
        else:
            im=scene(i,t-starts[i]);cap.draw(im,t)
            if i!=old:
                thumb.append(im.resize((180,320),Image.Resampling.LANCZOS));old=i
                print('scene',i+1,flush=True)
                if i==0:im.save(out/'cover.png')
        proc.stdin.write(im.tobytes())
    proc.stdin.close()
    if proc.wait():raise RuntimeError('encoder failed')
    subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    sheet=Image.new('RGB',(180*6,320*math.ceil(len(thumb)/6)),D)
    for i,im in enumerate(thumb):sheet.paste(im,(180*(i%6),320*(i//6)))
    sheet.save(out/'storyboard.jpg',quality=93)
    (out/'report.json').write_text(json.dumps({'status':'lab_only_review_required','publish_allowed':False,'voice':'Algenib','asr_match_ratio':ratio,'asr_words':words,'scenes':len(thumb),'duration':frames/FPS,'resolution':[W,H],'fps':FPS,'audio_sha256':digest(audio),'video_sha256':digest(target),'visual':'V5 recovered vector illustration; new bakery shots; not photorealistic','review_pending':['visual equivalence to Maria','listen to narration','word alignment spot check','independent factual review']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
