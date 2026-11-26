"""FatoVia V5-derived audiovisual lab: deterministic semantic scenes; NEVER publishes.
Reuses owner's original visual_base.py, articulated person/scene grammar and kinetic captions.
The factory is a reproducible lab, not a certified autonomous artist or fact checker.
"""
from __future__ import annotations
import argparse, math, json, hashlib, bisect, re, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE/'v5_legacy'
sys.path.insert(0,str(ORIGINAL))
import visual_base as v
import pilot_v4 as b
from kinetic_captions import KineticCaptions

W,H,FPS=1080,1920,24
S=2
v.W,v.H,v.S=1080,1920,2
D,G,C,Y,T,R=v.D,v.G,v.C,v.Y,v.T,v.R
ROLE_SCENES={
 'hook':'announcement', 'person':'character', 'announcement':'announcement',
 'human_consequence':'hope', 'time':'waiting', 'investigation':'investigate',
 'action':'investigate', 'official_source':'portal', 'caveat':'caveat',
 'verification':'checklist', 'discovery':'contrast', 'reflection':'reflect', 'brand':'brand'
}
ALLOWED_SOURCE_DOMAINS={'www.gov.br','gov.br','obrasgov.sistema.gov.br','portaldatransparencia.gov.br'}
LOGO=HERE.parent/'assets'/'fatovia-approved.png'
LOGO_SHA='df41d13bb11db469d2850c69c0ece41eeb7e33a262e7622b59afb21ef81c7ce6'

def hfile(path:Path)->str:
 with path.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()

def ease(x):return v.ease(min(1,max(0,x)))
def lerp(a,b,q):return a+(b-a)*q

def validate_fixture(beatfile,voicefile):
 from urllib.parse import urlsplit
 fx=json.loads(Path(beatfile).read_text())
 rows=json.loads(Path(voicefile).read_text())
 if fx['status']!='lab_only_no_publish' or fx['voice']!='Santa-R-1.0':raise ValueError('not lab-only Santa R')
 if len(fx['beats'])!=len(rows) or not 7<=len(rows)<=100:raise ValueError('caption/scene coverage')
 for i,(beat,row) in enumerate(zip(fx['beats'],rows)):
  if beat['phrase_index']!=i or beat['role'] not in ROLE_SCENES:raise ValueError('invalid scene semantics')
  if not row.get('caption') or len(row['caption'])>290:raise ValueError('unusable caption')
  if re.search(r'exemplo fict[ií]cio',row['caption'],re.I):raise ValueError('spoken disclaimer not allowed')
  if beat.get('claim_ids'):
   for claim in beat['claim_ids']:
    if claim not in {x['id'] for x in fx['claims']}:raise ValueError('unmapped claim')
 urls=fx['source_urls']
 if not urls or any(urlsplit(u).hostname not in ALLOWED_SOURCE_DOMAINS or urlsplit(u).scheme!='https' for u in urls):raise ValueError('untrusted URLs')
 if hfile(LOGO)!=LOGO_SHA:raise ValueError('Unapproved end-logo')
 return fx,rows

def block_timings(rows,manifest):
 blocks=manifest['blocks'];t=[];covered=[]
 for block in blocks:
  start,end=block['start'],block['end'];a=int(block['phrase_first'])-1;b=int(block['phrase_last'])
  if a!=len(covered) or b<=a or b>len(rows):raise ValueError('bad block boundaries')
  portion=rows[a:b];weights=[max(7,len(x.get('spoken',x['caption']))) for x in portion]
  cursor=start
  for j,(entry,weight) in enumerate(zip(portion,weights)):
   finish=end if j==len(weights)-1 else cursor+(end-cursor)*weight/sum(weights[j:])
   t.append({'start':cursor,'end':finish,'caption':entry['caption'],'method':'estimated_within_true_TTS_block'});
   cursor=finish
  covered+=list(range(a,b))
 if len(t)!=len(rows):raise ValueError('voice coverage incomplete')
 return t

def caption_groups(phrases):
 out=[]
 for p in phrases:
  words=p['caption'].split();weights=[max(1,len(w.strip('.,;:!?'))) for w in words]
  cursor=float(p['start']);times=[];remaining=sum(weights)
  for i,(w,n) in enumerate(zip(words,weights)):
   end=p['end'] if i==len(words)-1 else cursor+(p['end']-cursor)*n/remaining
   times.append({'start':cursor,'end':end,'method':'estimated_syllabic_char_weight'});cursor=end;remaining-=n
  run=[];stamps=[]
  for word,stamp in zip(words,times):
   if run and (len(run)>=3 or len(' '.join(run+[word]))>26):out.append((run,stamps));run=[];stamps=[]
   run.append(word);stamps.append(stamp)
   if word.endswith(('.',',','?','!',':',';')):
    out.append((run,stamps));run=[];stamps=[]
  if run:out.append((run,stamps))
 return out


