"""Generate 3 source-checked FatoVia carousels as public JPEGs."""
import json
from pathlib import Path
from fatovia.render import card

ROOT=Path("docs/media/insights-2026-11-02")
INPUT=Path("data/insights_20261102.json")

def main():
    posts=json.loads(INPUT.read_text(encoding="utf-8"))
    if len(posts)!=3:
        raise RuntimeError("Expected precisely 3 verified editorial items")
    for post in posts:
        if len(post["cards"])!=7:
            raise RuntimeError("Each Instagram carousel needs 7 cards")
        dest=ROOT/post["slug"]
        dest.mkdir(parents=True,exist_ok=True)
        for i,(headline,body,hint) in enumerate(post["cards"],1):
            card(dest/f"{i:02}.jpg",i,headline,body,hint)
            print(f"READY {post['slug']} {i:02}/07",flush=True)
    print("SUCCESS: generated 21 public JPEG cards")

if __name__=="__main__":
    main()
