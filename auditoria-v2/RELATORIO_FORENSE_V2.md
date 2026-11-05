# FatoVia | Auditoria forense documental v2 (04/11/2026)

**Protocolo TSE:** 83355301174031. **Objeto:** eleições do segundo turno de 25/10/2026, 27 UFs e exterior (ZZ). **Status geral quanto à hipótese de fraude:** INCONCLUSIVO, sem prova verificável suficiente para concluir sua ocorrência ou descartar todas as hipóteses possíveis.

## 1. Sumário executivo (10 linhas)

1. O trabalho original do FatoVia processou 168 ZIPs com SHA-512 coincidente com referências oficiais e cruzou 499.207 seções.
2. A revisão v2 corrigiu a preservação apenas parcial das divergências individuais.
3. Quatro lotes da v2 foram executados com sucesso para as 28 unidades geográficas, com arquivos oficiais e checagem de SHA-512.
4. A v2 reconstruiu um inventário nacional de **3.077 linhas de exceções documentais**.
5. São 350 mudanças de urna prevista de 24 para 25/10 e 12 novas seções previstas.
6. São mais 2.686 identificadores diferentes entre prevista em 25/10 e efetivada, além de 29 seções presentes apenas na efetivada, todas em ZZ.
7. Entre correspondência efetivada e BU web não houve diferenças de identificador nem diferença nos conjuntos de seções.
8. **15 seções** aparecem em mais de uma comparação de alteração; em duas, a identificação efetivada retorna à da previsão de 24/10.
9. A auditoria não recontou votos RDV nem validou BUs impressos independentes, assinaturas digitais de BU ou correspondência do software instalado.
10. A ausência de divergências dentro do conjunto testado não demonstra ausência de fraude na cadeia eleitoral completa.

## 2. Tabela de alegações e qualidade das evidências

| Alegação | Evidência disponível | Qualidade | Explicações alternativas | Status | Confiança na classificação | O que falta |
| --- | --- | --- | --- | --- | --- | --- |
| Arquivos adquiridos divergem do SHA-512 TSE | 4 ZIPs/UF em 28 UFs com MATCH no manifesto, além da execução v1 | alta para concordância de distribuição | hashes e ZIPs têm fonte oficial comum | refutada no universo v2 testado | alta | autenticação independente da origem |
| 350 alterações de urna prevista indicam fraude | comparação de IDs 24→25/10 | alta para diferença, baixa para causa | preparação e substituições autorizadas | inconclusivo quanto a fraude | alta | atas, ordens, justificativas |
| 2.686 alterações prevista→efetivada são irregulares | comparação de IDs 25→efetivada | alta para diferença, baixa para causa | contingência, manutenção, reservas | inconclusivo | alta | Ocorre JE, lacres, horários e autorização |
| 29 seções adicionais em ZZ são indevidas | efetivada com 29 chaves não presentes na prevista | alta para diferença, baixa para causa | inventário, agregação e atualização documental | diferença confirmada; causa inconclusiva | alta | atos administrativos ZZ |
| 675 GEDAI diferentes significam supressão | v1: SHA interno diferente | média para diferença, baixa para causa | rotação, reexportação e eventos novos | inconclusivo | alta | logs brutos, metadados, retenção |
| Divergência de identificador entre efetivada e BU web | v2: zero em 28 unidades | alta para controle exato | bases oficiais possivelmente correlacionadas | refutada no escopo testado | alta | confronto com BU físico e assinaturas |
| Houve manipulação de votos na totalização | nenhuma prova direta produzida na v2 | insuficiente | resultado correto ou manipulação em etapa fora do controle testado | inconclusivo | alta na insuficiência | RDV, BU assinado, fontes independentes, SISTOT |

**Conceitos:** “confirmado/refutado” restringe-se à proposição específica examinada. “Inconclusivo” não equivale a “provável”. Confiança é uma avaliação da justificativa, não probabilidade numérica de fraude.

## 3. Análise por etapa

- **Software e lacração:** solicitação ao TSE inclui versões, hashes, cerimônias, testes e assinaturas. Falta confrontar verificações por equipamento.
- **Preparação/GEDAI:** hash de distribuição verificado; 675 diferenças internas legadas ainda carecem de interpretação semântica e cronológica.
- **Transporte/guarda:** lacres, recibos, autorizações e movimentações aguardam documentos de custódia.
- **Votação/contingências:** diferenças documentais descritas em 3.077 linhas; não equivalem a 3.077 trocas físicas e incluem alterações repetidas e inclusões de seção.
- **Encerramento/RDV/BU:** v2 confere identificadores de arquivos BU web, não os votos ou assinaturas digitais individuais.
- **Transmissão/totalização:** a recontagem independente ainda é requisito não cumprido pelo FatoVia.
- **Fiscalização:** relatórios regionais devem ser cruzados com testes de integridade, autenticidade e apuração manual.

## 4. Achados críticos e menores

**Crítico de metodologia (corrigido):** o relatório v1 preservava apenas amostras limitadas. A v2 preserva todas as diferenças no CSV, separando troca de identificador, somente anterior e somente posterior.

**Crítico de metodologia (corrigido):** falha de leitura, ausência de ZIP, SHA divergente, coluna de seção inexistente, chave vazia ou conflito de urna impedem conclusão de sucesso.

**Crítico de escopo (aberto):** hashes obtidos de referências oficiais podem coincidir com dados oficiais sem garantir independência das fontes.

