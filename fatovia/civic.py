"""Bounded public-data narratives. No free-form claims, arbitrary URLs or paid APIs."""
from datetime import datetime,timedelta
from decimal import Decimal
import hashlib,json,re,csv,io,unicodedata
from .discovery import get

SPECS={
 "selic":{"title":"Selic e crédito","source":"Banco Central","url":"https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados","public":"https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom","topic":"economia","max_days":7},
 "ipca":{"title":"Inflação e poder de compra","source":"IBGE","url":"https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/last%2012","public":"https://sidra.ibge.gov.br/tabela/1737","topic":"economia","max_days":75},
 "energia":{"title":"Bandeiras tarifárias e conta de luz","source":"ANEEL","url":"https://dadosabertos.aneel.gov.br/dataset/7f43a020-6dc5-44b8-80b4-d97eaa94436c/resource/0591b8f6-fe54-437b-b72b-1aa2efd46e42/download/bandeira-tarifaria-acionamento.csv","public":"https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias","topic":"infraestrutura","max_days":31},
 "emprego":{"title":"Desocupação e mercado de trabalho","source":"IBGE","url":"https://apisidra.ibge.gov.br/values/t/4099/n1/all/v/4099/p/last%208","public":"https://sidra.ibge.gov.br/tabela/4099","topic":"economia","max_days":270},
}
def is_civic(item):
    return str(item.get("id","")).startswith("civic:")

def key(item):
    return str(item["id"]).split(":",1)[1]

def digest(x):
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def br(v):
    return format(Decimal(v),"f").replace(".",",")

def make(k,observation):
    s=SPECS[k]
    period=observation["period"]
    value=observation["value"] if k=="energia" else format(Decimal(observation["value"]).normalize(),"f")
    if k=="selic":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",period) or not 0<=Decimal(value)<=100:raise ValueError("invalid_selic")
        date=period
        # Daily observations of an unchanged target must not produce daily duplicates.
        identity={"key":k,"value":value}
        summary=f"Meta Selic definida pelo Copom: {br(value)}% ao ano. Não representa a taxa de um empréstimo individual."
    elif k=="ipca":
        if not re.fullmatch(r"\d{4}-\d{2}",period) or not -100<Decimal(value)<100:raise ValueError("invalid_ipca")
        date=period+"-01"; identity={"key":k,"period":period,"value":value}
        summary=f"IPCA nacional, variação mensal de {br(value)}% no período {period}. Não representa a inflação individual de cada família."
    elif k=="energia":
        if not re.fullmatch(r"\d{4}-\d{2}",period) or value not in ("verde","amarela","vermelha patamar 1","vermelha patamar 2"):raise ValueError("invalid_flag")
        date=period+"-01"; identity={"key":k,"period":period,"value":value}
        summary=f"ANEEL: bandeira tarifária {value} registrada para {period}. A bandeira indica condições de custo da geração de eletricidade."
    else:
        if not re.fullmatch(r"\d{4}-Q[1-4]",period) or not 0<=Decimal(value)<=100:raise ValueError("invalid_employment")
        date=period[:4]+"-"+str(int(period[-1])*3).zfill(2)+"-01"; identity={"key":k,"period":period,"value":value}
        summary=f"PNAD Contínua: taxa de desocupação nacional de {br(value)}% no período {period}, para pessoas de 14 anos ou mais na força de trabalho."
    return {"id":"civic:"+k,"version":digest(identity)[:14],"title":s["title"],"summary":summary,"summary_hash":digest(identity)[:14],"stage":"Observação oficial","stage_date":date,"source_url":s["url"],"public_url":s["public"],"source_name":s["source"],"topics":[s["topic"]],"observation":{"period":period,"value":value},"status":"discovered"}

def valid(item):
    try:
        k=key(item)
        if k not in SPECS:return False
        expected=make(k,item["observation"])
        return all(item.get(x)==expected[x] for x in expected if x!="status")
    except (ValueError,KeyError,TypeError,ArithmeticError,AttributeError):return False

def fresh(item,now):
    try:
        return valid(item) and 0<=(now.date()-datetime.fromisoformat(item["stage_date"]).date()).days<=SPECS[key(item)]["max_days"] and (key(item)!="energia" or item["observation"]["period"]==now.strftime("%Y-%m"))
    except (ValueError,KeyError,TypeError):return False

