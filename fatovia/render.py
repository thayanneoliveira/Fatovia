"""Carrosséis editoriais JPEG. Apenas resume documentos fornecidos, sem inferências."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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
    natural = str(headline).lower().capitalize()
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

    draw.line((72, 805, 212, 805), fill=sage, width=6)
    body_size, lines = 38, []
    while body_size >= 24:
        body_font = getfont(body_size)
        lines = wrapped(draw, body, body_font, 925)
        gap = max(38, body_size + 17)
        height = sum(20 if not line else gap for line in lines)
        if 847 + height <= 1158:
            break
        body_size -= 2
    if 847 + height > 1158:
        raise ValueError("Texto excedeu o limite editorial")
    y = 847
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

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    picture.save(path, "JPEG", quality=91, optimize=True, subsampling=0)
    return str(path)

def cards_for(item):
    summary = item["summary"].strip()
    if len(summary) > 330:
        cutoff = summary[:330].rfind(" ")
        first = summary[:cutoff] if cutoff > 0 else summary[:330]
        second = summary[len(first):].strip()
    else:
        first, second = summary, ""
    return [
        ("O que chegou à Câmara?", f'{item["title"]}\n\nUma proposição legislativa registrada na fonte oficial.', "Monitoramento documental, não recomendação eleitoral."),
        ("O que diz a ementa?", first, "Trecho da ementa oficial, não a íntegra do projeto."),
        ("E o restante do texto?", second or "A ementa termina no card anterior. Consulte a íntegra no site oficial.", "Não é análise de viabilidade nem resultado comprovado."),
        ("Qual é a tramitação?", f'Registro de {item["stage_date"]}:\n\n{item["stage"][:340]}', "A tramitação pode mudar. Confira na Câmara."),
        ("O que isso NÃO prova?", "A existência de um projeto não comprova aprovação, entrada em vigor, financiamento ou resultados.", "Proposta, lei e implementação são etapas distintas."),
        ("O que acompanhar?", "Qual é o texto final?\n\nQuais órgãos respondem pela execução?\n\nHá custo previsto e indicadores de resultado?", "São perguntas, não afirmações sobre efeitos."),
        ("Veja a fonte original", f'{item["title"]}\n\nCâmara dos Deputados\n\nID: {item["id"].split(":")[1]}\n\nLink completo na legenda.', "FatoVia | Informação antes de opinião."),
    ]


def render(item, root="docs/media"):
    destination = Path(root) / item["id"].replace(":", "-") / item["version"]
    paths = []
    try:
        for number, (headline, body, hint) in enumerate(cards_for(item), 1):
            paths.append(card(destination / f"{number:02}.jpg", number, headline, body, hint))
    except Exception:
        for path in paths:
            Path(path).unlink(missing_ok=True)
        raise
    item["cards"] = paths
    item["caption"] = (
        f'{item["title"]}: o que consta no registro oficial?\n\n'
        f'A ementa e o andamento foram consultados na Câmara em {item["stage_date"]}. '
        'Uma proposta não equivale a uma lei aprovada nem a benefício implementado.\n\n'
        f'Fonte: {item["public_url"]}\n'
        f'API oficial: {item["source_url"]}\n\n'
        f'FatoVia | Conteúdo informativo elaborado automaticamente.\n'
        f'ID editorial: {item["id"]}/{item["version"]}\n'
        '#FatoVia #PoliticasPublicas #CongressoNacional'
    )
    return item
