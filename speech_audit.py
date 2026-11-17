"""Independent ASR-derived speech audit and candidate subtitle timing. Never publishes."""
import argparse, hashlib, json, math, re, time, unicodedata
from pathlib import Path

# Narrow equivalent written forms; never equate different numeric values.
NUM={"0":"zero","1":"um","2":"dois","3":"três","4":"quatro","5":"cinco","6":"seis","7":"sete","8":"oito","9":"nove","10":"dez","100":"cem"}
def tokens(text):
    text=unicodedata.normalize("NFC",text).casefold()
    # Keep numeric punctuation and signs distinct, so 1,5 is not 15.
    raw=re.findall(r"[+-]?\d+(?:[.,]\d+)*%?|[^\W\d_]+|[%€$]",text,re.UNICODE)
    return [NUM.get(t,t) for t in raw]
def edits(a,b):
    n,m=len(a),len(b)
    d=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1):d[i][0]=i
    for j in range(m+1):d[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1):
            d[i][j]=min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]!=b[j-1]))
    ops=[];i=n;j=m
    while i or j:
        if i and j and a[i-1]==b[j-1] and d[i][j]==d[i-1][j-1]:
            ops.append(("match",i-1,j-1));i-=1;j-=1
        elif i and j and d[i][j]==d[i-1][j-1]+1:
            ops.append(("substitution",i-1,j-1));i-=1;j-=1
        elif i and d[i][j]==d[i-1][j]+1:
            ops.append(("deletion",i-1,None));i-=1
        else:
            ops.append(("insertion",None,j-1));j-=1
    return list(reversed(ops))

def evaluate(rows,words,duration,min_prob=.6):
    expected=[];groups=[]
    for i,row in enumerate(rows):
        ts=tokens(row.get("spoken",row["caption"]))
        if not ts: raise ValueError("empty expected phrase")
        groups.append(list(range(len(expected),len(expected)+len(ts))))
        expected.extend({"token":t,"phrase":i+1} for t in ts)
    recognized=[]
    for w in words:
        ts=tokens(w["text"])
        for token in ts:
            recognized.append({**w,"token":token,"shared_span":len(ts)>1})
    a=[w["token"] for w in expected];b=[w["token"] for w in recognized]
    ops=edits(a,b);counts=dict.fromkeys(("match","substitution","deletion","insertion"),0)
    matches={};differences=[]
    for typ,i,j in ops:
        counts[typ]+=1
        if typ=="match":
            matches[i]=recognized[j]
        else:
            differences.append({"type":typ,"expected_index":i,"expected":expected[i] if i is not None else None,"recognized":recognized[j] if j is not None else None})
    issues=[];aligned=[];previous_end=0.
    for i,e in enumerate(expected):
        w=matches.get(i)
        if w is None: continue
        s,t,p=w["start"],w["end"],w["probability"]
        valid=all(math.isfinite(v) for v in (s,t,p)) and 0<=s<t<=duration+.05 and 0<=p<=1
        if not valid or w["shared_span"] or s<previous_end-.02 or p<min_prob:
            issues.append({"index":i,"word":e["token"],"reason":"unreliable_or_overlapping_asr_timing","recognized":w})
            continue
        previous_end=t
        aligned.append({**e,"expected_index":i,"start":s,"end":min(t,duration),"probability":p,"timing":"ASR estimate"})
    lookup={w["expected_index"]:w for w in aligned}
    cues=[]
    for i,g in enumerate(groups):
        if all(k in lookup for k in g):
            cues.append({"phrase":i+1,"caption":rows[i]["caption"],"start":lookup[g[0]]["start"],"end":lookup[g[-1]]["end"]})
    errors=sum(counts[k] for k in ("substitution","deletion","insertion"))
    status="candidate_for_listening_review" if not errors and not issues and len(cues)==len(rows) else "needs_review"
    return {"status":status,"publish_allowed":False,"counts":counts,"reference_words":len(a),"recognized_words":len(b),"wer":errors/len(a),"duration":duration,"matched_word_timing_count":len(aligned),"phrase_cue_count":len(cues),"phrase_count":len(rows),"differences":differences,"timing_issues":issues,"aligned_words":aligned,"candidate_cues":cues,"limitations":"ASR differences are suspicions, not proof of wrong pronunciation. Exact transcription is not proof of correct prosody or speech. All timing is estimated. No automatic publication."}

def stamp(sec):
    ms=round(sec*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def main():
    p=argparse.ArgumentParser();p.add_argument("--audio",type=Path,required=True);p.add_argument("--script",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--out",type=Path,required=True);p.add_argument("--model",default="small")
    a=p.parse_args()
    from faster_whisper import WhisperModel
    rows=json.loads(a.script.read_text(encoding="utf-8"))
    manifest=json.loads(a.manifest.read_text(encoding="utf-8"))
    digest=hashlib.sha256(a.audio.read_bytes()).hexdigest()
    if digest!=manifest["sha256_mp3"]:raise ValueError("audio hash mismatch")
    if manifest["phrases"]!=len(rows) or " ".join(x.get("spoken",x["caption"]) for x in rows)!=" ".join(x["spoken"] for x in manifest["blocks"]):raise ValueError("script/manifest mismatch")
    start=time.monotonic()
    model=WhisperModel(a.model,device="cpu",compute_type="int8",cpu_threads=4)
    segments,info=model.transcribe(str(a.audio),language="pt",task="transcribe",beam_size=5,temperature=0.,condition_on_previous_text=False,word_timestamps=True,vad_filter=False)
    words=[];transcript=[]
    for seg in segments:
        transcript.append(seg.text.strip())
        for w in seg.words or []:words.append({"text":w.word,"start":float(w.start),"end":float(w.end),"probability":float(w.probability)})
    if abs(info.duration-manifest["duration"])>.15:raise ValueError("audio duration mismatch")
    report=evaluate(rows,words,manifest["duration"])
    report.update(audio_sha256=digest,model=a.model,transcript=" ".join(transcript),runtime_seconds=round(time.monotonic()-start,2),asr_words=words)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"speech_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (a.out/"transcript.txt").write_text(report["transcript"],encoding="utf-8")
    # Candidate only: incomplete subtitles cannot be confused with production output.
    (a.out/"candidate_partial.srt").write_text("\n\n".join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["caption"]}' for i,c in enumerate(report["candidate_cues"]))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k in ("status","counts","wer","reference_words","recognized_words","matched_word_timing_count","phrase_cue_count","phrase_count","runtime_seconds")},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
