"""Inspect previously published FatoVia cover designs via their own Instagram media URLs."""
import base64, io, json
from collections import Counter
from pathlib import Path
import requests
from PIL import Image

for entry in json.loads(Path("data/_visual_refs_20261102.json").read_text()):
    name=entry["label"]
    try:
        response=requests.get(entry["url"],timeout=25,headers={"User-Agent":"Mozilla/5.0"})
        response.raise_for_status()
        img=Image.open(io.BytesIO(response.content)).convert("RGB")
        thumb=img.copy()
        thumb.thumbnail((380,475))
        quant=img.resize((100,125)).quantize(colors=8,method=Image.Quantize.MEDIANCUT).convert("RGB")
        cnt=Counter(quant.getdata())
        palette=[{"rgb":"#%02X%02X%02X"%color,"coverage":round(n/(100*125),3)} for color,n in cnt.most_common(6)]
        b=io.BytesIO()
        thumb.save(b,format="JPEG",quality=66,optimize=True)
        print("FATOVIA_PALETTE "+name+" "+json.dumps(palette),flush=True)
        print("FATOVIA_REF "+name+" "+base64.b64encode(b.getvalue()).decode(),flush=True)
    except Exception as exc:
        print("FATOVIA_ERROR "+name+" "+str(exc)[:200],flush=True)
