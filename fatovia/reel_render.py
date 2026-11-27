"""Render reviewed-plan draft with sealed Algenib audio; no publish or approval."""
import argparse,bisect,difflib,hashlib,json,math,subprocess,unicodedata,wave
from pathlib import Path
import numpy as np
from PIL import Image
from faster_whisper import WhisperModel
from .v5_legacy.kinetic_captions import KineticCaptions
from .reel_art import scene
from .narration import generate
from .engine import save,load
W,H,FPS=1080,1920,24
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(s):return "".join(c for c in unicodedata.normalize("NFKD",s.casefold()) if c.isalnum() and not unicodedata.combining(c))
def render(plan,audio,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    seal=load(audio.with_suffix(".json"))
    if seal["voice"]!="Algenib" or seal["sha256"]!=sha(audio):raise ValueError("audio seal")
    with wave.open(str(audio)) as f:duration=f.getnframes()/f.getframerate()
    if not 15<=duration<=118.4:raise ValueError("duration out of bounds")
    pcm=subprocess.check_output(["ffmpeg","-v","error","-i",str(audio),"-ac","1","-ar","16000","-f","f32le","-"])
    model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
    segments,_=model.transcribe(np.frombuffer(pcm,dtype="<f4").copy(),language="pt",word_timestamps=True,beam_size=5)
    words=[dict(text=w.word.strip(),start=float(w.start),end=float(w.end)) for seg in segments for w in seg.words if norm(w.word) and w.end>w.start]
    ref=[];owners=[]
    for i,line in enumerate(plan["script"].strip().splitlines()):
        for w in line.split():
            if norm(w):ref.append(norm(w));owners.append(i)
    m=difflib.SequenceMatcher(a=ref,b=[norm(w["text"]) for w in words],autojunk=False)
    if m.ratio()<.94:raise ValueError("ASR disagreement")
    starts=[]
    matches={a+j:b+j for a,b,n in m.get_matching_blocks() for j in range(n)}
    for i in range(len(plan["shots"])):
        hits=[words[matches[j]]["start"] for j,k in enumerate(owners) if k==i and j in matches]
        if not hits:raise ValueError("missing aligned shot")
        starts.append(min(hits))
    starts[0]=0
    if any(b-a<.4 for a,b in zip(starts,starts[1:])):raise ValueError("shot overlap")
    groups=[];run=[]
    for w in words:
        if run and (len(run)>=3 or len(" ".join(x["text"] for x in run+[w]))>24):
            groups.append(([x["text"] for x in run],run));run=[]
        run.append(w)
        if w["text"].endswith((".",",","?","!",":",";")):groups.append(([x["text"] for x in run],run));run=[]
    if run:groups.append(([x["text"] for x in run],run))
    cap=KineticCaptions(groups,W,H)
    logo=Path("assets/fatovia-approved.png")
    if sha(logo)!="df41d13bb11db469d2850c69c0ece41eeb7e33a262e7622b59afb21ef81c7ce6":raise ValueError("logo mismatch")
    closing=Image.new("RGB",(W,H),"#142f29");lg=Image.open(logo).convert("RGBA");lg.thumbnail((460,460));closing.paste(lg,((W-lg.width)//2,(H-lg.height)//2),lg)
    frames=math.ceil((duration+1.5)*FPS);target=out/"reel.mp4"
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",str(audio),"-map","0:v","-map","1:a","-af","loudnorm=I=-16:TP=-1.5:LRA=11,apad","-t",str(frames/FPS),"-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-threads","4","-c:a","aac","-ar","48000","-ac","2","-b:a","160k","-movflags","+faststart",str(target)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE);thumb=[];old=-1
    try:
        for f in range(frames):
            t=f/FPS;i=max(0,bisect.bisect_right(starts,t)-1)
            im=closing if t>=duration else scene(plan,i,t-starts[i])
            if t<duration:
                cap.draw(im,t)
                if i!=old:
                    thumb.append(im.resize((180,320),Image.Resampling.LANCZOS));old=i
            proc.stdin.write(im.tobytes())
    finally:
        proc.stdin.close()
        code=proc.wait()
    if code:raise RuntimeError("encoding failed")
    subprocess.run(["ffmpeg","-v","error","-i",str(target),"-f","null","-"],check=True)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",str(target)]))["streams"]
    v=next(s for s in probe if s["codec_type"]=="video");a=next(s for s in probe if s["codec_type"]=="audio")
    if (v["width"],v["height"],v["avg_frame_rate"],v["codec_name"],a["codec_name"],a["channels"])!=(1080,1920,"24/1","h264","aac",2) or abs(float(v["duration"])-float(a["duration"]))>.15:raise ValueError("A/V specs")
    samples=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(target),"-map","0:a:0","-ac","1","-ar","16000","-f","f32le","-"]),dtype="<f4")
    rms=float(np.sqrt(np.mean(samples**2)));peak=float(np.max(np.abs(samples)))
    if not .025<rms<.4 or peak>=1 or len(thumb)!=len(plan["shots"]):raise ValueError("audio or shot gate")
    sheet=Image.new("RGB",(180*6,320*math.ceil(len(thumb)/6)),"#142f29")
    for i,im in enumerate(thumb):sheet.paste(im,(180*(i%6),320*(i//6)))
    sheet.save(out/"storyboard.jpg",quality=94)
    save(out/"report.json",{"status":"draft_requires_independent_review","publish_allowed":False,"video_sha256":sha(target),"audio_sha256":sha(audio),"script_sha256":plan["script_sha256"],"caption_sha256":hashlib.sha256(plan["caption"].encode()).hexdigest(),"asr_match":m.ratio(),"word_count":len(words),"shots":len(thumb),"duration":frames/FPS,"resolution":[W,H],"fps":FPS,"rms":rms,"peak":peak,"voice":"Algenib","visual_revision":"V6","logo_sha256":sha(logo)})
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);ap.add_argument("--cache",type=Path,required=True);args=ap.parse_args()
    plan=load(args.out/"plan.json")
    audio=generate(plan["script"],args.cache)
    render(plan,audio,args.out)
if __name__=="__main__":main()
