# Cruzamento das correspondências e boletins (MG e PE)
Arquivos oficiais, SHA-512 e índice por município, zona e seção.

## MG
- 24: 52061 seções; hash MATCH; linhas 52061
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_ESPERADA
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, None, urna=NR_URNA_ESPERADA
- 25: 52062 seções; hash MATCH; linhas 52062
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_ESPERADA
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, None, urna=NR_URNA_ESPERADA
- efetivada: 52062 seções; hash MATCH; linhas 52062
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_EFETIVADA
- bu: 52062 seções; hash MATCH; linhas 203235
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_EFETIVADA
- 24_vs_25: 15 identificadores de urna diferentes; 0 seções só na base anterior; 1 só na posterior.
- 25_vs_efetivada: 169 identificadores de urna diferentes; 0 seções só na base anterior; 0 só na posterior.
- efetivada_vs_bu: 0 identificadores de urna diferentes; 0 seções só na base anterior; 0 só na posterior.

## PE
- 24: 21418 seções; hash MATCH; linhas 21418
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_ESPERADA
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, None, urna=NR_URNA_ESPERADA
- 25: 21418 seções; hash MATCH; linhas 21418
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_ESPERADA
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, None, urna=NR_URNA_ESPERADA
- efetivada: 21418 seções; hash MATCH; linhas 21418
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_EFETIVADA
- bu: 21418 seções; hash MATCH; linhas 83243
  - Colunas-chave: CD_MUNICIPIO, NR_ZONA, NR_SECAO, urna=NR_URNA_EFETIVADA
- 24_vs_25: 15 identificadores de urna diferentes; 0 seções só na base anterior; 0 só na posterior.
- 25_vs_efetivada: 99 identificadores de urna diferentes; 0 seções só na base anterior; 0 só na posterior.
- efetivada_vs_bu: 0 identificadores de urna diferentes; 0 seções só na base anterior; 0 só na posterior.

Diferenças entre a urna prevista e a efetivada podem resultar de contingências; identificação de causa exige documentação específica.