def flags(raw,now):
    text=raw.decode("utf-8-sig",errors="strict")
    reader=csv.DictReader(io.StringIO(text),delimiter=";")
    if not {"DatCompetencia","NomBandeiraAcionada"}.issubset(reader.fieldnames or []):raise ValueError("flag_schema")
    current=now.strftime("%Y-%m")
    found=[]
    for row in reader:
        date=str(row["DatCompetencia"]).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",date):
            period=datetime.fromisoformat(date).strftime("%Y-%m")
        elif re.fullmatch(r"\d{4}-\d{2}",date):period=date
        else:raise ValueError("flag_date")
        if period!=current:continue
        value=" ".join(unicodedata.normalize("NFKD",row["NomBandeiraAcionada"].casefold()).encode("ascii","ignore").decode().replace("-"," ").split())
        aliases={"bandeira verde":"verde","bandeira amarela":"amarela","bandeira vermelha patamar 1":"vermelha patamar 1","bandeira vermelha patamar 2":"vermelha patamar 2","vermelha 1":"vermelha patamar 1","vermelha 2":"vermelha patamar 2"}
        found.append(aliases.get(value,value))
    if len(found)!=1:raise ValueError("flag_current_missing_or_duplicate")
    return [{"period":current,"value":found[0]}]

def observations(k,now,getter=get):
    s=SPECS[k]
    if k=="selic":
        from .research import parse
        raw=getter(s["url"],{"formato":"json","dataInicial":(now-timedelta(days=29)).strftime("%d/%m/%Y"),"dataFinal":now.strftime("%d/%m/%Y")})
        obs,status=parse(raw,"432",now)
    elif k=="energia":
        obs,status=flags(getter(s["url"]),now),"ok"
    else:
        from .ibge import parse,SPECS as SIDRA
        raw=getter(s["url"])
        result=parse(raw,SIDRA["ipca_monthly" if k=="ipca" else "unemployment_quarterly"],now)
        obs,status=result["observations"],result["status"]
        if result["missing_periods"] and (not obs or max(result["missing_periods"])>obs[-1]["period"]):raise ValueError("latest_missing")
    if status!="ok" or not obs:raise ValueError("source_stale")
    return obs

def fetch(k,now,getter=get):
    obs=observations(k,now,getter)
    item=make(k,obs[-1])
    if not fresh(item,now):raise ValueError("source_stale")
    return item

def collect(now,getter=get):
    rows=[]; errors={}
    for k in SPECS:
        try:rows.append(fetch(k,now,getter))
        except Exception as exc:errors[k]=type(exc).__name__
    return rows,errors

def verify(item,now,getter=get):
    if not fresh(item,now):return False
    try:
        k=key(item)
        obs=observations(k,now,getter)
        current=make(k,obs[-1])
        if k=="selic":
            return current["version"]==item["version"] and any(make(k,o)["observation"]==item["observation"] for o in obs)
        return all(current.get(x)==item.get(x) for x in current if x!="status")
    except Exception:return False

