"""Deterministic closing-brand assets. Missing/unverified source never substitutes a logo."""
import hashlib
import json
import re
from pathlib import Path
from PIL import Image

def approved_logo(policy_path="data/multiformat_experiment.json"):
    try:
        p=json.loads(Path(policy_path).read_text(encoding="utf-8"))
        r=p["approved_logo"]
        h=r["sha256"];path=Path(r["path"])
        if not isinstance(h,str) or not re.fullmatch(r"[a-f0-9]{64}",h):return None
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(Path("assets").resolve()):return None
        if path.stat().st_size>10_000_000 or hashlib.sha256(path.read_bytes()).hexdigest()!=h:return None
        with Image.open(path) as logo:
            if logo.format!="PNG" or logo.width<64 or logo.height<64 or max(logo.size)>4096:return None
            return logo.convert("RGBA")
    except (OSError,KeyError,ValueError,TypeError,AttributeError):return None

def fit_logo(logo,width,height):
    image=logo.copy().convert("RGBA")
    image.thumbnail((width,height),Image.Resampling.LANCZOS)
    return image

def carousel_header(picture,logo):
    """Replace provisional header on card 7, retain sources and CTA."""
    from PIL import ImageDraw
    draw=ImageDraw.Draw(picture)
    draw.rectangle((65,43,630,135),fill="#123E31")
    mark=fit_logo(logo,510,85)
    picture.paste(mark,(72,45+(85-mark.height)//2),mark)
