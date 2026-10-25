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
    picture = Image.new("RGB", (1080, 1350), CREAM)
    draw = ImageDraw.Draw(picture)
    draw.rectangle((0, 0, 1080, 18), fill=GREEN)
    draw.text((82, 82), "FATO", fill=GREEN, font=getfont(58, True))
    draw.text((273, 82), "VIA", fill="#4B8063", font=getfont(58, True))
    draw.line((82, 180, 998, 180), fill="#9EAE9B", width=3)
    draw.text((82, 225), f"EDITORIAL / {number:02}/07", fill="#587262", font=getfont(25, True))
    title_lines = wrapped(draw, headline, getfont(58, True), 900)
    if len(title_lines) > 5:
        raise ValueError("Título ultrapassa limite")
    y = 326
    for line in title_lines:
        draw.text((82, y), line, fill=GREEN, font=getfont(58, True))
        y += 81
    y += 65
    body_font = getfont(33 if len(body) > 420 else 39)
    step = 52 if len(body) > 420 else 61
    for line in wrapped(draw, body, body_font, 910):
        if y + step > 1130:
            raise ValueError(f"Card {number} excedeu limite de texto")
        draw.text((82, y), line, fill="#213B31", font=body_font)
        y += step
    draw.line((82, 1195, 998, 1195), fill="#B1BDAF", width=2)
    for index, line in enumerate(wrapped(draw, hint, getfont(22), 900)):
        if index >= 2:
            raise ValueError("Nota de rodapé ultrapassa limite")
        draw.text((82, 1220 + index * 28), line, fill="#607268", font=getfont(22))
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
