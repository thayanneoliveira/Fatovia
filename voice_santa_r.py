"""Santa R: standalone recreation of the preferred listening sample.
CPU only; no Chatterbox, expiring artifact dependency or publication."""
import argparse, json, re, subprocess, time, hashlib, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import pyworld as pw
from kokoro import KPipeline
SR=24000
PERIOD=5.
SPEED=.97
NORM="loudnorm=I=-16:TP=-1.5:LRA=7"
C_FILTER="highpass=f=70,equalizer=f=3200:t=q:w=1.2:g=-1.7,equalizer=f=6500:t=q:w=1:g=-1.5,"+NORM

def validate(a):
    if a.ndim!=1 or not len(a) or not np.isfinite(a).all() or np.max(np.abs(a))<1e-5:
        raise ValueError("invalid audio")
    return a

def load_rows(path):
    rows=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows,list) or not rows or any(not isinstance(p,dict) or not isinstance(p.get("caption"),str) or not p["caption"].strip() or not isinstance(p.get("spoken",p["caption"]),str) or not p.get("spoken",p["caption"]).strip() for p in rows):
        raise ValueError("invalid script")
    return rows

def block_text(rows):
    return " ".join(p.get("spoken",p["caption"]) for p in rows)

def make_blocks(rows,groups=None):
    if groups is not None:
        if not all(type(n)==int and n>0 for n in groups) or sum(groups)!=len(rows):
            raise ValueError("group counts must cover exactly all phrases")
        out=[];cursor=0
        for n in groups:
            out.append(rows[cursor:cursor+n]);cursor+=n
    else:
        out=[];current=[]
        for row in rows:
            if current and (len(current)>=3 or len(block_text(current+[row]))>240):
                out.append(current);current=[]
            current.append(row)
        if current: out.append(current)
    if any(len(block_text(b))>300 for b in out): raise ValueError("block too long")
    if [p for b in out for p in b]!=rows: raise ValueError("text coverage")
    return out

def norm_text(s):
    return re.sub(r"\s+","",s).casefold()

def synthesize(pipe, blocks, exact_gaps=None):
    pieces=[];timeline=[];cursor=0;phrase=0
    for i,b in enumerate(blocks):
        spoken=block_text(b)
        chunks=[]; graphemes=[]
        for result in pipe(spoken,voice="pm_santa",speed=SPEED,split_pattern=None):
            if result.audio is None: raise ValueError("missing chunk audio")
            phonemes=getattr(result,"phonemes",None)
            if isinstance(phonemes,str) and len(phonemes)>510: raise ValueError("phoneme limit")
            g=getattr(result,"graphemes",None)
            if isinstance(g,str): graphemes.append(g)
            a=result.audio
            if hasattr(a,"detach"): a=a.detach().cpu().numpy()
            chunks.append(validate(np.asarray(a,dtype=np.float32).reshape(-1)))
        if not chunks: raise ValueError("empty block")
        # Grapheme coverage is a text check only, not a speech recognition check.
        if graphemes and norm_text("".join(graphemes))!=norm_text(spoken):
            raise ValueError("pipeline text coverage mismatch: "+spoken)
        a=np.concatenate(chunks);start=cursor;cursor+=len(a)
        pieces.append(a)
        timeline.append({"block":i+1,"phrase_first":phrase+1,"phrase_last":phrase+len(b),"caption":" ".join(p["caption"] for p in b),"spoken":spoken,"start_sample":start,"end_sample":cursor,"start":start/SR,"end":cursor/SR,"chunks":len(chunks)})
        phrase+=len(b)
        if i<len(blocks)-1:
            pause=exact_gaps[i] if exact_gaps is not None else (.24 if spoken.endswith("?") else .20)
            gap=np.zeros(round(SR*pause),dtype=np.float32);pieces.append(gap);cursor+=len(gap)
    return validate(np.concatenate(pieces)),timeline

def ffmpeg(*args):
    subprocess.run(["ffmpeg","-v","error","-y",*map(str,args)],check=True)
def reconstruct(a):
    a=np.ascontiguousarray(a,dtype=np.float64)
    f,t=pw.dio(a,SR,frame_period=PERIOD,f0_floor=65,f0_ceil=500)
    f=pw.stonemask(a,f,t,SR)
    sp=pw.cheaptrick(a,f,t,SR)
    ap=pw.d4c(a,f,t,SR)
    return validate(pw.synthesize(f,sp,ap,SR,PERIOD))
def timestamp(sec):
    ms=round(sec*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
def render(pipe,rows,blocks,out,gaps=None):
    t=time.monotonic()
    a,timeline=synthesize(pipe,blocks,gaps)
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw=Path(tmp)/"raw.wav"; c=Path(tmp)/"C.wav"; r=Path(tmp)/"R.wav"
        # Recreate C exactly: no edge cuts or pre-normalization in the original benchmark.
        sf.write(raw,a,SR,subtype="PCM_16")
        ffmpeg("-i",raw,"-af",C_FILTER,"-ar",SR,"-ac",1,c)
        src,sr=sf.read(c,dtype="float64")
        if sr!=SR: raise ValueError("wrong sample rate")
        # Reconstruct unmodified acoustic parameters, as in R. Whole-episode processing.
        rec=reconstruct(src);rec*=min(1.,.85/np.max(np.abs(rec)))
        sf.write(r,rec,SR,subtype="PCM_16")
        wav=out.with_suffix(".wav");mp3=out.with_suffix(".mp3")
        ffmpeg("-i",r,"-af",NORM,"-ar",SR,"-ac",1,wav)
        ffmpeg("-i",wav,"-c:a","libmp3lame","-b:a","128k",mp3)
        ffmpeg("-i",mp3,"-f","null","-")
    info=sf.info(wav);duration=info.frames/SR
    if abs(duration-len(a)/SR)>.05: raise ValueError("timing drift")
    wave,_=sf.read(wav)
    peak=float(np.max(np.abs(wave)))
    if not np.isfinite(wave).all() or peak>=.999: raise ValueError("invalid mastered waveform")
    report={"profile":"Santa-R-1.0","status":"lab_only","sample_rate":SR,"duration":duration,"seconds":round(time.monotonic()-t,2),"phrases":len(rows),"blocks":timeline,"caption_precision":"block boundaries, not word-level","peak":peak,"sha256_mp3":hashlib.sha256(mp3.read_bytes()).hexdigest(),"limitations":"No ASR or listening evaluation performed; only technical checks."}
    out.with_suffix(".json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    out.with_suffix(".srt").write_text("\n\n".join(f'{i+1}\n{timestamp(b["start"])} --> {timestamp(b["end"])}\n{b["caption"]}' for i,b in enumerate(timeline))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="blocks"},ensure_ascii=False),flush=True)
    return report
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("creche_roteiro.json"));p.add_argument("--out",type=Path,default=Path("santa_r_samples"));p.add_argument("--benchmark",action="store_true")
    args=p.parse_args()
    rows=load_rows(args.input)
    pipe=KPipeline(lang_code="p",device="cpu",repo_id="hexgrad/Kokoro-82M")
    if args.benchmark:
        excerpt=rows[7:15]
        render(pipe,excerpt,make_blocks(excerpt,[3,2,3]),args.out/"R_regressao",[.16,.24])
    render(pipe,rows,make_blocks(rows),args.out/"R_episodio")
if __name__=="__main__": main()
