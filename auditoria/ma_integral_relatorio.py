"""Gera Markdown reproduzível a partir do JSON da execução integral MA."""
from __future__ import annotations
import json
from pathlib import Path


def markdown(report):
    coverage=report.get("cobertura",{})
    tests=report.get("verificacoes",{})
    issues=report.get("ocorrencias",{})
    states={
        "INCONCLUSIVO":"INCONCLUSIVO: não houve cobertura integral",
        "ALERTAS_TECNICOS_REQUEREM_ANALISE":"ALERTAS TÉCNICOS: verificar documentação e exceções",
        "CONFERENCIA_INTERNA_CONSISTENTE_COM_RESSALVAS":"CONFERÊNCIA INTERNA CONSISTENTE, COM RESSALVAS",
    }
    lines=["# FATOVIA AUDITA | Maranhão | 2º turno 2026",
           "",f"**Status: {states.get(report['status'], report['status'])}.**","",
           f"Gerado em UTC: {report['gerado_utc']}.","",
           "## Cobertura",
           "",
           "| Indicador | Quantidade |","|---|---:|",
           f"| Seções no BU oficial | {coverage.get('secoes_bu','n/d')} |",
           f"| Seções na correspondência efetivada (CEFT) | {coverage.get('secoes_ceft','n/d')} |",
           f"| Seções no pacote bruto | {coverage.get('secoes_pacote_bruto','n/d')} |",
           f"| Seções efetivamente processadas | {coverage.get('secoes_processadas','n/d')} |",
           f"| Seções com alertas | {coverage.get('secoes_alertadas','n/d')} |",
           "",
           "### Conferências por seção",
           "",
           "| Teste | Resultado |","|---|---:|",
           f"| RDV Presidente = BU | {tests.get('rdv_bu_ok',0)} |",
           f"| Identidade da seção no RDV correta | {tests.get('rdv_secao_ok',0)} |",
           f"| Quantidade de eventos de voto no log = comparecimento | {tests.get('log_bu_ok',0)} |",
           f"| Log não aplicável (origem especial) | {tests.get('log_nao_aplicavel',0)} |",
           f"| Identidade de urna RDV = CEFT | {tests.get('rdv_urna_ceft_ok',0)} |",
           f"| Código de carga RDV = CEFT | {tests.get('rdv_carga_ceft_ok',0)} |",
           f"| Identidade de urna CEFT presente no log | {tests.get('urna_ceft_log_ok',0)} |",
           f"| SHA-512 de arquivos presentes = hashes declarados no VSC | {tests.get('arquivos_sha512_conferidos',0)} |",
           f"| SHA-512 divergentes | {tests.get('arquivos_sha512_divergentes',0)} |",
           f"| Urna efetivada diferente da esperada | {tests.get('urna_esperada_diferente_efetivada',0)} |",
           "",
           "## Alertas e ocorrências",
           ""]
    if not issues:
        lines.append("Nenhum alerta técnico classificado pelo motor nesta execução.")
    else:
        lines.extend(["| Tipo | Ocorrências | Exemplo (município/zona/seção) |",
                      "|---|---:|---|"])
        for typ, n in sorted(issues.items(),key=lambda pair:(-pair[1],pair[0])):
            examples=report.get("ocorrencias_amostra",{}).get(typ,[])
            example=", ".join("/".join(map(str,key)) for key in examples[:3])
            lines.append(f"| {typ} | {n} | {example} |")
    missing=coverage.get("chaves_sem_correspondencia",{})
    if missing and any(missing.values()):
        lines.extend(["","**Cobertura incompleta:**", "", *[
            f"- {name}: {n}" for name,n in missing.items() if n
        ]])
    lines.extend([
        "", "## Ressalvas fundamentais", "",
        "- Os hashes SHA-512 foram conferidos contra valores declarados nas estruturas VSC. "
        "A assinatura criptográfica, certificados e cadeia de confiança ainda NÃO foram validados.",
        "- A concordância entre RDV, BU, CEFT e logs verifica consistência interna do material "
        "publicado pelo TSE, não a intenção original do eleitor nem a autenticidade de BUs coletados externamente.",
        "- Eventos de log e alteração de números de urnas exigem interpretação contextual e documental.",
        "- Logs de apuração especial podem não ser comparáveis à sequência ordinária de eventos.",
        "- Se o relatório contiver alertas técnicos, eles não constituem prova automática de fraude.",
        "- O ZIP de arquivos transmitidos não é garantia de cobertura de transmissões rejeitadas ou pendentes.",
        "",
        "## Fontes e reprodução",
        "",
        "- https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna",
        "- https://dadosabertos.tse.jus.br/dataset/resultados-2026-correspondencias-esperadas-e-efetivadas-2-turno",
        "- https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao",
        "- Código de execução: python -m auditoria.ma_integral",
        "- Evidência detalhada: docs/auditoria/ma-integral-2026-2t.json",
        "",
        "**Nenhum status significa certificação irrestrita de ausência de fraude.**",
    ])
    return "\n".join(lines)+"\n"

if __name__=="__main__":
    source=Path("work/ma-integral/ma-2026-2t-integral.json")
    destination=Path("work/ma-integral/ma-2026-2t-integral.md")
    report=json.loads(source.read_text(encoding="utf-8"))
    destination.write_text(markdown(report),encoding="utf-8")
    print(f"Gerado: {destination}",flush=True)
