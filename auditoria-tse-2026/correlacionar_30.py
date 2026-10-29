#!/usr/bin/env python3
"""Estudo documental da coincidencia por zona e do conteudo temporal de 30 mudancas previstas.
Nao interpreta ocorrencia de string como confirmacao de substituicao de urna.
"""
import hashlib, io, json, re, subprocess, tempfile, zipfile
from pathlib import Path
from collections import Counter
OUT=Path('auditoria-resultados')
c=json.loads((OUT/'RESULTADO_CRUZAMENTO.json').read_text())
g=json.loads((OUT/'RESULTADO_GEDAI.json').read_text())
dest={'scope':'30 mudancas de correspondencia esperada 24->25 MG PE','states':{},'disclaimer':'Correspondencia por zona e presenca de ID em log sao correlacoes, nao provas de causalidade ou fraude.'}
def logs_for(data,path):
    with tempfile.TemporaryDirectory() as td:
        d=Path(td); p=d/'log.jez';p.write_bytes(data)
        q=subprocess.run(['7z','x','-y',f'-o{d/"open"}',str(p)],capture_output=True,text=True,timeout=90)
        if q.returncode!=0:return [],'extract_error:'+q.stderr[-200:]
        text=[]
        for f in (d/'open').rglob('*'):
            if f.is_file() and f.suffix.lower() in ('.txt','.log'):
                raw=f.read_bytes();t=raw.decode('utf8-sig',errors='replace')
                if t.count('\ufffd')>50:t=raw.decode('latin1')
                text.extend(t.splitlines())
        return text,None
for uf in ('MG','PE'):
    files=g['ufs'][uf]['difference']['members_changed_samples']
    changes=c['states'][uf]['comparisons']['24_vs_25']['examples_different']
    workstations={}
    for f in files:
        match=re.search(r'Z'+uf+r'(\d{3})',f,re.I)
        if match:workstations.setdefault(str(int(match.group(1))),[]).append(f)
    cases=[]
    with zipfile.ZipFile(OUT/f'log_gedai_2t_{uf}_241020261329.zip') as before, zipfile.ZipFile(OUT/f'log_gedai_2t_{uf}_251020261327.zip') as after:
        for change in changes:
            zone=change['zona'];newid=change['urn_new'].zfill(8);oldid=change['urn_old'].zfill(8)
            hits=[]
            for file in workstations.get(zone,[]):
                old,err1=logs_for(before.read(file),file)
                new,err2=logs_for(after.read(file),file)
                from collections import Counter as C
                added=list((C(new)-C(old)).elements())
                # Literal ID match in GEDAI events; only identifiers, not arbitrary substrings
                pattern=re.compile(r'(?<!\d)0*'+re.escape(str(int(newid)))+r'(?!\d)')
                pattern_old=re.compile(r'(?<!\d)0*'+re.escape(str(int(oldid)))+r'(?!\d)')
                new_hits=[x[:270] for x in added if pattern.search(x)]
                old_hits=[x[:270] for x in old if pattern_old.search(x)]
                if new_hits or old_hits:
                    hits.append({'station':file,'new_id_in_added_lines':len(new_hits),'old_id_in_before':len(old_hits),'new_examples':new_hits[:4],'old_examples':old_hits[:2]})
            cases.append({**change,'workstations_in_zone':len(workstations.get(zone,[])),'event_matches':hits,
                          'new_id_added_lines_match':sum(x['new_id_in_added_lines'] for x in hits)})
    dest['states'][uf]={'changed_planned':len(cases),'cases':cases,
      'new_id_in_added_lines_cases':sum(x['new_id_added_lines_match']>0 for x in cases),
      'has_changed_station_in_zone_cases':sum(x['workstations_in_zone']>0 for x in cases)}
OUT.joinpath('RESULTADO_CORRELACOES.json').write_text(json.dumps(dest,ensure_ascii=False,indent=2),encoding='utf8')
md=['# Correlacoes exploratorias: 30 mudancas de correspondencia esperada','Nenhuma coincidencia documental deve ser interpretada automaticamente como justificativa administrativa.','']
for uf,v in dest['states'].items():
    md+=['## '+uf,
      f"- Casos: {v['changed_planned']}; com estacao GEDAI alterada na mesma zona: {v['has_changed_station_in_zone_cases']}; novo ID encontrado em linhas acrescidas: {v['new_id_in_added_lines_cases']}.",
      '### Casos e excertos']
    for d in v['cases']:
        text=' | '.join(y['new_examples'][0] for y in d['event_matches'] if y['new_examples'])
        md.append(f"- Municipio {d['mun']} zona {d['zona']} secao {d['secao']}: prevista {d['urn_old']} -> {d['urn_new']}; ocorrencias novas com ID: {d['new_id_added_lines_match']}; excerto: {text[:400]}")
    md.append('')
OUT.joinpath('RESULTADO_CORRELACOES.md').write_text('\n'.join(md),encoding='utf8')
print('\n'.join(md),flush=True)