def asr_phrase_timings(rows,manifest,asr):
 """Use independently recognized, time-aligned tokens rather than guessing char timing.
 Low-confidence words are retained in LAB only and counted for the independent gate.
 Do not accept ASR from a different waveform or script.
 """
 import unicodedata
 if asr.get('audio_sha256')!=hfile(Path(VOICE_AUDIO_PATH)):
  raise ValueError('ASR must be tied to the exact rendered mp3 SHA')
 if asr.get('reference_words')!=asr.get('recognized_words') or asr.get('wer')!=0:
  raise ValueError('ASR coverage not exact')
 words=asr.get('asr_words',[])
 expected=[];sizes=[]
 for row in rows:
  spoken=row.get('spoken',row['caption'])
  tks=re.findall(r'[+-]?\d+(?:[.,]\d+)*%?|[^\W\d_]+|[%€$]',unicodedata.normalize('NFC',spoken).casefold())
  expected.extend(tks);sizes.append(len(tks))
 if len(words)!=len(expected):raise ValueError('word tokenizer and ASR differ')
 offsets=[];pos=0
 for n in sizes:offsets.append((pos,pos+n));pos+=n
 data=[];unsafe=[]
 for ix,(start,end) in enumerate(offsets):
  segment=words[start:end]
  if not segment:raise ValueError('empty segment')
  for word in segment:
   if word['probability']<.6: unsafe.append(dict(phrase=ix,word=word['text'],confidence=word['probability']))
  caption_words=rows[ix]['caption'].split()
  if len(caption_words)==len(segment):
   stamps=[{'start':float(w['start']),'end':float(w['end']),'method':'independent_asr','probability':w['probability']} for w in segment]
   method='independent_word_asr'
  else:
   lo=float(segment[0]['start']);hi=float(segment[-1]['end'])
   weights=[max(1,len(x)) for x in caption_words]
   stamps=[];cur=lo;remaining=sum(weights)
   for i,weight in enumerate(weights):
    nxt=hi if i==len(weights)-1 else cur+(hi-cur)*weight/remaining
    stamps.append({'start':cur,'end':nxt,'method':'caption_mismatch_fallback_estimate','probability':None})
    remaining-=weight;cur=nxt
   method='caption_mismatch_fallback_estimate'
  data.append({'start':float(segment[0]['start']),'end':float(segment[-1]['end']),
              'caption':rows[ix]['caption'],'word_stamps':stamps,'method':method})
 return data,unsafe

def caption_groups_asr(phrases):
 out=[]
 for p in phrases:
  words=p['caption'].split()
  stamps=p['word_stamps']
  if len(words)!=len(stamps):raise ValueError('ASR word mapping malformed')
  run=[];times=[]
  for word,stamp in zip(words,stamps):
   if run and (len(run)>=3 or len(' '.join(run+[word]))>26):out.append((run,times));run=[];times=[]
   run.append(word);times.append(stamp)
   if word.endswith(('.',',','?','!',':',';')):
    out.append((run,times));run=[];times=[]
  if run:out.append((run,times))
 return out

def clinic(a,x,y,p=1):
 v.building(a,x,y,316,224,'health',p)
 # The legacy V5 asset labels generic non-house buildings "CRECHE". Replace the
 # precise old label, preserving the approved building silhouette and palette.
 a.box(x+54,y-270,209,52,Y,9)
 a.text(x+158,y-244,'SAÚDE',21,D)
 a.e(x+138,y-206,40,40,C);a.box(x+156,y-199,6,26,R);a.box(x+146,y-189,26,6,R)

def billboard(a,x,y,how='UNIDADE DE SAÚDE'):
 a.box(x-4,y-4,235,120,'#d7c39e',6);a.box(x,y,226,112,C,6)
 a.box(x+4,y+4,218,34,G,4);a.text(x+113,y+21,'OBRA ANUNCIADA',15,C)
 a.text(x+114,y+66,how,15,D);a.text(x+114,y+96,'CONSULTE O PRAZO',12,T)
 a.box(x+9,y+114,8,110,'#806444',2);a.box(x+212,y+114,8,110,'#806444',2)

def person(a,x,y,s,t,pose='stand',who='mom'):v.person(a,x,y,s,who,t,pose)
def city(t,shift):return b.city(t,shift)

