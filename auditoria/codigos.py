"""Normalização estrita de códigos de carga das urnas, sem perder zeros."""
from __future__ import annotations


def codigo_carga_padronizado(valor: object) -> str | None:
    """Preserva 24 posições, preenchendo zeros à esquerda em campos decimais.

    Um CSV pode representar o mesmo código com menos dígitos. Valores
    alfanuméricos, vazios, negativos ou com mais de 24 dígitos são rejeitados.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not (1 <= len(texto) <= 24 and texto.isascii() and texto.isdigit()):
        return None
    return texto.zfill(24)


def codigos_carga_conferem(rdv: object, ceft: object) -> bool:
    a = codigo_carga_padronizado(rdv)
    b = codigo_carga_padronizado(ceft)
    return a is not None and b is not None and a == b