def cards(item):
    if not valid(item):raise ValueError("invalid_civic_claim")
    k=key(item); p=item["observation"]["period"]; v=item["observation"]["value"] if k=="energia" else br(item["observation"]["value"])
    if k=="selic":
        rows=[
          ("Por que o empréstimo não custa a mesma coisa que a Selic?","A taxa de referência da economia e o preço do crédito ao consumidor não são a mesma coisa."),
          ("A taxa de referência",f"Em {p}, a série oficial do Banco Central registrou meta Selic de {v}% ao ano."),
          ("Onde entra a política pública?","A meta Selic é definida pelo Copom e integra a condução da política monetária."),
          ("E a prestação?","A taxa de um contrato também depende de fatores como risco, prazo e custos. A Selic não é a taxa cobrada de cada cliente."),
          ("Compare antes de decidir","Acompanhe a taxa de referência e compare o custo efetivo total das ofertas de crédito."),
          ("O que este dado não prova","A meta anual não informa o rendimento diário nem a taxa de um empréstimo específico."),
        ]
    elif k=="ipca":
        rows=[
          ("Seu mercado subiu mais que a inflação?","O índice nacional e a cesta de compras de uma família não são a mesma coisa."),
          ("O dado oficial",f"Em {p}, o IPCA nacional registrou variação mensal de {v}%, segundo o IBGE."),
          ("Onde entra a política pública?","O IPCA é a referência do regime de metas de inflação. A política monetária busca a estabilidade de preços."),
          ("E o seu bolso?","Cada família compra uma combinação diferente de produtos e serviços. A variação de suas despesas pode ser diferente do índice."),
          ("Como comparar","Compare períodos iguais. A taxa mensal não é o acumulado em doze meses."),
          ("O que este dado não prova","O IPCA sozinho não identifica a causa de cada aumento de preço nem o resultado de uma medida pública."),
        ]
    elif k=="energia":
        rows=[
          ("O que a cor da bandeira diz sobre a sua conta de luz?","A bandeira tarifária é um sinal das condições de custo da geração de energia."),
          ("A bandeira do mês",f"Para {p}, a base oficial da ANEEL registra a bandeira {v}."),
          ("Onde entra a regulação?","A ANEEL aciona mensalmente a bandeira conforme critérios regulatórios e condições de geração."),
          ("Verde não significa conta grátis","A bandeira verde não acrescenta cobrança de bandeira. Amarela e vermelha indicam adicionais tarifários."),
          ("O que conferir na fatura","Observe o período de faturamento, o consumo e o adicional da bandeira, quando houver."),
          ("O que este dado não prova","A cor da bandeira não determina sozinha o valor total de uma conta de luz."),
        ]
    else:
        rows=[
          ("Por que a taxa de desemprego não conta toda a história?","Um indicador do mercado de trabalho precisa ser lido junto com sua definição."),
          ("O dado oficial",f"No período {p}, a PNAD Contínua registrou taxa de desocupação de {v}% no Brasil."),
          ("Onde entra a política pública?","O acompanhamento do mercado de trabalho oferece informação para planejar e avaliar políticas de emprego e renda."),
          ("Quem entra nessa conta?","A taxa considera pessoas desocupadas em relação à força de trabalho, na população de 14 anos ou mais."),
          ("O que acompanhar","Observe também ocupação, participação e rendimento. Um indicador isolado não descreve todo o mercado."),
          ("O que este dado não prova","A taxa trimestral não é mensal, não é uma contagem de pessoas e não prova o efeito de uma política específica."),
        ]
    rows.append(("Confira a fonte",item["source_name"]+" | "+item["title"]+"\n\nSérie oficial na legenda."))
    return [(h,b,"Fonte: "+item["source_name"]) for h,b in rows]

def closing(item):
    return {"energia":"Compartilhe com quem abre a conta de luz como se fosse um filme de suspense.","selic":"Compartilhe com quem sempre confunde a Selic com os juros do cartão.","ipca":"Compartilhe com quem compara o índice de inflação com o carrinho do mercado.","emprego":"Compartilhe com quem quer entender os números do mercado de trabalho."}[key(item)]

def caption(item):
    c=cards(item)
    return c[0][0]+"\n\n"+c[1][1]+"\n\n"+c[2][1]+"\n\n"+c[5][1]+"\n\nFonte oficial: "+item["public_url"]+"\nAPI: "+item["source_url"]+"\nID editorial: "+item["id"]+"/"+item["version"]+"/premium-editorial-v1\n#FatoVia #Economia #Cidadania #PoliticasPublicas\n\nSalve este post para consultar os indicadores. "+closing(item)

def matrix(item):
    return {"policy":"civic-series-v1","document_id":item["id"],"version":item["version"],"source_url":item["source_url"],"entries":[{"location":f"card_{i:02}","text":h+" | "+b,"type":"official_observation" if i==2 else "controlled_explanation","evidence":{"period":item["observation"]["period"],"value":item["observation"]["value"],"url":item["source_url"]} if i==2 else {"url":item["public_url"]},"limitation":"No causal attribution; fixed explanatory template."} for i,(h,b,_) in enumerate(cards(item),1)]+[{"location":"caption","text":caption(item),"type":"reconstructed_caption"}],"unverified_dimensions":["causality","individual_impact"]}
