"""FatoVia narration engine v2: Santa, CPU, sample-accurate phrase timeline."""
import argparse, json, re, subprocess, time
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro import KPipeline

SR=24000
PROFILES={
    "documental":{"speed":0.94,"pause":0.28,"question":0.38,"hook":0.97,"emphasis":0.91},
    "conversacional":{"speed":1.0,"pause":0.18,"question":0.24,"hook":1.02,"emphasis":0.96},
    "dinamico":{"speed":1.07,"pause":0.12,"question":0.2,"hook":1.09,"emphasis":1.01}
}
VOICE="pm_santa"
BENCHMARK=[
    {"caption":"A inflação caiu. Então, por que tudo continua tão caro?","style":"hook"},
    {"caption":"Porque a inflação mede a velocidade com que os preços sobem."},
    {"caption":"Se essa velocidade diminui, os preços ainda podem subir. Só que mais devagar.","style":"emphasis"}
]
EPISODE=[
    {"caption":"A inflação caiu. Então, por que tudo continua tão caro?","style":"hook"},
    {"caption":"Inflação é a variação do nível geral de preços ao longo do tempo."},
    {"caption":"Imagine uma cesta de compras que custa R$ 100.","spoken":"Imagine uma cesta de compras que custa cem reais."},
    {"caption":"Com uma inflação de 10%, ela passa a custar R$ 110.","spoken":"Com uma inflação de dez por cento, ela passa a custar cento e dez reais."},
    {"caption":"No ano seguinte, a inflação cai para 5%.","spoken":"No ano seguinte, a inflação cai para cinco por cento."},
    {"caption":"A cesta passa a custar R$ 115,50. Não volta a R$ 100.","spoken":"A cesta passa a custar cento e quinze reais e cinquenta centavos. Não volta a cem reais.","style":"emphasis"},
    {"caption":"É como um carro que diminui a velocidade. Ele continua avançando."},
    {"caption":"Quando a inflação é negativa, chamamos isso de deflação."},
    {"caption":"No Brasil, o IPCA é calculado pelo IBGE.","spoken":"No Brasil, o i pê cê a é calculado pelo i bê gê é."},
    {"caption":"Inflação menor não significa preços menores. Significa, em geral, preços subindo mais devagar.","style":"emphasis"}
]
def audio_chunk(pipe,text,speed):
    chunks=[]
    for r in pipe(text,voice=VOICE,speed=speed):
        a=r.audio
        if a is not None:
            if hasattr(a,"detach"): a=a.detach().cpu().numpy()
            chunks.append(np.asarray(a,dtype=np.float32).reshape(-1))
    if not chunks: raise ValueError("Empty synthesis")
    a=np.concatenate(chunks)
    if not np.isfinite(a).all() or np.max(np.abs(a))<1e-5: raise ValueError("Invalid speech")
    # Remove excess silence only at edges, preserving breath and internal pauses.
    idx=np.flatnonzero(np.abs(a)>0.003)
    if len(idx):
        a=a[max(0,idx[0]-int(SR*.065)):min(len(a),idx[-1]+int(SR*.09)+1)]
    fade=min(int(SR*.008),len(a)//2)
    if fade:
        a[:fade]*=np.linspace(0,1,fade); a[-fade:]*=np.linspace(1,0,fade)
    return a
def timestamp(sec):
    ms=round(sec*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
def render(pipe,phrases,profile,out):
    cfg=PROFILES[profile]; cursor=0; parts=[]; timeline=[]; started=time.monotonic()
    for i,p in enumerate(phrases):
        caption=p["caption"]; spoken=p.get("spoken",caption)
        speed=cfg.get(p.get("style","speed"),cfg["speed"])
        speed=float(speed)
        a=audio_chunk(pipe,spoken,speed)
        start=cursor; cursor+=len(a); parts.append(a)
        timeline.append({"scene":i+1,"caption":caption,"spoken":spoken,"start_sample":start,"end_sample":cursor,"start":start/SR,"end":cursor/SR,"speed":speed})
        if i<len(phrases)-1:
            pause=cfg["question"] if spoken.endswith("?") else cfg["pause"]
            gap=np.zeros(round(pause*SR),dtype=np.float32); parts.append(gap); cursor+=len(gap)
    a=np.concatenate(parts); a*=min(1.,0.85/np.max(np.abs(a)))
    out.parent.mkdir(parents=True,exist_ok=True)
    raw=out.with_suffix(".raw.wav"); wav=out.with_suffix(".wav"); mp3=out.with_suffix(".mp3")
    sf.write(raw,a,SR,subtype="PCM_16")
    # Normalize with no resampling drift (dynamic loudnorm internally upsamples).
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),"-af","loudnorm=I=-16:TP=-1.5:LRA=7","-ar",str(SR),"-ac","1",str(wav)],check=True)
    raw.unlink()
    duration=sf.info(wav).frames/SR
    assert abs(duration-len(a)/SR)<.05, "Timing drift"
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","128k",str(mp3)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],check=True)
    out.with_suffix(".json").write_text(json.dumps({"voice":VOICE,"profile":profile,"sample_rate":SR,"duration":duration,"phrases":timeline},ensure_ascii=False,indent=2),encoding="utf-8")
    out.with_suffix(".srt").write_text("\n\n".join(f'{i+1}\n{timestamp(p["start"])} --> {timestamp(p["end"])}\n{p["caption"]}' for i,p in enumerate(timeline))+"\n",encoding="utf-8")
    return {"file":out.name,"profile":profile,"duration_s":round(duration,3),"cpu_seconds":round(time.monotonic()-started,2),"phrases":len(phrases)}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("samples"))
    parser.add_argument("--input",type=Path,help="JSON array of {caption, spoken?, style?}")
    parser.add_argument("--profile",choices=PROFILES,default="documental")
    args=parser.parse_args()
    pipe=KPipeline(lang_code="p",device="cpu",repo_id="hexgrad/Kokoro-82M")
    if args.input:
        phrases=json.loads(args.input.read_text(encoding="utf-8"))
        report=[render(pipe,phrases,args.profile,args.out/"narracao")]
    else:
        report=[render(pipe,BENCHMARK,p,args.out/("santa_"+p)) for p in PROFILES]
        report.append(render(pipe,EPISODE,"documental",args.out/"santa_episodio"))
    (args.out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
