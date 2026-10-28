"""FATOVIA AUDITA: cruzamento presencial de 6 seções MA com arquivos TSE.

Somente APIs e arquivos já publicados, HTTP Range, sem acesso a serviços internos.
NÃO publica sequências individuais do RDV nem eventos nominativos.
As especificações ASN.1 incluídas em auditoria/spec/ são usadas nos termos MIT.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

from .ma_arqurna_range import RemoteZip,URL
from .tse import csv_rows,download_zip,sha512_expected
from .proveniencia_ma import FILES,read_selected_rows

FOCO=((7536,26,88),(9210,1,124),(9210,1,125))
CONTROLES=((7030,52,32),(7048,70,184),(7005,12,21))
ALVOS=tuple(FOCO+CONTROLES)
PATTERN=re.compile(r"^o\d{5}ma(\d{5})(\d{4})(\d{4})-([^/]+)$",re.I)
BU_URL=("https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/"
        "buweb/bweb_2t_MA_261020260742.zip")
SPEC=Path(__file__).parent/"spec"

def file_index(archive):
    """Mapear todas as seções pelos nomes, preservando avisos de formatos novos."""
    sections=defaultdict(dict)
    nonmatched=[]
    collisions=[]
    for e in archive.infolist():
        if e.is_dir():continue
        matched=PATTERN.match(e.filename)
        if not matched:
            if len(nonmatched)<12:nonmatched.append(e.filename)
            continue
        key=tuple(int(matched.group(i)) for i in range(1,4))
        kind=matched.group(4).lower()
        if kind in sections[key]:
            if len(collisions)<20:collisions.append({"secao":key,"tipo":kind})
        sections[key][kind]=e
    kinds=Counter()
    missing=[]
    for key,items in sections.items():
        kinds.update(items.keys())
        if len(items)!=5 and len(missing)<20:
            missing.append({"secao":key,"tipos":sorted(items)})
    return sections,{"secoes_com_arquivos":len(sections),"tipos":dict(kinds),
                    "secoes_com_numero_tipos_distinto_de_5_amostra":missing,
                    "colisoes_amostra":collisions,"fora_do_padrao_amostra":nonmatched}

def sample_bu_counts():
    out=defaultdict(Counter)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"bu.zip"
        digest,bytes_downloaded=download_zip(BU_URL,path)
        for r in csv_rows(path):
            if r.get("NR_TURNO")!="2":
                continue
            if r.get("CD_CARGO_PERGUNTA")!="1":
                continue
            key=(int(r["CD_MUNICIPIO"]),int(r["NR_ZONA"]),int(r["NR_SECAO"]))
            if key in ALVOS:
                out[key][str(int(r["NR_VOTAVEL"]))]+=int(r["QT_VOTOS"])
    return out,{"url":BU_URL,"sha512_calculado":digest,"bytes":bytes_downloaded}

def sample_ceft():
    result={}
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"ceft.zip"
        url=FILES["efetivada_26"]
        expected=sha512_expected(url+".sha512")
        digest,size=download_zip(url,path)
        if digest!=expected:
            raise ValueError("SHA512 CEFT diferente do hash oficial")
        for row in read_selected_rows(path,"ceft_"):
            key=(int(row["CD_MUNICIPIO"]),int(row["NR_ZONA"]),int(row["NR_SECAO"]))
            if key in ALVOS:
                result[key]={k:row.get(k,"") for k in (
                    "NR_URNA_ESPERADA","NR_URNA_EFETIVADA",
                    "CD_CARGA_URNA_ESPERADA","CD_CARGA_URNA_EFETIVADA",
                    "CD_FLASHCARD_URNA_ESPERADA","CD_FLASHCARD_URNA_EFETIVADA",
                    "TP_DIVERGENCIA","DS_ORIGEM_VOTO")}
    return result,{"url":url,"sha512_conferido":True,"bytes":size}

def decode_rdv(data, compiler):
    rdv=compiler.decode("EntidadeResultadoRDV",bytearray(data))
    r=rdv["rdv"]
    ident=r["identificacao"]
    mz=ident["municipioZona"]
    ident_key=(int(mz["municipio"]),int(mz["zona"]),int(ident["secao"]))
    elections=r["eleicoes"]
    if not (isinstance(elections,tuple) and len(elections)==2):
        raise ValueError("RDV eleicoes não é CHOICE")
    origin,elections_list=elections
    counts=Counter()
    registered=0
    president_blocks=0
    choices=[]
    for election in elections_list:
        for cargo in election.get("votosCargos",[]):
            ch=cargo.get("idCargo")
            if not (isinstance(ch,tuple) and ch[1]=="presidente"):
                continue
            president_blocks+=1
            choices.append(int(cargo["quantidadeEscolhas"]))
            for v in cargo["votos"]:
                registered+=1
                typ=v.get("tipoVoto")
                if typ=="nominal":
                    digit=v.get("digitacao")
                    if not digit or not str(digit).isdigit():
                        raise ValueError("Voto nominal com digitação inválida")
                    counts[str(int(digit))]+=1
                elif typ in ("branco","brancoAposSuspensao"):
                    counts["95"]+=1
                elif typ in ("nulo","nuloAposSuspensao","nuloPorRepeticao",
                              "nuloCargoSemCandidato","nuloAposSuspensaoCargoSemCandidato"):
                    counts["96"]+=1
                else:
                    raise ValueError(f"Tipo RDV presidente não suportado: {typ}")
    if not president_blocks:
        raise ValueError("RDV sem cargo Presidente")
    if any(c!=1 for c in choices):
        raise ValueError("RDV presidente com número de escolhas inesperado")
    urna=rdv.get("urna") or {}
    carga=(urna.get("correspondenciaResultado") or {}).get("carga") or {}
    return {"secao_interna":ident_key,"origem":origin,
            "fase":str(r.get("fase")),"pleito":int(r.get("pleito")),
            "votos":dict(counts),"registros_presidente":registered,
            "blocos_presidente":president_blocks,
            "numero_interno_urna":carga.get("numeroInternoUrna"),
            "codigo_carga_urna":carga.get("codigoCarga")}

def asn1_topology(raw):
    """Somente metadados TLV (tag e comprimentos), sem expor certificados."""
    def tlv(at):
        if at+2>len(raw):return None
        tag=raw[at]
        first=raw[at+1]
        if first==128:raise ValueError("BER indefinido: não suportado na inspeção")
        if first<128:n,ln=first,1
        else:
            count=first&127
            if count>4:raise ValueError("Comprimento ASN.1 anormal")
            n=int.from_bytes(raw[at+2:at+2+count],"big")
            ln=1+count
        val=at+1+ln
        return {"tag":hex(tag),"inicio":at,"valor_inicio":val,
                "fim":val+n,"comprimento":n}
    root=tlv(0)
    if not root:return []
    children=[]
    pos=root["valor_inicio"]
    for _ in range(8):
        if pos>=min(root["fim"],len(raw)):break
        part=tlv(pos)
        if not part:break
        children.append(part)
        if part["fim"]<=pos:break
        pos=part["fim"]
    return {"arquivo_bytes":len(raw),"raiz":root,"filhos":children}

def signature_hashes(raw,compiler):
    """Extrai hashes declarados sem alegar validação criptográfica da assinatura."""
    mode="direto"
    try:
        decoded=compiler.decode("EntidadeAssinaturaEcourna",bytearray(raw))
        envelopes=[decoded[k] for k in ("assinaturaSW","assinaturaHW") if k in decoded]
        model=str(decoded.get("modeloEquipamento"))
    except Exception as exc:
        # Formato real 2026 observado: SEQUENCE de dois envelopes ASN.1
        # mais uma pequena SEQUENCE. Fallback estrito, não permissivo.
        topology=asn1_topology(raw)
        chunks=topology["filhos"]
        if len(chunks)!=3 or topology["raiz"]["fim"]!=len(raw) or any(
                x["tag"]!="0x30" for x in chunks):
            raise ValueError(f"VSC com estrutura não reconhecida: {exc}")
        envelopes=[]
        for chunk in chunks[:2]:
            data=raw[chunk["inicio"]:chunk["fim"]]
            envelopes.append(compiler.decode("EntidadeAssinatura",bytearray(data)))
        mode="envelopes_ber_2026"
        model="terceiro_campo_nao_interpretado"
    hashes={}
    for item in envelopes:
        signed=item.get("conteudoAutoAssinado")
        if not signed:continue
        body=compiler.decode("Assinatura",bytearray(signed))
        for file in body.get("arquivosAssinados",[]):
            name=str(file.get("nomeArquivo",""))
            digest=file.get("assinatura",{}).get("hash")
            if name and digest:hashes.setdefault(name,set()).add(digest.hex())
    if not hashes:
        raise ValueError("Nenhum hash de arquivo encontrado no VSC")
    return hashes,{"modo_decodificacao":mode,"modelo":model,
                   "envelopes_decodificados":len(envelopes),
                   "assinaturas_digitalmente_verificadas":False}

def compare_hashes(files,hashed):
    result={}
    for name,digests in hashed.items():
        if not name or "/" in name or "\\" in name or ".." in name:
            result[name]="NOME_INVALIDO"
            continue
        # Casar nome completo terminando em "-bu.dat" com chave "bu.dat",
        # sem confundir com "imgbu.dat".
        matches=[k for k in files if name==k or name.endswith("-"+k)]
        if len(matches)!=1:
            result[name]="SEM_ARQUIVO_OU_AMBIGUO"
        elif len(digests)!=1:
            result[name]="HASHES_DECLARADOS_DIVERGENTES"
        elif hashlib.sha512(files[matches[0]]).hexdigest()==next(iter(digests)):
            result[name]="HASH_OK"
        else:
            result[name]="HASH_DIVERGENTE"
    return result

def log_summary(blob):
    """Apura somente totais de eventos, sem expor linha do eleitor, relógio ou identificador."""
    texts=[]
    def collect(raw,level=0):
        if level>2:raise ValueError("Log aninhado além do limite")
        with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
            names=zipped.namelist()
            for name in names:
                if name.endswith("/"):continue
                info=zipped.getinfo(name)
                if info.file_size>15*1024*1024:
                    raise ValueError("Log excessivamente grande")
                data=zipped.read(name)
                if name.lower().endswith(".jez"):
                    collect(data,level+1)
                elif name.lower().endswith("logd.dat"):
                    texts.append(data.decode("latin-1",errors="strict"))
    collect(blob)
    if not texts:raise ValueError("Nenhum logd.dat em .jez")
    # União multiconjunto: uma linha repetida em logs copiados é contada no máximo
    # com a maior multiplicidade observada numa das cópias.
    union=Counter()
    for t in texts:
        local=Counter(t.splitlines())
        for line,n in local.items():
            union[line]=max(union[line],n)
    total_votes=0
    urnas_com_evento_voto=set()
    dates=Counter()
    opening=0
    closing=0
    errors=Counter()
    for line,n in union.items():
        fields=line.split("\t")
        if len(fields)<5:continue
        when,level,serial,app,msg=fields[:5]
        day=when[:10]
        if app=="VOTA" and "O voto do eleitor foi computado" in msg:
            dates[day]+=n
            if day=="25/10/2026":
                total_votes+=n
                if serial.isdigit():urnas_com_evento_voto.add(int(serial))
        if "Urna pronta para receber votos" in msg:opening+=n
        if "Inicio do Encerramento" in msg or "Início do Encerramento" in msg:closing+=n
        if any(x in msg.casefold() for x in ("erro","falha","reinici")):
            errors[app]+=n
    return {"logs_internos":len(texts),"total_eventos_voto_25_10":total_votes,
            "urnas_com_eventos_voto_25_10":sorted(urnas_com_evento_voto),
            "eventos_voto_por_data":dict(dates),
            "marcadores_urna_pronta":opening,"marcadores_inicio_encerramento":closing,
            "mensagens_tecnicas_por_aplicativo":dict(errors),
            "metodo":"contagem de eventos 'O voto do eleitor foi computado' após união de cópias de log"}

def run():
    import asn1tools
    rdvc=asn1tools.compile_files(str(SPEC/"rdv.asn1"),codec="ber")
    sigc=asn1tools.compile_files(str(SPEC/"assinatura.asn1"),codec="ber")
    expected,buinfo=sample_bu_counts()
    ceft,ceftinfo=sample_ceft()
    out={"gerado_utc":datetime.now(timezone.utc).isoformat(),"escopo":"MA, 2º turno 2026",
         "metodo":"Conferência seletiva e inventário integral de nomes em ZIP bruto",
         "fonte_bruta":URL,"bu_csv":buinfo,"ceft_csv":ceftinfo,"secoes":{},
         "limitacoes":["Verificação dos hashes listados no .vsc NÃO equivale à validação "
                       "criptográfica da assinatura, cadeia de certificados ou chave da urna.",
                       "Comparação de conteúdo RDV/BU depende de artefatos produzidos pela urna.",
                       "Ausência de um evento no log pode ter causas operacionais; não implica fraude." ]}
    with RemoteZip() as remote:
        with zipfile.ZipFile(remote) as archive:
            sections,inventory=file_index(archive)
            out["inventario"]=inventory
            out["alvos"]=len(ALVOS)
            for key in ALVOS:
                tag=f"{key[0]}/{key[1]}/{key[2]}"
                rec={"secao":list(key),"grupo":"foco" if key in FOCO else "controle",
                     "arquivos":{},"resultado":"INCONCLUSIVO"}
                try:
                    entries=sections.get(key)
                    if not entries:raise ValueError("Seção não encontrada no arquivo bruto")
                    for kind,e in entries.items():
                        rec["arquivos"][kind]={"bytes":e.file_size,"comprimido_bytes":e.compress_size}
                    def select(suffix):
                        matches=[(name,e) for name,e in entries.items() if name.endswith(suffix)]
                        if len(matches)!=1:raise ValueError(f"Esperado {suffix} único; presentes: {list(entries)}")
                        return matches[0]
                    rawfiles={kind:archive.read(info) for kind,info in entries.items()}
                    signed_name,signed_blob=next(((k,v) for k,v in rawfiles.items() if k.endswith("vota.vsc")), (None,None))
                    if not signed_blob:raise ValueError("Assinatura vota.vsc ausente")
                    try:
                        hashes,sigmeta=signature_hashes(signed_blob,sigc)
                        rec["assinatura"]=sigmeta
                        rec["assinatura"]["hashes_listados"]=len(hashes)
                        rec["assinatura"]["comparacao_sha512"]=compare_hashes(rawfiles,hashes)
                    except Exception as exc:
                        rec["assinatura"]={"status":"NAO_DECODIFICADA",
                                          "erro":f"{type(exc).__name__}: {exc}",
                                          "assinaturas_digitalmente_verificadas":False,
                                          "comparacao_sha512":{},
                                          "topologia_asn1":asn1_topology(signed_blob)}
                    rdvname,rdvraw=select("rdv.dat")
                    rdv=decode_rdv(rawfiles[rdvname],rdvc)
                    if rdv["secao_interna"]!=key:raise ValueError("ID seção RDV difere da seção no caminho")
                    bu=expected.get(key)
                    if bu is None:raise ValueError("Seção não consta no CSV BU de referência")
                    # Zero ausente e campo com valor zero são equivalentes.
                    # Evitar falso positivo em seção sem votos brancos/nulos.
                    counts={str(k):int(n) for k,n in rdv["votos"].items() if int(n)>0}
                    buout={str(v):int(n) for v,n in bu.items() if int(n)>0}
                    rec["rdv_presidente"]={
                        "fase":rdv["fase"],"quantidade_registros":rdv["registros_presidente"],
                        "contagens":dict(counts),
                        "bu_publicado":buout,
                        "igual_ao_bu":dict(counts)==buout}
                    logname,lograw=select("log.jez")
                    logs=log_summary(rawfiles[logname])
                    logs["comparecimento_bu"]=sum(bu.values())
                    logs["eventos_igual_comparecimento"]=logs["total_eventos_voto_25_10"]==sum(bu.values())
                    rec["logs"]=logs
                    ceft_row=ceft.get(key)
                    if ceft_row is None:raise ValueError("CEFT não contém a seção")
                    serial_ef=ceft_row.get("NR_URNA_EFETIVADA")
                    internal=rdv.get("numero_interno_urna")
                    serial_in_log=logs.get("urnas_com_eventos_voto_25_10") or []
                    rec["correspondencia_equipamento"]={
                        "urna_esperada":ceft_row.get("NR_URNA_ESPERADA"),
                        "urna_efetivada":serial_ef,
                        "urna_reportada_no_rdv":internal,
                        "codigo_carga_efetivada":ceft_row.get("CD_CARGA_URNA_EFETIVADA"),
                        "codigo_carga_no_rdv":rdv.get("codigo_carga_urna"),
                        "codigo_divergencia":ceft_row.get("TP_DIVERGENCIA"),
                        "identificacao_rdv_confere_com_ceft":(
                            internal is not None and serial_ef is not None
                            and int(internal)==int(serial_ef)),
                        "urna_efetivada_presente_nos_logs_de_voto":(
                            serial_ef is not None and int(serial_ef) in serial_in_log)}
                    statuses=rec["assinatura"]["comparacao_sha512"]
                    hashes_ok=(bool(statuses) and all(v=="HASH_OK" for v in statuses.values()))
                    if rdv["fase"]!="oficial" or not rec["rdv_presidente"]["igual_ao_bu"]:
                        rec["resultado"]="DIVERGENCIA_REQUER_INVESTIGACAO"
                    elif not hashes_ok or not logs["eventos_igual_comparecimento"]:
                        rec["resultado"]="RESSALVA_TECNICA"
                    else:
                        rec["resultado"]="CONSISTENCIA_OBSERVADA"
                except Exception as exc:
                    rec["erro"]=str(exc)
                out["secoes"][tag]=rec
            out["bytes_transferidos_range"]=remote.bytes_fetched
            out["requisicoes_range"]=remote.http_requests
    out["resumo"]=dict(Counter(x["resultado"] for x in out["secoes"].values()))
    Path("work/aprofundada").mkdir(parents=True,exist_ok=True)
    path=Path("work/aprofundada/ma_amostra_profunda.json")
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
    print(json.dumps({"resumo":out["resumo"],
                      "inventario":out["inventario"],
                      "secoes":out["secoes"],
                      "bytes_transferidos_range":out["bytes_transferidos_range"]},
                     ensure_ascii=False,indent=2,default=str))
    if any(x=="INCONCLUSIVO" for x in out["resumo"]):
        raise SystemExit(1)

if __name__=="__main__":run()
