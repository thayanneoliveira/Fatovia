"""Carrosséis editoriais JPEG. Apenas resume documentos fornecidos, sem inferências."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from .didactic import reviewed, REVISION
TEMPLATE_REVISION=REVISION
LEGACY_REVISION="documentary-hook-v3"
GREEN = "#102F28"
CREAM = "#F5F1E7"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def getfont(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else FONT, size)
    except OSError:
        return ImageFont.load_default()


def wrapped(draw, text, font, max_width):
    result = []
    for paragraph in str(text).split("\n"):
        if not paragraph:
            result.append("")
            continue
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                current = trial
            else:
                if current:
                    result.append(current)
                current = word
                if draw.textbbox((0, 0), current, font=font)[2] > max_width:
                    raise ValueError("Uma palavra não cabe no card")
        if current:
            result.append(current)
    return result


def card(path, number, headline, body, hint):
    """Formato FatoVia: fundo verde escuro, títulos serifados e microtipografia editorial."""
    picture = Image.new("RGB", (1080, 1350), "#123E31")
    draw = ImageDraw.Draw(picture)
    cream, sage, muted = "#F5F1E7", "#B5D39F", "#D0DFC6"

    def serif(size):
        for path in (
            "/usr/share/fonts/truetype/ebgaramond/EBGaramond08-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
        return ImageFont.load_default()

    draw.text((72, 56), "FATOVIA", fill=cream, font=getfont(34, True))
    draw.text((808, 69), "ENTENDA / 2026", fill=muted, font=getfont(22))
    draw.line((72, 146, 1008, 146), fill="#9FBF99", width=2)
    draw.text((72, 190), f"FATOVIA / {number:02}/07", fill=muted, font=getfont(25, True))
    natural = str(headline)
    for acronym in ("IA", "PEC", "SUS", "TSE", "PL", "STF"):
        natural = natural.replace(" " + acronym.lower() + " ", " " + acronym + " ")
        natural = natural.replace(" " + acronym.lower() + "?", " " + acronym + "?")
        natural = natural.replace(" " + acronym.lower() + ".", " " + acronym + ".")
    title_size = 91
    while title_size >= 56:
        title_font = serif(title_size)
        title_lines = wrapped(draw, natural, title_font, 926)
        if len(title_lines) <= 5:
            break
        title_size -= 5
    if len(title_lines) > 5:
        raise ValueError("Título excedeu a área editorial")
    y = 272
    for index, line in enumerate(title_lines):
        draw.text((72, y), line, fill=cream if index == 0 else sage, font=title_font)
        y += title_size + 8

    divider_y = max(565, y + 40)
    body_y = divider_y + 42
    draw.line((72, divider_y, 212, divider_y), fill=sage, width=6)
    body_size, lines = 38, []
    while body_size >= 24:
        body_font = getfont(body_size)
        lines = wrapped(draw, body, body_font, 925)
        gap = max(38, body_size + 17)
        height = sum(20 if not line else gap for line in lines)
        if body_y + height <= 1158:
            break
        body_size -= 2
    if body_y + height > 1158:
        raise ValueError("Texto excedeu o limite editorial")
    y = body_y
    for line in lines:
        if line:
            draw.text((72, y), line, fill=cream, font=body_font)
        y += 20 if not line else gap

    cta = "FONTES NA LEGENDA" if number == 7 else "DESLIZE PARA ENTENDER"
    draw.text((72, 1190), cta, fill=sage, font=getfont(26, True))
    draw.line((72, 1270, 1008, 1270), fill="#9FBF99", width=2)
    footer_font = getfont(18)
    footer = wrapped(draw, hint, footer_font, 780)
    draw.text((72, 1284), (footer[0] if footer else "")[:110], fill=muted, font=footer_font)
    draw.text((940, 1284), f"{number:02}/07", fill=cream, font=getfont(18, True))

    if number==7:
        from .brand import approved_logo,carousel_header
        logo=approved_logo()
        if logo is not None:
            carousel_header(picture,logo)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    picture.save(path, "JPEG", quality=91, optimize=True, subsampling=0)
    return str(path)

HOOKS=(
    (("médicos residentes","reajustes periódicos da bolsa"),"O que pode mudar para médicos residentes?"),
    (("responsabilização disciplinar de atletas","violência contra a mulher"),"Atletas e violência contra a mulher: o que propõe o PL?"),
    (("fogos de artifício","estampidos"),"O que o projeto propõe sobre fogos com estampido?"),
    (("serviços médico-veterinários","redução de 60%"),"O que a proposta prevê para tributos de serviços veterinários?"),
    (("devolução geral progressiva","renda domiciliar per capita"),"Como a proposta relaciona devolução de impostos e renda?"),
    (("planos privados de assistência à saúde","núcleo familiar"),"Planos de saúde familiares: o que está em discussão?"),
    (("Imposto Seletivo","financiamento adicional"),"O que o projeto propõe para financiar tratamentos no SUS?"),
    (("lucros e dividendos","Imposto sobre a Renda"),"O que está em discussão sobre lucros e dividendos?"),
)
def editorial_hook(item):
    import re
    summary=item["summary"]
    for terms,title in HOOKS:
        matches=[re.search(re.escape(t),summary,re.I) for t in terms]
        if all(matches):
            return title,[m.group(0) for m in matches]
    return "O que está previsto nesta proposta?",[]

def cards_for(item):
    row=reviewed(item)
    if row:
        labels=("O tema","O que propõe","Como entender","Impacto possível","Perguntas em aberto")
        cards=[(c["headline"],c["body"],labels[i]+" | "+item["title"]) for i,c in enumerate(row["cards"])]
        cards.extend([
            ("Já está valendo?",f'Registro de {item["stage_date"]}: {item["stage"]}. A existência do projeto não comprova vigência.',"Situação documental na data indicada."),
            ("Confira a fonte",f'{item["title"]}\n\nCâmara dos Deputados | ID {item["id"].split(":")[1]}\n\nTexto integral e tramitação no link da legenda.',"FatoVia | Informação antes de opinião.")
        ])
        return cards
    summary = item["summary"].strip()
    if len(summary) > 330:
        cutoff = summary[:330].rfind(" ")
        first = summary[:cutoff] if cutoff > 0 else summary[:330]
        second = summary[len(first):].strip()
    else:
        first, second = summary, ""
    return [
        (editorial_hook(item)[0], f'{item["title"]}\n\nProposta legislativa registrada na Câmara.', "Monitoramento documental, não recomendação eleitoral."),
        ("O que diz a ementa?", first, "Trecho da ementa oficial, não a íntegra do projeto."),
        ("O restante da ementa" if second else "Ementa não é a íntegra", second or "A ementa resume o tema. Para conhecer condições, exceções e detalhes, consulte o texto integral.", "Não é análise de viabilidade nem resultado comprovado."),
        ("Qual é a tramitação?", f'Registro de {item["stage_date"]}:\n\n{item["stage"][:340]}', "A tramitação pode mudar. Confira na Câmara."),
        ("O que isso NÃO prova?", "A existência de um projeto não comprova aprovação, entrada em vigor, financiamento ou resultados.", "Proposta, lei e implementação são etapas distintas."),
        ("O que acompanhar?", "Qual é o texto final?\n\nQuais órgãos respondem pela execução?\n\nHá custo previsto e indicadores de resultado?", "São perguntas, não afirmações sobre efeitos."),
        ("Veja a fonte original", f'{item["title"]}\n\nCâmara dos Deputados\n\nID: {item["id"].split(":")[1]}\n\nLink completo na legenda.', "FatoVia | Informação antes de opinião."),
    ]


def render(item, root="docs/media"):
    row=reviewed(item)
    destination = Path(root) / item["id"].replace(":", "-") / item["version"]
    if row:
        destination=destination/REVISION
    paths = []
    try:
        for number, (headline, body, hint) in enumerate(cards_for(item), 1):
            paths.append(card(destination / f"{number:02}.jpg", number, headline, body, hint))
    except Exception:
        for path in paths:
            Path(path).unlink(missing_ok=True)
        raise
    item["template_revision"] = REVISION if row else LEGACY_REVISION
    from .brand import approved_logo
    if approved_logo() is not None:
        import json
        item["brand_sha256"]=json.loads(Path("data/multiformat_experiment.json").read_text(encoding="utf-8"))["approved_logo"]["sha256"]
    else:
        item.pop("brand_sha256",None)
    item["cards"] = paths
    item["caption"] = (
        f'{editorial_hook(item)[0]}\n\n{item["title"]}\n\n'
        f'A ementa consta na Câmara e o registro de andamento tem data de {item["stage_date"]}. '
        'Uma proposta não equivale a uma lei aprovada nem a benefício implementado.\n\n'
        f'Fonte: {item["public_url"]}\n'
        f'API oficial: {item["source_url"]}\n\n'
        f'FatoVia | Conteúdo informativo elaborado automaticamente.\n'
        f'ID editorial: {item["id"]}/{item["version"]}\n'
        '#FatoVia #PoliticasPublicas #CongressoNacional'
    )
    if row:
        item["caption"] = (row["cards"][0]["headline"]+"\n\n"+row["cards"][1]["body"]+"\n\n"+row["cards"][3]["body"]
            +"\n\n"+f'{item["title"]} | Registro de {item["stage_date"]}. Proposta, não benefício comprovado.'
            +"\n\nFonte oficial: "+item["public_url"]+"\n"
            +f'ID editorial: {item["id"]}/{item["version"]}/{REVISION}\n#FatoVia #PoliticasPublicas')
    return item
