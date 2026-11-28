"""Render exact migrated drafts using the approved logo. No state or Meta changes."""
import json
from pathlib import Path
from .engine import classify,digest
from .didactic import MANIFEST
from .render import render
from .brand import approved_logo
from .premium_carousel import REVISION
from PIL import Image,ImageDraw
def main():
    if approved_logo() is None: raise ValueError("approved_logo_unavailable")
    drafts=json.loads((MANIFEST.parent/"carousel_premium_drafts.json").read_text())["items"]
    rows=json.loads(MANIFEST.read_text())["items"]
    root=Path("premium-preview")
    for draft in drafts:
        row=next(r for r in rows if (r["id"],r["version"])==(draft["id"],draft["version"]))
        item={k:row[k] for k in ("id","version","title","summary","stage","stage_date")}
        ident=item["id"].split(":")[1]
        item.update(topics=classify(item["summary"]),summary_hash=digest(item["summary"].casefold()),source_url="https://dadosabertos.camara.leg.br/api/v2/proposicoes/"+ident,public_url="https://www.camara.leg.br/propostas-legislativas/"+ident)
        render(item,root,premium=True)
        assert item["template_revision"]==REVISION and len(item["cards"])==7
        folder=Path(item["cards"][0]).parent
        sheet=Image.new("RGB",(7*216,270),"#F5F1E7")
        for i,path in enumerate(item["cards"]):
            with Image.open(path) as im:
                assert im.size==(1080,1350)
                sheet.paste(im.resize((216,270)),(i*216,0))
        sheet.save(folder/"preview.jpg",quality=93)
        (folder/"draft.json").write_text(json.dumps({"caption":item["caption"],"status":"preview_only","publication_authorized":False},ensure_ascii=False,indent=2))
    print("Premium preview: "+str(len(drafts)*7)+" cards; no publication")
if __name__=="__main__": main()
