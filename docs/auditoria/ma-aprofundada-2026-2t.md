# FATOVIA AUDITA | Maranhão, segundo turno 2026

Data UTC: 2026-10-28T11:12:30.383566+00:00.

## Resultado das verificações

- Seções indexadas no pacote bruto: **18.093**.
- Seções amostradas: **6** (3 com diferenças de identificação e 3 controles).
- RDV presidencial igual ao BU publicado: **6/6**.
- Eventos de voto nos logs iguais ao comparecimento: **6/6**.
- Número da urna no RDV coincide com a urna efetivada: **6/6**.
- Urna efetivada aparece nos eventos de voto dos logs: **6/6**.
- SHA-512 dos arquivos presentes no pacote igual ao declarado na estrutura VSC: **24**.
- SHA-512 divergente entre arquivos presentes e hash declarado: **0**.
- Referências na estrutura VSC sem arquivo correspondente nesse pacote: **42** (não se trata, por si só, de falha).

| Município (código TSE) / Zona / Seção | Tipo | RDV x BU | Log x comparecimento | Urna RDV x CEFT | Urna CEFT no log | Hashes locais |
|---|---|---|---|---|---|---|
| 7536/26/88 | foco | coincide | coincide | sim | sim | 4 OK |
| 9210/1/124 | foco | coincide | coincide | sim | sim | 4 OK |
| 9210/1/125 | foco | coincide | coincide | sim | sim | 4 OK |
| 7030/52/32 | controle | coincide | coincide | sim | sim | 4 OK |
| 7048/70/184 | controle | coincide | coincide | sim | sim | 4 OK |
| 7005/12/21 | controle | coincide | coincide | sim | sim | 4 OK |

## Limitações cruciais

1. **Assinatura criptográfica não validada**: foi conferida somente a igualdade dos hashes SHA-512 com valores declarados nas estruturas VSC. Não se realizou verificação criptográfica das assinaturas digitais, dos certificados nem da cadeia de confiança.
2. Os arquivos VSC mencionam artefatos adicionais que não integram o pacote público de arquivos totalizados. A ausência desses arquivos nesse ZIP não demonstra adulteração.
3. O RDV, o BU e o log são produzidos pela infraestrutura eleitoral; concordância entre eles não comprova que a intenção individual do eleitor foi gravada corretamente.
4. Mudança da identificação de uma urna, registros de contingência e campos de divergência vazios não são fraude por si. É necessário consultar critérios de preenchimento e documentos operacionais.
5. O pacote de arquivos transmitidos inclui **somente registros na situação Totalizado**, conforme aviso do Portal de Dados Abertos do TSE; não serve sozinho para excluir a existência de ocorrências ou tentativas de transmissão rejeitadas.

## Reprodução e fontes

- Dataset TSE: https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao
- Boletins de urna: https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna
- Código de extração via HTTP Range: auditoria/ma_arqurna_range.py
- Código de teste de RDV, SHA512 e logs: auditoria/ma_amostra_profunda.py
- Especificações ASN.1 v2: auditoria/spec/ (origem DataUrnas-BR, licença MIT)

**Conclusão:** nas seis seções testadas, não foi observada divergência nas contagens verificadas. A validação criptográfica da assinatura e a justificativa das trocas de urna dependem de verificações adicionais.
