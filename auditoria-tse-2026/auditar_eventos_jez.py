#!/usr/bin/env python3
"""Read changed TSE GEDAI .jez archives as nested 7z; classify factual log deltas."""
import collections
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

OUT=Path('auditoria-resultados')
R=json.loads((OUT/'RESULTADO_GEDAI.json').read_text(encoding='utf8'))
DATE_RE=re.compile(r'(?<!\d)(?:\d{2}/10/2026|2026-10-\d{2})\s+\d{2}:\d{2}:\d{2}')
WORDS=re.compile(r'(?:alerta|erro|falha|substitui|troca|inconsist|corrompid|conting.ncia|verifica|assinatura|autoriz|prepar|m.dia)',re.I)
results={'run_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'GEDAI official ZIPs, verified by SHA-512 in RESULTADO_GEDAI.json','ufs':{},'parsing_limits':[]}

def extract_tree(data,outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'outer.jez').write_bytes(data)
    q=[(outdir/'outer.jez',0)]
    found=[]
    seen=set()
    while q:
        item,depth=q.pop(0)
        if depth>3:continue
        checksum=hashlib.sha256(item.read_bytes()).hexdigest()
        if checksum in seen:continue
        seen.add(checksum)
        target=outdir/f'level_{depth}_{len(seen)}'
        target.mkdir(exist_ok=True)
        p=subprocess.run(['7z','x','-y',f'-o{target}',str(item)],capture_output=True,text=True,timeout=120)
        if p.returncode!=0:
            found.append({'type':'archive_error','error':p.stderr[-300:],'file':item.name})
            continue
        for f in target.rglob('*'):
            if not f.is_file():continue
            if f.suffix.lower() in ('.log','.txt'):
                if f.stat().st_size>50*1024*1024:
                    found.append({'type':'text_too_big','file':f.name,'bytes':f.stat().st_size});continue
                # Decode losslessly enough for line comparison, no timestamp synthesis
                t=f.read_bytes().decode('utf-8-sig',errors='replace')
                if t.count('\ufffd')>50:t=f.read_bytes().decode('latin-1')
                found.append({'type':'text','name':f.name,'lines':t.splitlines()})
            elif f.suffix.lower() in ('.jez','.7z','.zip') and depth<3 and f.stat().st_size<100*1024*1024:
                q.append((f,depth+1))
    return found

def summarize(olds,news):
    oldtexts=[x for x in olds if x.get('type')=='text'];newtexts=[x for x in news if x.get('type')=='text']
    def merge(data): return [line for f in data for line in f['lines']]
    a=merge(oldtexts);b=merge(newtexts)
    ca=collections.Counter(a);cb=collections.Counter(b)
    added=list((cb-ca).elements());removed=list((ca-cb).elements())
    adddates=collections.Counter()
    remdates=collections.Counter()
    for line in added:
        match=DATE_RE.search(line)
        if match:adddates[match.group().split(' ')[0]]+=1
    for line in removed:
        match=DATE_RE.search(line)
        if match:remdates[match.group().split(' ')[0]]+=1
    candidates=[x[:400] for x in added if WORDS.search(x)]
    return {'status':'parsed' if oldtexts and newtexts else 'unparsed',
      'old_log_line_count':len(a),'new_log_line_count':len(b),
      'added_lines_count':len(added),'removed_lines_count':len(removed),
      'append_only_text':bool(len(oldtexts)==len(newtexts)==1 and len(b)>=len(a) and b[:len(a)]==a),
      'added_by_literal_date':dict(adddates),'removed_by_literal_date':dict(remdates),
      'example_new_lines':added[:10],'example_interest_lines':candidates[:20],
      'archive_errors_24':[x for x in olds if x.get('type')!='text'][:5],
      'archive_errors_25':[x for x in news if x.get('type')!='text'][:5]}

for uf,u in R['ufs'].items():
    changed=u['difference'].get('members_changed_samples',[])
    rows=[]
    counts=collections.Counter()
    dated=collections.Counter()
    for i,name in enumerate(changed):
        zip24=OUT/f'log_gedai_2t_{uf}_241020261329.zip'
        zip25=OUT/f'log_gedai_2t_{uf}_251020261327.zip'
        with zipfile.ZipFile(zip24) as z:old=z.read(name)
        with zipfile.ZipFile(zip25) as z:new=z.read(name)
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            a=extract_tree(old,td/'old')
            b=extract_tree(new,td/'new')
            res=summarize(a,b)
        res['file']=name
        rows.append(res)
        counts[res['status']]+=1
        counts['added_lines']+=res['added_lines_count']
        counts['removed_lines']+=res['removed_lines_count']
        if res['append_only_text']:counts['append_only_files']+=1
        for k,v in res['added_by_literal_date'].items():dated[k]+=v
        print(uf,i+1,'/',len(changed),res['status'],res['added_lines_count'],res['removed_lines_count'],name,flush=True)
    results['ufs'][uf]={'changed_jez':len(changed),'statistics':dict(counts),
                        'new_lines_by_original_timestamp_date':dict(dated),'files':rows}
OUT.joinpath('RESULTADO_EVENTOS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Análise de conteúdo dos GEDAI .jez de 24 e 25/10/2026',
       'A comparação SHA-256 identificou mudanças em .jez. Esta etapa abriu os arquivos internos 7z e comparou linhas de texto, sem interpretar diferenças como fraude.','']
for uf,u in results['ufs'].items():
    s=u['statistics']
    lines+=['## '+uf, f"- .jez alterados: {u['changed_jez']}; interpretados em texto: {s.get('parsed',0)}; sem parser: {s.get('unparsed',0)}.",
             f"- Linhas adicionadas: {s.get('added_lines',0)}; removidas: {s.get('removed_lines',0)}; arquivos append-only: {s.get('append_only_files',0)}.",
             f"- Datas textuais de linhas acrescentadas: {json.dumps(u['new_lines_by_original_timestamp_date'],ensure_ascii=False)}.",
             '- Atenção: toda diferença é um indício para esclarecimento, não prova de irregularidade.','']
OUT.joinpath('RESULTADO_EVENTOS.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines),flush=True)
