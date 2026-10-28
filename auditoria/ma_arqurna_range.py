"""Inventário NÃO INVASIVO de entradas em arquivo ZIP remoto muito grande.

Lê por HTTPS Range apenas blocos necessários para obter diretório do ZIP.
Não analisa votos individuais nem divulga material individualizado.
"""
from __future__ import annotations
from collections import Counter, OrderedDict
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
import io,json,re,zipfile

URL=("https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/arqurnatot/"
     "bu_imgbu_logjez_rdv_vscmr_2026_2t_MA.zip")
MAX_BYTES_TRANSFERRED=192*1024*1024
BLOCK=2*1024*1024
MAX_BLOCKS=40

class RemoteZip(io.RawIOBase):
    def __init__(self,url=URL):
        if urlparse(url).hostname!="cdn.tse.jus.br":
            raise ValueError("Origem não permitida")
        self.url=url
        with urlopen(Request(url,method="HEAD"),timeout=40) as r:
            if r.status!=200 or not r.headers.get("Content-Length"):
                raise ValueError("HEAD sem tamanho declarado")
            self.size=int(r.headers["Content-Length"])
            self.etag=r.headers.get("ETag")
        if self.size<=0:
            raise ValueError("Tamanho inválido")
        self.position=0
        self.cache=OrderedDict()
        self.bytes_fetched=0
        self.http_requests=0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        if whence==0:target=offset
        elif whence==1:target=self.position+offset
        elif whence==2:target=self.size+offset
        else:raise ValueError("whence")
        if target<0:raise ValueError("seek < 0")
        self.position=target
        return target
    def block(self,index):
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        start=index*BLOCK
        end=min(start+BLOCK,self.size)-1
        length=end-start+1
        if self.bytes_fetched+length>MAX_BYTES_TRANSFERRED:
            raise ValueError("Limite de tráfego atingido; pare a execução")
        headers={"Range":f"bytes={start}-{end}","User-Agent":"FatoViaAudita/1.1"}
        if self.etag:
            headers["If-Range"]=self.etag
        with urlopen(Request(self.url,headers=headers),timeout=90) as r:
            if r.status!=206:
                raise ValueError(f"Servidor não respeitou Range: HTTP {r.status}")
            expected=f"bytes {start}-{end}/{self.size}"
            if r.headers.get("Content-Range")!=expected:
                raise ValueError(f"Intervalo inesperado: {r.headers.get('Content-Range')}")
            content=r.read(length+1)
        if len(content)!=length:
            raise ValueError("Resposta incompleta")
        self.bytes_fetched+=len(content)
        self.http_requests+=1
        self.cache[index]=content
        if len(self.cache)>MAX_BLOCKS:self.cache.popitem(last=False)
        return content
    def read(self,n=-1):
        if self.position>=self.size:return b""
        if n<0:n=self.size-self.position
        n=min(n,self.size-self.position)
        pieces=[]
        while n:
            index=self.position//BLOCK
            b=self.block(index)
            offset=self.position%BLOCK
            part=b[offset:offset+n]
            if not part: raise IOError("Bloco remoto incompleto")
            pieces.append(part)
            self.position+=len(part)
            n-=len(part)
        return b"".join(pieces)

def inspect_index(url=URL):
    with RemoteZip(url) as remote:
        with zipfile.ZipFile(remote) as archive:
            entries=archive.infolist()
            types=Counter()
            sample={}
            matching=[]
            total_uncompressed=0
            total_compressed=0
            for e in entries:
                if e.is_dir():continue
                ext=e.filename.rsplit(".",1)[-1].lower() if "." in e.filename else "(sem_extensao)"
                types[ext]+=1
                if ext not in sample:sample[ext]=e.filename[:200]
                total_uncompressed+=e.file_size
                total_compressed+=e.compress_size
                # Somente nome de arquivo; não inferir seção a partir de strings isoladas.
                if any(tok in e.filename for tok in ("_26_88","_1_124","_1_125")):
                    if len(matching)<12:matching.append(e.filename[:240])
            result={
                "gerado_utc":datetime.now(timezone.utc).isoformat(),
                "url":url,"conteudo_remoto_bytes":remote.size,
                "etag":remote.etag,
                "metodo":"HTTP Range / diretório central do ZIP",
                "arquivos_contabilizados":sum(types.values()),
                "tipos":dict(sorted(types.items())),"amostra_por_tipo":sample,
                "comprimidos_total_bytes":total_compressed,
                "descomprimidos_total_bytes":total_uncompressed,
                "nomes_candidatos_amostra":matching,
                "bytes_transferidos":remote.bytes_fetched,
                "requisicoes_range":remote.http_requests,
                "nota":("Listagem das entradas, não verificação de assinaturas, votos "
                        "nem completude dos registros de transmissão.")
            }
    Path("work/aprofundada").mkdir(parents=True,exist_ok=True)
    Path("work/aprofundada/ma_arqurna_index.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return result

if __name__=="__main__":inspect_index()
