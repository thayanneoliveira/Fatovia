# FATOVIA AUDITA | Maranhão | 2º turno 2026

**Status: ALERTAS TÉCNICOS: verificar documentação e exceções.**

Gerado em UTC: 2026-10-28T14:52:37.678829+00:00.

## Cobertura

| Indicador | Quantidade |
|---|---:|
| Seções no BU oficial | 18093 |
| Seções na correspondência efetivada (CEFT) | 18093 |
| Seções no pacote bruto | 18093 |
| Seções efetivamente processadas | 18093 |
| Seções com alertas | 1 |

### Conferências por seção

| Teste | Resultado |
|---|---:|
| RDV Presidente = BU | 18093 |
| Identidade da seção no RDV correta | 18093 |
| Quantidade de eventos de voto no log = comparecimento | 18091 |
| Log não aplicável (origem especial) | 1 |
| Identidade de urna RDV = CEFT | 18093 |
| Código de carga RDV = CEFT | 18093 |
| Identidade de urna CEFT presente no log | 18093 |
| SHA-512 de arquivos presentes = hashes declarados no VSC | 72372 |
| SHA-512 divergentes | 0 |
| Urna efetivada diferente da esperada | 147 |

## Alertas e ocorrências

| Tipo | Ocorrências | Exemplo (município/zona/seção) |
|---|---:|---|
| LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO | 1 | 8893/47/609 |

## Ressalvas fundamentais

- Os hashes SHA-512 foram conferidos contra valores declarados nas estruturas VSC. A assinatura criptográfica, certificados e cadeia de confiança ainda NÃO foram validados.
- A concordância entre RDV, BU, CEFT e logs verifica consistência interna do material publicado pelo TSE, não a intenção original do eleitor nem a autenticidade de BUs coletados externamente.
- Eventos de log e alteração de números de urnas exigem interpretação contextual e documental.
- Logs de apuração especial podem não ser comparáveis à sequência ordinária de eventos.
- Se o relatório contiver alertas técnicos, eles não constituem prova automática de fraude.
- O ZIP de arquivos transmitidos não é garantia de cobertura de transmissões rejeitadas ou pendentes.

## Fontes e reprodução

- https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna
- https://dadosabertos.tse.jus.br/dataset/resultados-2026-correspondencias-esperadas-e-efetivadas-2-turno
- https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao
- Código de execução: python -m auditoria.ma_integral
- Evidência detalhada: docs/auditoria/ma-integral-2026-2t.json

**Nenhum status significa certificação irrestrita de ausência de fraude.**
