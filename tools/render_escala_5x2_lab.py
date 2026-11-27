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
from escala_5x2_v6_scenes import scene, NAMES

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
    # Shot boundaries tied to actual matched speech. Sub-beats use nearest
    # aligned word, rather than uniform cuts or new synthesis.
    cues=[(0,0),(0,7),(1,0),(2,0),(2,3),(2,7),(3,0),(4,0),
          (5,0),(7,0),(8,0),(8,6),(8,10),(9,0),(11,0),(12,0),
          (14,0),(14,6),(15,0),(16,0),(18,0),(19,0),(20,0),(21,0)]
    ref_by_line={}
    for pos,line in enumerate(owners):ref_by_line.setdefault(line,[]).append(pos)
    word_match={}
    for a,b,n in match.get_matching_blocks():
        for j in range(n):word_match[a+j]=b+j
    shot_starts=[]
    for li,offset in cues:
        indices=ref_by_line[li]
        candidates=[p for p in indices if p in word_match]
        if not candidates:raise ValueError('Missing aligned shot cue')
        goal=indices[min(offset,len(indices)-1)]
        hit=min(candidates,key=lambda p:abs(p-goal))
        shot_starts.append(words[word_match[hit]]['start'])
    shot_starts[0]=0.
    if len(shot_starts)!=len(NAMES) or any(b-a<.32 for a,b in zip(shot_starts,shot_starts[1:])):
        raise ValueError('Shot cues too close or out of order')
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
    target=out/'FatoVia_Escala_5x2_Algenib_V6_Teste.mp4'
    frames=math.ceil((duration+1.5)*FPS)
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(audio),'-map','0:v','-map','1:a','-af','loudnorm=I=-16:TP=-1.5:LRA=11,apad','-t',str(frames/FPS),'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-threads','4','-c:a','aac','-ar','48000','-ac','2','-b:a','160k','-movflags','+faststart',str(target)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    thumb=[];old=-1
    for f in range(frames):
        t=f/FPS;i=min(len(NAMES)-1,max(0,bisect.bisect_right(shot_starts,t)-1))
        if t>=duration:im=closing
        else:
            im=scene(i,t-shot_starts[i]);cap.draw(im,t)
            if i!=old:
                thumb.append(im.resize((180,320),Image.Resampling.LANCZOS));old=i
                print('scene',i+1,flush=True)
                if i==0:im.save(out/'cover.png')
        proc.stdin.write(im.tobytes())
    proc.stdin.close()
    if proc.wait():raise RuntimeError('encoder failed')
    subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    # Verify the actual MP4 audio, not the detached source WAV.
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(target)]))
    streams=probe['streams'];video=next(s for s in streams if s['codec_type']=='video');audio_stream=next(s for s in streams if s['codec_type']=='audio')
    assert (video['width'],video['height'])==(W,H) and video['avg_frame_rate']=='24/1'
    assert audio_stream['codec_name']=='aac' and audio_stream['channels']==2
    assert abs(float(audio_stream['duration'])-float(video['duration']))<.15
    audio_pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(target),'-map','0:a:0','-ac','1','-ar','16000','-f','f32le','-'])
    pcm=np.frombuffer(audio_pcm,dtype='<f4');rms=float(np.sqrt(np.mean(pcm**2)));peak=float(np.max(np.abs(pcm)))
    if not .025<rms<.4 or peak>=1:raise ValueError('Integrated audio silent, too loud or clipping')
    if len(thumb)!=len(NAMES):raise ValueError('Incomplete storyboard')
    sheet=Image.new('RGB',(180*6,320*math.ceil(len(thumb)/6)),D)
    for i,im in enumerate(thumb):sheet.paste(im,(180*(i%6),320*(i//6)))
    sheet.save(out/'storyboard.jpg',quality=93)
    (out/'report.json').write_text(json.dumps({'status':'lab_only_review_required','publish_allowed':False,'voice':'Algenib','asr_match_ratio':ratio,'asr_words':words,'scenes':len(thumb),'duration':frames/FPS,'resolution':[W,H],'fps':FPS,'audio_sha256':digest(audio),'video_sha256':digest(target),'visual':'V6 independent editorial vector art; 24 unique compositions; no Maria characters/scenes','shot_names':NAMES,'shot_starts':shot_starts,'integrated_audio':{'codec':audio_stream['codec_name'],'channels':audio_stream['channels'],'rms':rms,'peak':peak,'duration':audio_stream['duration']},'review_pending':['originality, diversity and pacing against Maria reference','listen to narration','word alignment spot check','independent factual review']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
