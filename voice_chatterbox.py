"""Compare Chatterbox multilingual CPU against previous Santa benchmark.
No human voice cloning, no paid services, no publisher."""
from pathlib import Path
import inspect, json, random, subprocess, time
import numpy as np
import soundfile as sf
import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from importlib.metadata import version

OUT=Path("chatterbox_samples")
OUT.mkdir(exist_ok=True)
rows=json.loads(Path("creche_roteiro.json").read_text(encoding="utf-8"))[7:15]
blocks=[" ".join(x.get("spoken",x["caption"]) for x in b) for b in (rows[:3],rows[3:5],rows[5:])]
assert all(len(b)<=300 for b in blocks), "Benchmark block exceeds limit"
torch.set_num_threads(4)
started=time.monotonic()
kwargs={"device":"cpu"}
supports_v3="t3_model" in inspect.signature(ChatterboxMultilingualTTS.from_pretrained).parameters
if supports_v3: kwargs["t3_model"]="v3"
model=ChatterboxMultilingualTTS.from_pretrained(**kwargs)
sr=int(model.sr)
report={"package":version("chatterbox-tts"),"model":"ResembleAI/chatterbox multilingual general (not dedicated PT-BR)","checkpoint":"v3" if supports_v3 else "package default","voice":"official built-in conditioning, no external reference","load_seconds":round(time.monotonic()-started,2),"variants":[]}
(OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
for name,ex,cfg in (("D",.5,.5),("E",.65,.35)):
    t0=time.monotonic()
    chunks=[];timeline=[];cursor=0
    for i,text in enumerate(blocks):
        # Same seed for the corresponding passage across the two profiles.
        seed=4260+i
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        print(f"{name}: block {i+1}/{len(blocks)}",flush=True)
        with torch.inference_mode():
            tensor=model.generate(text,language_id="pt",exaggeration=ex,cfg_weight=cfg,temperature=.7)
        a=tensor.detach().cpu().float().numpy().reshape(-1)
        if not len(a) or not np.isfinite(a).all() or np.max(np.abs(a))<1e-5:
            raise ValueError("Invalid waveform")
        start=cursor;cursor+=len(a);chunks.append(a)
        timeline.append({"text":text,"start":start/sr,"end":cursor/sr})
        if i<len(blocks)-1:
            gap=np.zeros(round(sr*.2),dtype=np.float32);chunks.append(gap);cursor+=len(gap)
    a=np.concatenate(chunks)
    a*=min(1.,.85/np.max(np.abs(a)))
    raw=OUT/(name+".raw.wav");wav=OUT/(name+".wav");mp3=OUT/(name+".mp3")
    sf.write(raw,a,sr,subtype="PCM_16")
    # Same target loudness used in the Santa comparison.
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),"-af","loudnorm=I=-16:TP=-1.5:LRA=7","-ar",str(sr),"-ac","1",str(wav)],check=True)
    raw.unlink()
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","128k",str(mp3)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],check=True)
    duration=sf.info(wav).frames/sr
    assert abs(duration-len(a)/sr)<.1
    report["variants"].append({"id":name,"exaggeration":ex,"cfg_weight":cfg,"duration_seconds":round(duration,3),"generation_seconds":round(time.monotonic()-t0,2),"timeline":timeline})
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
