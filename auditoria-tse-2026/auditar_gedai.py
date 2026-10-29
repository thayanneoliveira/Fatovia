#!/usr/bin/env python3
"""Coleta e compara ZIPs oficiais do GEDAI do segundo turno de 2026.
Executado no GitHub Actions. Nunca interpreta mudança isolada como fraude.
"""
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.request
import zipfile
from collections import Counter

UFs = ('MG','PE')
BASE = 'https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/logsgedai/'
OUT = Path('auditoria-resultados')
OUT.mkdir(exist_ok=True)
DAY_SUFFIX = {'24':'241020261329','25':'251020261327'}
DATES = re.compile(r'\b(?:24|25|26)[/.]10[/.]2026\b|\b2026-10-(?:24|25|26)\b')
SHA512_PATTERN = re.compile(r'\b[A-Fa-f0-9]{128}\b')
TIME_PATTERN = re.compile(r'\b(?:(?:24|25|26)/10/2026|2026-10-(?:24|25|26))\s+[0-2]\d:[0-5]\d(?::[0-5]\d)?')
MAX_BYTES = 4*1024**3
HEADERS = {'User-Agent':'FatoVia-independent-civic-audit/2026 (public electoral open data)'}
report = {'run_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
          'purpose':'Public data cross-check, not an allegation',
          'source_dataset':'https://dadosabertos.tse.jus.br/dataset/resultados-2026-logs-do-sistema-de-preparacao-das-urnas-eletronicas-gedai-2-turno',
          'ufs':{}, 'limits':[
          'Divergence between ZIPs does not demonstrate election fraud.',
          'GEDAI logs concern preparation, not a record of cast votes.',
          'Complete administrative justification requires official documents.',
          'File name timestamp and internal log timestamps are distinct.']}

def download(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return {'status':'cached','bytes':dest.stat().st_size}
    part=dest.with_suffix(dest.suffix+'.part')
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=90) as res, open(part,'wb') as out:
                length=res.headers.get('Content-Length')
                if length and int(length)>MAX_BYTES:raise ValueError('HTTP file exceeds 4 GiB cap')
                count=0
                sha=hashlib.sha512()
                while True:
                    block=res.read(1024*1024)
                    if not block:break
                    count+=len(block)
                    if count>MAX_BYTES:raise ValueError('download exceeds 4 GiB cap')
                    out.write(block);sha.update(block)
            part.replace(dest)
            return {'status':'downloaded','bytes':count,'sha512':sha.hexdigest()}
        except Exception as e:
            last=f'{type(e).__name__}: {e}'
            if part.exists():part.unlink()
            time.sleep(attempt+1)
    return {'status':'error','error':last}

def ref_hash(path):
    try:
        content=path.read_bytes()
        if zipfile.is_zipfile(io.BytesIO(content)):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                fs=[x for x in z.namelist() if not x.endswith('/')]
                if len(fs)!=1: return {'status':'ambiguous_zip_hash','members':fs[:10]}
                content=z.read(fs[0])
        matches=set(x.lower() for x in SHA512_PATTERN.findall(content.decode('utf-8-sig',errors='replace')))
        if len(matches)==1:return {'status':'found','digest':next(iter(matches))}
        return {'status':'ambiguous_or_missing','matches_count':len(matches)}
    except Exception as e:return {'status':'error','error':str(e)}

def sha512(path):
    h=hashlib.sha512()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def inspect_zip(path):
    members={}
    parsed_events=Counter()
    examples=[]
    try:
        with zipfile.ZipFile(path) as z:
            for member in z.infolist():
                if member.is_dir():continue
                h=hashlib.sha256()
                with z.open(member) as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
                members[member.filename]={'bytes':member.file_size,'sha256':h.hexdigest(),
                                          'zip_modified':str(member.date_time)}
                if member.filename.lower().endswith(('.csv','.txt','.log','.xml')):
                    # Bounded scan per member to prevent pathological inputs
                    with z.open(member) as s:
                        count=0
                        for raw in s:
                            count+=1
                            if count>200000:break
                            line=raw.decode('latin-1',errors='replace')
                            m=TIME_PATTERN.search(line)
                            if m:
                                day=re.search(r'(24|25|26)(?:/10/2026|-10-)',m.group())
                                # Use original date string rather than pretending timezone conversion
                                key=m.group().split(' ')[0]
                                parsed_events[key]+=1
                                if len(examples)<25:examples.append({'file':member.filename,'timestamp_text':m.group(),'line_excerpt':line[:240].rstrip()})
        return {'status':'ok','members':members,'event_date_samples':dict(parsed_events),
                'examples':examples,'scan_note':'Only first 200000 lines per readable member scanned for dates.'}
    except Exception as e:return {'status':'error','error':f'{type(e).__name__}: {e}'}

