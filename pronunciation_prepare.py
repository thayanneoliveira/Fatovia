"""Apply only explicitly approved lexical pronunciation rules; never alter display text."""
import re
import json
from pathlib import Path

def prepare(rows, dictionary):
    rules=[x for x in dictionary["entries"] if x["status"]=="approved_in_episode"]
    result=[]
    for row in rows:
        p=dict(row)
        spoken=p.get("spoken",p["caption"])
        for rule in rules:
            spoken=re.sub(r"(?<!\w)"+re.escape(rule["written"])+r"(?!\w)",lambda m:rule["spoken"],spoken)
        p["spoken"]=spoken
        result.append(p)
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    rules=json.loads(Path(__file__).with_name("pronunciation_dictionary.json").read_text(encoding="utf-8"))
    rows=json.loads(a.input.read_text(encoding="utf-8"))
    a.output.write_text(json.dumps(prepare(rows,rules),ensure_ascii=False,indent=2),encoding="utf-8")
