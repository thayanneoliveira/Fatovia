"""Conservative lexical overlap, not semantic equivalence."""
import re
import unicodedata
STOP=set("a o as os e de da do das dos em no na nos nas para por com que um uma sobre dispõe institui altera dispõe dispõe estabelece outras providências".split())


def terms(value):
    text=unicodedata.normalize("NFKD",str(value).casefold())
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    return {x for x in re.findall(r"[a-z0-9]+",text) if len(x)>=3 and x not in STOP}


def overlap(a,b):
    left,right=terms(a.get("summary","")),terms(b.get("summary",""))
    if min(len(left),len(right))<8:
        return 0.0
    return len(left & right)/len(left | right)


def duplicate(a,b):
    if a.get("id")==b.get("id") and a.get("version")==b.get("version"):
        return True
    h=a.get("summary_hash")
    return bool(h and h==b.get("summary_hash")) or overlap(a,b)>=0.82
