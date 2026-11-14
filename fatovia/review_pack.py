"""Private-to-workflow artifact with actual approved JPEGs, not a publication action."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .editorial_audit import paths_for,inspect_files,approved
from .engine import load,now_local
from .render import cards_for

OUT=Path("review-output")

def visual_check(item):
    try:
        inspect_files(item)
        for name in paths_for(item):
            with Image.open(name) as im:
                if im.format!="JPEG" or im.size!=(1080,1350) or im.mode!="RGB":
                    return False
                im.load()
        return True
    except Exception:
        return False

def sheet(item,target):
    paths=paths_for(item)
    # Contact sheet of actual files, not a new representation of card text.
    thumb=(270,338)
    canvas=Image.new("RGB",(4*290+20,2*370+70),"#F5F1E7")
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",22)
    draw.text((20,15),item["title"]+" | FatoVia | REVISÃO",font=font,fill="#123E31")
    for i,p in enumerate(paths):
        with Image.open(p) as im:
            page=im.copy()
            page.thumbnail(thumb)
            x=20+(i%4)*290; y=60+(i//4)*370
            canvas.paste(page,(x,y))
            draw.text((x,y+340),str(i+1).zfill(2),font=font,fill="#123E31")
    canvas.save(target,"PNG")

def main():
    now=now_local()
    state=load("data/state.json")
    preflight=load("data/preflight_report.json")
    okay={(r["id"],r["version"]) for r in preflight.get("rows",[]) if r.get("ready_for_documentary_pilot")}
    OUT.mkdir(exist_ok=True)
    rows=[]
    for item in state.get("pending",[])[:8]:
        if (item["id"],item["version"]) not in okay or not approved(item,now) or not visual_check(item):
            continue
        folder=OUT/item["id"].replace(":","-")
        folder.mkdir(exist_ok=True)
        sheet(item,folder/"contato.png")
        for source in paths_for(item):
            (folder/Path(source).name).write_bytes(Path(source).read_bytes())
        record={"id":item["id"],"version":item["version"],"title":item["title"],"source":item["public_url"],
                "caption":item["caption"],"cards":[{"headline":h,"body":b,"footer":f} for h,b,f in cards_for(item)],
                "status":"requires_editorial_review","publication_authorized":False}
        (folder/"conteudo.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
        rows.append({"id":item["id"],"folder":folder.name,"status":record["status"]})
    (OUT/"manifest.json").write_text(json.dumps({"items":rows,"publication_authorized":False},ensure_ascii=False,indent=2)+"\n")
    print("REVIEW_PACK",len(rows),"carousels; no publication")
if __name__=="__main__":
    main()
