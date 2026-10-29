# FATOVIA AUDITA | Gedai: comparação de referências em 24 e 25/10/2026

**Escopo:** 36 arquivos de log Gedai oficiais (18 UFs, dois conjuntos por UF), verificados por SHA-512 do TSE, com pesquisa das urnas previstas e efetivadas em CEFT.

## Resultado verificável

- 4.730 números físicos distintos de urnas pesquisados nos logs de preparação.
- 12 números aparecem nos registros extraídos do pacote de 25/10 sem aparecer, pelo mesmo método, no pacote de 24/10: BA (4), MG (4), PE (1), PR (2) e SP (1).
- Os registros internos de parte dessas referências são datados de setembro. A presença no pacote de 25/10 **não prova preparação, troca ou fraude no dia da eleição**.

| UF | Município | Zona/seção | Equipamento | Tipo CEFT | Data encontrada no log Gedai | Encerramento BWeb |
|---|---|---|---|---|---|---|
| BA | Salvador | 19/71 | 2327816 | Efetivada | 22/09/2026 | 19:03:41 |
| BA | Salvador | 19/71 | 2352441 | Prevista | 22/09/2026 | 19:03:41 |
| BA | Salvador | 19/450 | 2387642 | Efetivada | 22/09/2026 | 19:00:25 |
| BA | Salvador | 19/450 | 2429338 | Prevista | 22/09/2026 | 19:00:25 |
| MG | Lambari | 159/71 | 2007867 | Efetivada | 24/10/2026 | 17:01:12 |
| MG | Montes Claros | 184/163 | 2011733 | Efetivada | 24/10/2026 | 17:00:35 |
| MG | Matias Cardoso | 63/181 | 2080079 | Prevista | 24/10/2026 | 17:02:03 |
| MG | Jaíba | 63/140 | 2096376 | Prevista | 24/10/2026 | 17:00:48 |
| PE | Macaparana | 90/24 | 2184400 | Prevista | 24/10/2026 | 17:22:25 |
| PR | Nova Esperança | 71/52 | 1771766 | Efetivada | 24/09/2026 | 17:01:26 |
| PR | Nova Esperança | 71/52 | 1824872 | Prevista | 24/09/2026 | 17:01:26 |
| SP | São Paulo | 422/222 | 1830519 | Efetivada | 25/10/2026 | 17:02:59 |

## Cruzamentos que esclarecem prioridades

- **Macaparana (PE), zona 90, seção 24:** a urna prevista consta em registro Gedai datado de 24/10, enquanto os logs de votação públicos analisados não identificaram evento atribuível à urna efetivada. É necessário correlacionar ata, ocorrência e ambos os equipamentos.
- **Salvador (BA), zona 19, seções 71 e 450:** encerramento BWeb após 19h e referências de preparação em pacotes datados de dias distintos. Os logs de votação analisados, entretanto, **já registravam atividade da urna efetivada antes das 17h**, portanto não há indicação direta de substituição tardia nesses dois casos.
- **São Paulo (SP), zona 422, seção 222:** o Gedai contém uma referência cuja data interna é 25/10, embora o BWeb registre encerramento às 17:02:59. É necessário verificar o significado operacional da linha do Gedai antes de concluir qualquer coisa sobre preparação ou substituição.

## Limitações essenciais

A pesquisa encontra números físicos de urna citados no texto de logs aninhados, mas a mera referência numérica precisa de validação semântica. Uma diferença entre dois pacotes de dias distintos pode decorrer de extração acumulada ou atualização de publicação. O número de série no Gedai não estabelece, por si, a seção eleitoral de uso nem o momento de eventual substituição.

## Solicitação documental

Solicitar às autoridades eleitorais dicionário dos eventos do Gedai, explicação da periodicidade e escopo dos pacotes de 24/10 e 25/10, registros de preparação/carga desses equipamentos, atas de mesa, ocorrências Ocorre JE e identificação de eventuais equipamentos de contingência. **Não solicitar dados pessoais de eleitores.**

Fonte oficial: https://dadosabertos.tse.jus.br/dataset/resultados-2026-logs-do-sistema-de-preparacao-das-urnas-eletronicas-gedai-2-turno

Evidências extraídas: https://github.com/thayanneoliveira/Fatovia/tree/main/docs/auditoria/gedai-2026/ufs
