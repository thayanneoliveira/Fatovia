#!/usr/bin/env python3
"""Cruzamento independente: correspondencias 24/25 x efetivadas 26 x BU 26 (MG, PE)."""
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import re
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

OUT=Path('auditoria-nacional-resultados')
OUT.mkdir(exist_ok=True)
BASE='https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/'
RESULT={'run_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'geographic_scope':{'ufs':27,'abroad':'ZZ'},'states':{},'caveat':'Cruzamentos indicam diferenças a validar, não comprovação de fraude.'}
HASH=re.compile(r'\b[a-fA-F0-9]{128}\b')
HEAD={'User-Agent':'FatoVia-auditoria-civica/2026'}
REG={'24':('correspesp','CESP_2t_{uf}_241020261231.zip'),
'25':('correspesp','CESP_2t_{uf}_251020261345.zip'),
'efetivada':('correspefet','CEFT_2t_{uf}_261020261201.zip'),
'bu':('buweb','bweb_2t_{uf}_261020260742.zip')}
def norm(x): return re.sub(r'[^A-Z0-9]','',str(x).upper())
def column(cols,variants):
    idx={norm(x):x for x in cols}
    for a in variants:
        if norm(a) in idx:return idx[norm(a)]
    return None
def dl(url,path,limit=1024**3):
    if path.exists() and path.stat().st_size:return None
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=120) as r,path.open('wb') as w:
        size=0
        for chunk in iter(lambda:r.read(1024*1024),b''):
            size+=len(chunk)
            if size>limit:raise ValueError('download exceeds per-file cap')
            w.write(chunk)
    return size
def sha512(path):
    h=hashlib.sha512()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def official_hash(path):
    b=path.read_bytes()
    if zipfile.is_zipfile(io.BytesIO(b)):
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            names=[x for x in z.namelist() if not x.endswith('/')]
            if len(names)!=1:return None
            b=z.read(names[0])
    matches=set(x.lower() for x in HASH.findall(b.decode('utf8',errors='replace')))
    return next(iter(matches)) if len(matches)==1 else None
def analyse_csv(path):
    o={'members':[],'rows':0,'sections':0,'conflicts':0,'index':{}}
    sectionmap={}
    with zipfile.ZipFile(path) as z:
        for member in z.infolist():
            if member.is_dir() or not member.filename.lower().endswith(('.csv','.txt')):continue
            with z.open(member) as fp:
                reader=io.TextIOWrapper(fp,encoding='latin-1',errors='replace',newline='')
                header=reader.readline()
                if not header:continue
                sep=max((';',',','\t'),key=lambda s:header.count(s))
                rows=csv.DictReader(iter([header]+[]) if False else reader,fieldnames=next(csv.reader([header],delimiter=sep)),delimiter=sep)
                cols=rows.fieldnames
                mun=column(cols,['CD_MUNICIPIO','CD_MUN','NR_MUNICIPIO','COD_MUNICIPIO'])
                zone=column(cols,['NR_ZONA','ZONA','NUM_ZONA'])
                sec=column(cols,['NR_SECAO','SECAO','NUM_SECAO'])
                urn=column(cols,['NR_URNA','NR_SERIE_URNA','NR_URNA_EFETIVADA','NR_URNA_ESPERADA','NR_EQUIPAMENTO','NUM_SERIE_URNA'])
                o['members'].append({'file':member.filename,'delimiter':sep,'columns':cols,'columns_municipio':mun,'zona':zone,'secao':sec,'urna':urn})
                if not (mun and zone and sec):continue
                for row in rows:
                    o['rows']+=1
                    def clean(s):
                        s=str(s or '').strip()
                        return str(int(s)) if s.isdecimal() else s
                    key=(clean(row.get(mun,'')),clean(row.get(zone,'')),clean(row.get(sec,'')))
                    if not all(key):continue
                    u=clean(row.get(urn,'')) if urn else ''
                    if key not in sectionmap:sectionmap[key]=u
                    elif sectionmap[key] and u and sectionmap[key]!=u:o['conflicts']+=1
    o['sections']=len(sectionmap);o['index']=sectionmap
    return o
