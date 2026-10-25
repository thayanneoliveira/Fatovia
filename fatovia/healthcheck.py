"""Gera uma imagem estritamente técnica para verificar URLs públicas."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def generate(path="docs/media/healthcheck.jpg"):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGB", (1080, 1350), "#F5F1E7")
    draw = ImageDraw.Draw(canvas)
    font_file = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_file, 58)
    small = ImageFont.truetype(font_file, 33)
    draw.rectangle((0, 0, 1080, 28), fill="#102F28")
    draw.text((92, 140), "FATOVIA", font=font, fill="#102F28")
    draw.text((92, 320), "TESTE DE HOSPEDAGEM", font=small, fill="#102F28")
    draw.text((92, 440), "NAO PUBLICAR", font=font, fill="#A13D2A")
    draw.text((92, 555), "Nenhuma informacao politica", font=small, fill="#102F28")
    draw.text((92, 620), "Esta e uma imagem tecnica.", font=small, fill="#102F28")
    draw.text((92, 1190), "Arquivo JPEG 1080 x 1350", font=small, fill="#465D50")
    canvas.save(target, format="JPEG", quality=90, optimize=True, subsampling=0)
    return str(target)


if __name__ == "__main__":
    print(generate())