**Menor:** duas inversões de sequência documentadas para BA (mun. 35653, zona 173, seção 2: 1753213 → 1833178 → 1753213) e PA (mun. 5215, zona 33, seção 158: 2318458 → 2469714 → 2318458), ainda sem motivo confirmado. Outras 13 seções apresentam alteração em duas etapas. Esses eventos não comprovam fraude.

## 5. Hipóteses concorrentes e testes de falsificação

1. **Substituição irregular vs contingência autorizada:** comparar seção, cronologia, ata, Ocorre JE, lacre e decisão. Trilha íntegra e justificada enfraquece hipótese de irregularidade.
2. **Alteração na transmissão vs totalização regular:** validar BUs assinados, somar votos por seção e reconciliar SISTOT com retificações e logs. Concordância reproduzível enfraquece a hipótese de manipulação pós-assinatura.
3. **Manipulação antes da assinatura vs urna íntegra:** solicitar verificações do software instalado, testes de integridade e autenticidade. Concordância RDV/BU por si só não refuta essa hipótese.
4. **Log GEDAI truncado vs rotação/exportação regular:** comparar originais, metadados, versões e eventos de exportação. O caso PE ZPE019WKS03 requer documento bruto e histórico de retenção.
5. **Anomalia estatística vs variação territorial:** controles por município, zona, comparecimento, modelo e histórico; testes de sensibilidade e multiplicidade; não inferir fraude a partir de Benford ou outliers isolados.

## 6. Lacunas e solicitações

O requerimento de 29/10/2026 já contém 24 grupos documentais. Não duplicar pedido amplo. Priorizar resposta com vínculo **UF/município/zona/seção → ocorrência → equipamento → autorização → ata → data e hora**, além de logs e política de preservação, esclarecimento das 29 seções de ZZ, documentação de contingência para as 15 seções com múltiplas mudanças e relatórios de auditoria regional, incluindo resultados de contagem independente de votos.

## 7. O que não foi perguntado, mas é crucial

- **Independência:** reexecutar RDV × BU com assinaturas, e comparar BUs digitais com exemplares físicos coletados independentemente.
- **Cadeia de custódia:** registrar origem, URL, UTC, arquivo, hash, ferramenta, commit, transformação e responsável por cada cópia.
- **Contraditório:** consultar testes com resultado normal e as melhores explicações administrativas, não apenas os casos excepcionais.
- **Retenção:** solicitar preservação de registros voláteis antes de sua eliminação prevista, conforme competência legal.
- **Comunicação:** não confundir 3.077 linhas de exceções com urnas fraudadas; o conjunto inclui mudanças e inclusões, com 15 seções repetidas.
- **Direito e segurança:** LAI não confere acesso automático a dados protegidos; pedir versões expurgadas, justificativa e custodiante quando houver restrição.

## 8. Conclusão calibrada

**Sustentável:** os arquivos da fonte oficial adquiridos pela v2 passaram nas verificações de SHA-512; os inventários de identificadores foram reprocessados em 28 unidades; as contagens de exceções foram reproduzidas; há demandas documentais objetivas de explicação.

**Não sustentável:** afirmar fraude, manipulação de votos ou que todos os mecanismos eleitorais foram auditados. **Estado:** inconclusivo para alegações gerais de fraude, com evidências documentais sobre diferenças de inventários e nenhuma divergência de identificador efetivada × BU web no recorte nacional.

## 9. Fontes e limitações de proveniência

- [GitHub FatoVia, resultado da v2](https://github.com/thayanneoliveira/Fatovia/actions/runs/41840015604): coleta por lote, manifesto, matriz CSV e hash.
- [Revisão do legado](https://github.com/thayanneoliveira/Fatovia/actions/runs/41839615680): valida metadados do relatório anterior; **não** reprocessa ZIPs.
- [Piloto AC](https://github.com/thayanneoliveira/Fatovia/actions/runs/41839384320): piloto real de todos os arquivos de correspondência e BU web daquele estado.
- [TSE Dados Abertos](https://dadosabertos.tse.jus.br/): origem institucional dos dados; não constitui evidência física independente.
- [Resolução TSE nº 23.673/2021](https://www.tse.jus.br/legislacao/compilada/res/2021/resolucao-no-23-673-14-de-dezembro-de-2021) e [Resolução nº 23.769/2026](https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-769-de-3-de-agosto-de-2026): fiscalização e relatórios de auditoria.
- [TSE, 01/11/2026](https://www.tse.jus.br/comunicacao/noticias/2026/Novembro/tres-devem-encaminhar-ao-tse-relatorios-de-auditoria-das-urnas-eletronicas-ate-4-de-novembro): prevê encaminhamento dos relatórios até 04/11, não comprova divulgação integral imediata.
- [DataUrnas-BR](https://github.com/alissonlinneker/DataUrnas-BR/blob/main/docs/veredicto-auditoria-2026.md): fonte de terceiro para contraditório, **não reexecutada pelo FatoVia**.
- Requerimento e comprovante de protocolo TSE: documentos administrativos enviados e recebidos, sem valor pericial sobre o mérito.

**Trava de escopo:** a auditoria v2 nacional termina apenas no confronto de arquivos e identificadores. RDV, BU assinado, BU físico e custódia constituem etapa técnica adicional, não uma validação implícita.