def compare_sections(a,b):
    ia=a.get('index',{});ib=b.get('index',{})
    only_a=set(ia)-set(ib); only_b=set(ib)-set(ia)
    diffs=[(k,ia[k],ib[k]) for k in set(ia)&set(ib) if ia[k] and ib[k] and ia[k]!=ib[k]]
    return {'sections_previous':len(ia),'sections_next':len(ib),
            'only_previous':len(only_a),'only_next':len(only_b),
            'urn_id_different':len(diffs),
            'examples_different':[{'mun':k[0],'zona':k[1],'secao':k[2],'urn_old':x,'urn_new':y} for k,x,y in sorted(diffs)[:40]],
            'examples_only_previous':[list(x) for x in sorted(only_a)[:20]],
            'examples_only_next':[list(x) for x in sorted(only_b)[:20]]}
for uf in ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO","ZZ"]:
    entries={};indexes={}
    for name,(folder,pattern) in REG.items():
        filename=pattern.format(uf=uf);url=BASE+folder+'/'+filename
        p=OUT/filename;hr=OUT/(filename+'.sha512')
        record={'url':url}
        try:
            dl(url,p);record['bytes']=p.stat().st_size
            record['sha512_local']=sha512(p)
            try:
                dl(url+'.sha512',hr)
                expected=official_hash(hr);record['hash_expected']=expected
                record['sha512_status']='MATCH' if expected==record['sha512_local'] else ('MISMATCH' if expected else 'UNKNOWN')
            except Exception as e:record['sha512_status']='REFERENCE_ERROR';record['hash_error']=str(e)
            parsed=analyse_csv(p);indexes[name]=parsed
            record.update({k:v for k,v in parsed.items() if k!='index'})
        except Exception as e:record['error']=f'{type(e).__name__}: {e}'
        entries[name]=record
        print(uf,name,record.get('bytes'),record.get('sha512_status'),record.get('sections'),record.get('error','OK'),flush=True)
    pairs={}
    for lhs,rhs in [('24','25'),('25','efetivada'),('efetivada','bu')]:
        pairs[lhs+'_vs_'+rhs]=compare_sections(indexes[lhs],indexes[rhs]) if lhs in indexes and rhs in indexes else {'status':'blocked'}
    RESULT['states'][uf]={'sources':entries,'comparisons':pairs}
OUT.joinpath('RESULTADO_NACIONAL_CRUZAMENTO.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2),encoding='utf8')
md=['# Cruzamento das correspondências e boletins (MG e PE)','Arquivos oficiais, SHA-512 e índice por município, zona e seção.','']
for uf,u in RESULT['states'].items():
    md+=['## '+uf]
    for k,s in u['sources'].items():
        md.append(f"- {k}: {s.get('sections','não processado')} seções; hash {s.get('sha512_status','sem referência')}; linhas {s.get('rows','n/d')}")
        for m in s.get('members',[])[:3]:md.append(f"  - Colunas-chave: {m['columns_municipio']}, {m['zona']}, {m['secao']}, urna={m['urna']}")
        if s.get('error'):md.append('  - ERRO: '+s['error'])
    for k,v in u['comparisons'].items():
        md.append(f"- {k}: {v.get('urn_id_different','n/d')} identificadores de urna diferentes; {v.get('only_previous','n/d')} seções só na base anterior; {v.get('only_next','n/d')} só na posterior.")
    md.append('')
md.append('Diferenças entre a urna prevista e a efetivada podem resultar de contingências; identificação de causa exige documentação específica.')
OUT.joinpath('RESULTADO_NACIONAL_CRUZAMENTO.md').write_text('\n'.join(md),encoding='utf8')
print('\n'.join(md),flush=True)