def compare(a,b):
    a=a.get('members',{}); b=b.get('members',{})
    changed=[name for name in a.keys()&b.keys() if a[name]['sha256']!=b[name]['sha256']]
    return {'members_only_24':sorted(a.keys()-b.keys())[:500],
            'members_only_25':sorted(b.keys()-a.keys())[:500],
            'members_changed_count':len(changed),'members_changed_samples':sorted(changed)[:500],
            'members_equal_count':sum(a[n]['sha256']==b[n]['sha256'] for n in a.keys()&b.keys()),
            'member_counts':{'24':len(a),'25':len(b)},
            'interpretation':'Differences require context; not proof of irregularity.'}

for uf in UFs:
    report['ufs'][uf]={'days':{}}
    for day,stamp in DAY_SUFFIX.items():
        name=f'log_gedai_2t_{uf}_{stamp}.zip'
        url=BASE+name
        zipfile_path=OUT/name
        hash_path=OUT/(name+'.sha512')
        print('DOWNLOAD',url,flush=True)
        dl=download(url,zipfile_path)
        hashdl=download(url+'.sha512',hash_path)
        result={'url':url,'download':dl,'hash_download':hashdl}
        if dl['status'] in ('cached','downloaded'):
            result['sha512_local']=sha512(zipfile_path)
            if hashdl['status'] in ('cached','downloaded'):
                expected=ref_hash(hash_path)
                result['reference']=expected
                result['hash_status']='MATCH' if expected.get('digest')==result['sha512_local'] else ('MISMATCH' if expected.get('digest') else 'UNVERIFIED')
            result['internal']=inspect_zip(zipfile_path)
        report['ufs'][uf]['days'][day]=result
    a=report['ufs'][uf]['days']['24'].get('internal',{})
    b=report['ufs'][uf]['days']['25'].get('internal',{})
    report['ufs'][uf]['difference']=compare(a,b) if a.get('status')=='ok' and b.get('status')=='ok' else {'status':'blocked_missing_files'}

OUT.joinpath('RESULTADO_GEDAI.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
lines=['# Auditoria independente de logs GEDAI, segundo turno de 2026',
       'Coleta automatizada de fontes oficiais do TSE, sem suposição sobre fraude.','']
for uf,v in report['ufs'].items():
    lines+=['## '+uf]
    for day,item in v['days'].items():
        s=item['download']
        lines.append(f"- {day}/10/2026: download **{s['status']}**; bytes: {s.get('bytes','n/d')}; SHA-512: {item.get('hash_status','não verificado')}; membros: {len(item.get('internal',{}).get('members',{}))}")
        if s.get('error'):lines.append('  - Erro: '+s['error'])
        if item.get('internal',{}).get('error'):lines.append('  - Erro ZIP: '+item['internal']['error'])
    dif=v['difference']
    if dif.get('status')=='blocked_missing_files':lines.append('- **Comparação impedida:** faltam ZIPs processáveis.')
    else:lines.append(f"- Comparação: {dif['members_changed_count']} membros alterados, {dif['members_equal_count']} iguais, {len(dif['members_only_24'])} exclusivos de 24, {len(dif['members_only_25'])} exclusivos de 25.")
    lines.append('')
lines+=['**Limite:** alterações e diferenças de ZIP não indicam, por si, fraude; o sistema GEDAI registra preparação de urnas.',
        'Detalhes verificáveis por arquivo e hash estão em RESULTADO_GEDAI.json.']
OUT.joinpath('RESULTADO_GEDAI.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines),flush=True)
