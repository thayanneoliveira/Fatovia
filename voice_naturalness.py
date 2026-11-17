"""Controlled Santa naturalness experiment. No publisher, no paid APIs."""
import json, time, subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro import KPipeline
from voice_engine import render, audio_chunk, SR
out=Path("naturalness");out.mkdir(exist_ok=True)
script=json.loads(Path("creche_roteiro.json").read_text(encoding="utf-8"))
# Same approved text in all three variants, including the original punctuation.
phrases=script[7:15]
pipe=KPipeline(lang_code="p",device="cpu",repo_id="hexgrad/Kokoro-82M")
baseline=render(pipe,phrases,"documental",out/"A")
blocks=[phrases[:3],phrases[3:5],phrases[5:]]
def synthesize_blocks():
    pieces=[]; timing=[]; cursor=0
    for i,block in enumerate(blocks):
        text=" ".join(p.get("spoken",p["caption"]) for p in block)
        # Preserve contextual intonation within the whole passage; only cut at thought boundaries.
        chunks=[]
        for result in pipe(text,voice="pm_santa",speed=0.97,split_pattern=None):
            if result.audio is not None:
                a=result.audio
                if hasattr(a,"detach"): a=a.detach().cpu().numpy()
                chunks.append(np.array(a,dtype=np.float32).reshape(-1))
        if not chunks: raise ValueError("empty block")
        a=np.concatenate(chunks)
        if not np.isfinite(a).all() or np.max(np.abs(a))<1e-5: raise ValueError("invalid block")
        start=cursor
        pieces.append(a);cursor+=len(a)
        timing.append({"text":text,"start":start/SR,"end":cursor/SR})
        if i<len(blocks)-1:
            gap=np.zeros(round(SR*[0.16,0.24][i]),dtype=np.float32)
            pieces.append(gap);cursor+=len(gap)
    return np.concatenate(pieces),timing
def master(raw,name,filters):
    wav=out/(name+".wav");mp3=out/(name+".mp3")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),"-af",filters,"-ar",str(SR),"-ac","1",str(wav)],check=True)
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","128k",str(mp3)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],check=True)
    return round(sf.info(wav).frames/SR,3)
t=time.monotonic()
a,timing=synthesize_blocks()
raw=out/"blocks.raw.wav"
sf.write(raw,a,SR,subtype="PCM_16")
norm="loudnorm=I=-16:TP=-1.5:LRA=7"
b=master(raw,"B",norm)
# Same neural waveform as B; only mild mastering changes. No artificial breath or pitch injection.
c=master(raw,"C","highpass=f=70,equalizer=f=3200:t=q:w=1.2:g=-1.7,equalizer=f=6500:t=q:w=1:g=-1.5,"+norm)
raw.unlink()
assert abs(b-c)<.05
report={"A":{"description":"Original Santa, per-sentence","seconds":baseline["duration_s"]},"B":{"description":"Santa in coherent speech blocks","seconds":b},"C":{"description":"Identical to B, with mild acoustic mastering","seconds":c},"generation_seconds":round(time.monotonic()-t,2),"block_timing":timing,"notes":"B and C compare mastering only. A vs B also changes pacing and segmentation. No claim of better naturalness until blind listening."}
(out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
