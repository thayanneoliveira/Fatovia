# Política permanente de abrangência das auditorias eleitorais FatoVia

## Escopo obrigatório
Toda auditoria nacional, divulgação de resultados nacionais, requerimento amplo e monitoramento automatizado do segundo turno de 2026 deve considerar:
- As 27 unidades federativas: AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP e TO;
- A categoria ZZ, referente à votação do exterior, quando aplicável.

**Nenhum subconjunto de UFs representa o país.** MG e PE são apenas o piloto histórico. Uma análise regional deve estar rotulada com sua abrangência e não pode ser extrapolada para o Brasil.

## Critérios mínimos para chamar um resultado de nacional
1. Lista explícita das 28 unidades (27 UFs + ZZ) e base de dados por unidade.
2. Registro verificável por arquivo: URL, data, SHA-512 oficial, SHA-512 calculado e resultado de comparação.
3. Cobertura por UF: total de seções em cada conjunto, seções ausentes/adicionadas, mudanças de identificador de urna, contingências e divergências de identificação efetivada vs. BU.
4. Status separados por dimensão: download, integridade, análise de conteúdo, evidência administrativa, evidência independente e recontagem de votos.
5. Falha, ausência de arquivo ou erro de análise deve constar como **não avaliado**, nunca como 'zero irregularidades'.
6. Para comunicar ao público, apresentar o denominador nacional e os limites, sem tomar diferença operacional como fraude.
7. Testes de RDV, BU impresso independente, logs individuais e totalização têm status próprios, não são cobertos automaticamente por comparações de CSV ou hash.
8. Toda publicação precisa distinguir resultados concluídos de investigações em andamento, e explicar o método reproduzível.

## Resultados do primeiro cruzamento nacional
Resultado calculado em 29/10/2026, com bases oficiais de segundo turno:
- 168 arquivos ZIP, 168 hashes SHA-512 conferidos com correspondência;
- 499.207 seções nos conjuntos efetivados verificados;
- 350 identificadores esperados alterados entre 24 e 25 de outubro;
- 2.686 identificadores diferentes entre previsão de 25/10 e efetivação;
- zero divergências de **identificador de urna** entre correspondências efetivadas e a identificação presente no arquivo do BU;
- 675 arquivos GEDAI internos com conteúdo alterado entre as versões;
- 12 seções adicionadas ao conjunto esperado de 25/10.

Estes resultados **não comprovam ausência nem existência de fraude**, e tampouco constituem recontagem de votos.

## Fontes e reprodutibilidade
- [Resumo nacional com 28 unidades](auditoria-nacional-resultados/RESUMO_NACIONAL_2026.md)
- [Scripts nacionais](auditoria-nacional-2026/)
- [Registros nacionais](auditoria-nacional-resultados/)
- [Histórico regional de MG e PE](auditoria-resultados/)

Adota-se publicação neutra, factual, com fonte, hipótese, teste e limite em campos distintos.