def paper(a,title,labels,t,highlight=0):
 x,y,w,h=45,210,452,400;a.box(x+9,y+10,w,h,'#97ac96',12);a.box(x,y,w,h,C,12)
 a.box(x,y,w,62,G,10);a.text(x+w/2,y+30,title,21,C)
 for i,line in enumerate(labels):
  yy=y+113+i*61;a.box(x+27,yy-15,31,31,'#d8e5d0',5);a.text(x+42,yy,'✓' if i<highlight else '?',17,G)
  a.text(x+70,yy,line,17,D,anchor='lm');a.line([(x+70,yy+22),(x+w-18,yy+22)],'#cbd6c8',2)

def portal(a,title,t,q):
 x,y,w,h=54,240,431,385
 a.box(x-8,y-12,w+16,h+21,D,14);a.box(x,y,w,h,C,7)
 a.box(x,y,w,58,G,7);a.text(x+w/2,y+29,title,20,C)
 a.box(x+20,y+72,w-40,42,'#dfebdd',7);a.text(x+42,y+93,'Pesquise sua obra',17,G,anchor='lm')
 for i,label in enumerate(['Localização','Situação','Informações disponíveis']):
  yy=y+164+i*62;a.box(x+20,yy-19,w-40,42,'#dce6d6' if i==min(2,int(q*3.2)) else '#f2f0de',7);a.text(x+32,yy,label,17,G,anchor='lm')
 a.box(165,659,212,15,D,5)
 a.tag(270,705,'INTERFACE ILUSTRATIVA',C,G,14)

def stage(fx,beat,t,s,e):
 q=ease((t-s)/max(.05,e-s));role=beat['role'];scene=ROLE_SCENES[role];u=t-s
 dark=scene in ('caveat','contrast','brand')
 if scene=='brand':
  a=v.A(v.bg('dark').copy());a.e(172,288,196,196,'#32624b')
  logo=Image.open(LOGO).convert('RGBA').resize((360,360),Image.Resampling.LANCZOS)
  # A coordinates operate on native 540x960 then scaled by 2.
  logo=logo.resize((350,350),Image.Resampling.LANCZOS)
  a.im.paste(logo,(round(270*v.S-175),round(335*v.S-175)),logo)
  a.text(270,552,'FATOVIA',45,C)
  a.text(270,612,'Entender também é',22,C)
  a.text(270,644,'uma forma de fiscalizar.',22,Y)
  return a.im
 if scene in ('announcement','character','hope','waiting','reflect'):
  a=city(t,30*q)
  # recurrent named location, so background doesn't suddenly change story world
  clinic(a,158,650,.48 if scene=='waiting' else 1)
  if scene in ('announcement','character'):
   person(a,115+45*q,709,1.6,t,'walk' if scene=='character' else 'point')
   if scene=='announcement':billboard(a,280,350)
   else:a.tag(194,267,fx.get('person','PESSOA').upper(),C,G,21)
  elif scene=='hope':
   person(a,126,725,1.60,t,'point');person(a,254+25*q,715,1.64,t,'walk')
   a.tag(300,272,'ATENDIMENTO MAIS PERTO',D,Y,14)
  elif scene=='waiting':
   person(a,115,721,1.68,t,'sad');billboard(a,301,365)
   a.e(209,164,132,132,C);a.e(217,172,116,116,G)
   a.line([(275,230),(275+47*math.sin(u*5),230-47*math.cos(u*5))],Y,7)
   a.tag(274,337,'O TEMPO PASSA',C,R,17)
  else:
   person(a,134,725,1.6,t,'sad');a.e(224,230,93,93,Y);a.text(270,278,'?',64,D)
  return b.camera(a.im,1.03+.05*q,(270,497))
 if scene=='investigate':
  a=v.A(v.bg('room').copy());paper(a,'PERGUNTAS',('A obra começou?','Qual é o prazo?','Há recursos?'),t,int(q*3))
  person(a,128,739,1.53,t,'point');a.tag(300,652,'BUSQUE REGISTROS',D,Y,17)
  return b.camera(a.im,1.03+.05*q,(270,520))
 if scene=='portal':
  a=v.A(v.bg('paper').copy());title='OBRASGOV.BR' if beat['phrase_index'] in (8,9) else 'PORTAL DA TRANSPARÊNCIA';portal(a,title,t,q)
  person(a,113,763,1.30,t,'point');return b.camera(a.im,1.01+.055*q,(270,490))
 if scene=='caveat':
  a=v.A(v.bg('dark').copy());paper(a,'CADASTRO',('Pode não estar listado','Consulte o órgão','Peça esclarecimentos'),t,int(q*3))
  a.tag(270,681,'AUSÊNCIA ≠ INEXISTÊNCIA',C,R,18)
  return b.camera(a.im,1.01+.04*q,(270,500))
 if scene=='checklist':
  a=v.A(v.bg('paper').copy());paper(a,'CONFRONTE',('Anúncio divulgado','Prazo registrado','Situação informada'),t,int(q*3));return b.camera(a.im,1.02+.04*q,(270,500))
 if scene=='contrast':
  a=v.A(v.bg('paper').copy());a.box(34,262,218,395,'#c9d5bc',14);billboard(a,39,346,'PROJETO')
  a.box(279,262,224,395,'#c9d5bc',14);v.doc(a,297,330,190,272,'DOCUMENTOS',[("Prazo","consultar"),("Valor","consultar"),("Situação","consultar")],t)
  a.tag(270,713,'ANÚNCIO × REGISTROS',D,Y,18)
  return b.camera(a.im,1.02+.035*q,(270,490))
 raise ValueError('unsupported semantic role '+scene)

