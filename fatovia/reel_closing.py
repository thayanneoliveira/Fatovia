"""Replace a known closing panel with the exact owner-approved PNG; preserve narration.
Generic input requires explicit closing timestamp. Never infer it or publish."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image,ImageDraw
from .brand import approved_logo,fit_logo

def probe(path):
    r=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],check=True,capture_output=True,text=True)
    return json.loads(r.stdout)

def export(source,output,start,policy):
    logo=approved_logo(policy)
    if logo is None:raise ValueError("Original approved logo PNG and matching hash required")
    if source.resolve()==output.resolve():raise ValueError("Do not overwrite source")
    data=probe(source);duration=float(data["format"]["duration"])
    video=next(x for x in data["streams"] if x["codec_type"]=="video")
    if (video["width"],video["height"])!=(1080,1920) or not 0<start<duration-1:raise ValueError("Invalid dimensions or endcard timestamp")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        # Overlay only the provisional brand panel. Caption zone and footer remain unchanged.
        panel=Image.new("RGBA",(1080,690))
        d=ImageDraw.Draw(panel)
        for y in range(690):
            t=y/689
            d.line((0,y,1080,y),fill=(round(34-14*t),round(75-21*t),round(59-15*t),255))
        mark=fit_logo(logo,680,460)
        panel.paste(mark,((1080-mark.width)//2,(570-mark.height)//2),mark)
        # Retain the approved closing wording below the logo.
        from PIL import ImageFont
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",42)
        d.text((540,600),"Entender também é uma forma de fiscalizar.",font=font,anchor="mm",fill="#F5F1E7")
        overlay=Path(folder)/"brand.png";panel.save(overlay)
        filter=f"[0:v][1:v]overlay=0:500:enable='gte(t,{start:.3f})'[v]"
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(source),"-i",str(overlay),"-filter_complex",filter,"-map","[v]","-map","0:a:0","-c:v","libx264","-preset","fast","-crf","23","-maxrate","3000k","-bufsize","6000k","-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-b:a","128k","-movflags","+faststart",str(output)],check=True)
    out=probe(output)
    video=next(x for x in out["streams"] if x["codec_type"]=="video")
    audio=next(x for x in out["streams"] if x["codec_type"]=="audio")
    if (video["codec_name"]!="h264" or (video["width"],video["height"])!=(1080,1920)
        or video["r_frame_rate"]!="24/1" or audio["codec_name"]!="aac" or audio["sample_rate"]!="48000"
        or abs(float(out["format"]["duration"])-duration)>.15 or output.stat().st_size>95_000_000):raise ValueError("MP4 technical preflight failed")
    subprocess.run(["ffmpeg","-v","error","-i",str(output),"-f","null","-"],check=True)
    return {"status":"technical_preflight_only","sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"bytes":output.stat().st_size,"duration":float(out["format"]["duration"]),"closing_start":start,"publish_allowed":False,"requires":"independent visual, source, audio and identity review"}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--closing-start",type=float,required=True);p.add_argument("--policy",default="data/multiformat_experiment.json");a=p.parse_args()
    result=export(a.source,a.output,a.closing_start,a.policy);a.output.with_suffix(".preflight.json").write_text(json.dumps(result,indent=2));print(json.dumps(result))
