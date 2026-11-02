"""FatoVia: 3 social-discussion posts verified on 2026-11-02.

This routine only renders. It NEVER publishes automatically.
"""
import json
from pathlib import Path
from PIL import Image
from fatovia.render import card

SOURCE = Path("data/editorial_social_2026_11_02.json")
OUTPUT = Path("docs/media/radar-social-2026-11-02")

def main():
    editorial = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = editorial["posts"]
    assert len(items) == 3
    for entry in items:
        assert len(entry["cards"]) == 7
        assert 150 <= len(entry["caption"]) <= 2200
        assert len(entry["sources"]) >= 2
        target=OUTPUT/entry["slug"]
        for number,(title,body,note) in enumerate(entry["cards"],start=1):
            path=target/f"{number:02d}.jpg"
            card(path,number,title,body,note)
            with Image.open(path) as img:
                assert img.format=="JPEG" and img.size==(1080,1350)
                rgb=img.convert("RGB").getpixel((15,450))
                assert rgb[0]<55 and 45<rgb[1]<90 and rgb[2]<100, (path,rgb)
                assert path.stat().st_size<8_000_000
            print(f"RENDERED {entry['slug']} {number:02d}/07",flush=True)
    assert len(list(OUTPUT.rglob("*.jpg")))==21
    print("DONE 21 on-brand 4:5 JPEG assets")

if __name__=="__main__":
    main()