VOICE_AUDIO_PATH=''
def render(fixture,voice_json,audio_file,out,mode='full',asr_path=None):
 fx,rows=validate_fixture(fixture,voice_json)
 manifest=json.loads(Path(voice_json).with_name('R_episodio.json').read_text())
 if manifest['profile']!='Santa-R-1.0':raise ValueError('wrong voice profile')
 global VOICE_AUDIO_PATH
 VOICE_AUDIO_PATH=str(audio_file)
 if asr_path is not None:
  asr=json.loads(Path(asr_path).read_text(encoding='utf-8'))
  timings,asr_uncertain=asr_phrase_timings(rows,manifest,asr)
  cps=caption_groups_asr(timings)
 else:
  timings=block_timings(rows,manifest);asr_uncertain=[]
  cps=caption_groups(timings)
 cap=KineticCaptions(cps,W,H)
 duration=manifest['duration'];boundaries=[p['start'] for p in timings]+[duration]
 if duration<20 or duration>180:raise ValueError('duration outside lab budget')
 render_until=duration if mode=='full' else min(duration,15)
 frames=math.floor(render_until*FPS)
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
 cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(audio_file),'-t',str(render_until),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','22','-threads','4','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','128k','-movflags','+faststart',str(out)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 thumb=[];old=-1;started=time.time();framehash=[];logo_tag=fx['beats'][-1]['role']=='brand'
 for f in range(frames):
  t=f/FPS;i=min(len(timings)-1,bisect.bisect_right(boundaries,t)-1)
  i=max(0,i);im=stage(fx,fx['beats'][i],t,timings[i]['start'],timings[i]['end'])
  d=ImageDraw.Draw(im)
  # Lettering is separate from camera. Baseline remains fixed, as in V3 approved.
  if fx['beats'][i]['role']!='brand':
   d.text((60,116),'FATOVIA',font=v.ft(17),fill=D,stroke_width=2,stroke_fill=C)
  cap.draw(im,t)
  if i!=old:
   bimg=im.resize((144,256),Image.Resampling.LANCZOS);thumb.append(bimg);old=i
  if f%(FPS*12)==0:print('frames',f,'/',frames,flush=True)
  if f%(FPS*6)==0:framehash.append(hashlib.sha256(im.tobytes()).hexdigest())
  try:proc.stdin.write(im.tobytes())
  except BrokenPipeError:raise RuntimeError('encoder terminated')
 proc.stdin.close()
 if proc.wait():raise RuntimeError('ffmpeg encoder failed')
 subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
 ncols=6;sheet=Image.new('RGB',(ncols*144,math.ceil(len(thumb)/ncols)*256),D)
 for i,im in enumerate(thumb):sheet.paste(im,((i%ncols)*144,(i//ncols)*256))
 storyboard=out.with_suffix('.storyboard.jpg');sheet.save(storyboard,quality=91)
 report={'fixture':fx['id'],'profile':'Santa-R-1.0','visual_source':'FatoVia original V5 components','status':'lab_review_required','publish_allowed':False,'render_mode':mode,'duration_seconds':render_until,'fps':FPS,'size':[W,H],'generated_frames':frames,'scene_count':len(thumb),'storyboard_path':str(storyboard),'caption_timing':'independently recognized word timestamps with flagged uncertainties' if asr_path else 'estimated within genuine TTS blocks; ASR word audit pending','asr_low_confidence_words':asr_uncertain,'audio_source_sha256':hfile(Path(audio_file)),'video_sha256':hfile(out),'source_urls':fx['source_urls'],'logo_sha256':LOGO_SHA,'final_endcard_included':logo_tag and mode=='full','elapsed_sec':round(time.time()-started,2),'frame_hash_samples':framehash}
 out.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--fixture',required=True);parser.add_argument('--voice',required=True);parser.add_argument('--audio',required=True);parser.add_argument('--out',required=True);parser.add_argument('--mode',choices=['full','preview'],default='full');parser.add_argument('--asr');args=parser.parse_args()
 print(json.dumps(render(args.fixture,args.voice,args.audio,args.out,args.mode,args.asr),ensure_ascii=False),flush=True)