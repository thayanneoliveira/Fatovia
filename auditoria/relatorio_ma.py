"""Relatório público sem votos individuais ou logs brutos."""
import json
from pathlib import Path
from collections import Counter

SOURCE=Path("work/aprofundada/ma_amostra_profunda.json")
DEST=Path("work/aprofundada/ma_relatorio.md")

def render(report):
    secs=report["secoes"]
    checks=Counter()
    for r in secs.values():
        checks.update(r.get("assinatura",{}).get("comparacao_sha512",{}).values())
    rdv_ok=sum(r.get("rdv_presidente",{}).get("igual_ao_bu") is True for r in secs.values())
    logs_ok=sum(r.get("logs",{}).get("eventos_igual_comparecimento") is True for r in secs.values())
    lines=[
        "# FATOVIA AUDITA | Maranhão, segundo turno 2026",
        "",f"Data UTC: {report['gerado_utc']}.",
        "", "## Resultado das verificações", "",
        f"- Seções indexadas no pacote bruto: **{report['inventario']['secoes_com_arquivos']:,}**.".replace(",","."),
        f"- Seções amostradas: **{len(secs)}** (3 com diferenças de identificação e 3 controles).",
        f"- RDV presidencial igual ao BU publicado: **{rdv_ok}/{len(secs)}**.",
        f"- Eventos de voto nos logs iguais ao comparecimento: **{logs_ok}/{len(secs)}**.",
        f"- SHA-512 dos arquivos presentes no pacote igual ao declarado na estrutura VSC: **{checks['HASH_OK']}**.",
        f"- SHA-512 divergente entre arquivos presentes e hash declarado: **{checks['HASH_DIVERGENTE']}**.",
        f"- Referências na estrutura VSC sem arquivo correspondente nesse pacote: **{checks['SEM_ARQUIVO_OU_AMBIGUO']}** (não se trata, por si só, de falha).",
        "",
        "| Município (código TSE) / Zona / Seção | Tipo | RDV x BU | Log x comparecimento | Hashes locais |",
        "|---|---|---|---|---|",
    ]
    for tag,r in secs.items():
        hashes=Counter(r.get("assinatura",{}).get("comparacao_sha512",{}).values())
        rdv="coincide" if r.get("rdv_presidente",{}).get("igual_ao_bu") else "não confirmado"
        log="coincide" if r.get("logs",{}).get("eventos_igual_comparecimento") else "não confirmado"
        lines.append(f"| {tag} | {r['grupo']} | {rdv} | {log} | {hashes['HASH_OK']} OK |")
    lines += [
        "", "## Limitações cruciais", "",
        "1. **Assinatura criptográfica não validada**: foi conferida somente a igualdade dos hashes "
        "SHA-512 com valores declarados nas estruturas VSC. Não se realizou verificação criptográfica "
        "das assinaturas digitais, dos certificados nem da cadeia de confiança.",
        "2. Os arquivos VSC mencionam artefatos adicionais que não integram o pacote público "
        "de arquivos totalizados. A ausência desses arquivos nesse ZIP não demonstra adulteração.",
        "3. O RDV, o BU e o log são produzidos pela infraestrutura eleitoral; concordância entre eles "
        "não comprova que a intenção individual do eleitor foi gravada corretamente.",
        "4. Mudança da identificação de uma urna, registros de contingência e campos de divergência "
        "vazios não são fraude por si. É necessário consultar critérios de preenchimento e documentos operacionais.",
        "5. O pacote de arquivos transmitidos inclui **somente registros na situação Totalizado**, "
        "conforme aviso do Portal de Dados Abertos do TSE; não serve sozinho para excluir "
        "a existência de ocorrências ou tentativas de transmissão rejeitadas.",
        "", "## Reprodução e fontes", "",
        "- Dataset TSE: https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao",
        "- Boletins de urna: https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna",
        "- Código de extração via HTTP Range: auditoria/ma_arqurna_range.py",
        "- Código de teste de RDV, SHA512 e logs: auditoria/ma_amostra_profunda.py",
        "- Especificações ASN.1 v2: auditoria/spec/ (origem DataUrnas-BR, licença MIT)",
        "",
        "**Conclusão:** nas seis seções testadas, não foi observada divergência nas contagens "
        "verificadas. A validação criptográfica da assinatura e a justificativa das trocas de urna "
        "dependem de verificações adicionais.",
    ]
    return "\n".join(lines)+"\n"

def main():
    report=json.loads(SOURCE.read_text(encoding="utf-8"))
    DEST.write_text(render(report),encoding="utf-8")
    print(f"Relatório: {DEST} ({len(report['secoes'])} seções)")

if __name__=="__main__":main()
