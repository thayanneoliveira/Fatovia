# FATOVIA AUDITA | Reconciliação de cortes BWeb/TSE

**Status:** 27_UFS_ANALISADAS_CRITERIOS_DIVERGEM. **UFs:** 27/27.

O TSE divulgou 24.268 seções que permaneceram abertas após 17h10. O teste abaixo
conta por critério explícito o campo DT_ENCERRAMENTO do BWeb. Essa variável
pode representar um evento operacional diferente e os totais não devem ser
interpretados como mesmo fenômeno sem confirmação da metodologia.

| Critério | Seções (soma das 27 UFs) |
|---|---:|
| BWeb depois_17:00 | 465,872 |
| BWeb depois_17:02 | 201,409 |
| BWeb depois_17:05 | 54,045 |
| BWeb depois_17:10 | 13,031 |
| BWeb depois_17:15 | 8,989 |
| BWeb depois_18:00 | 7,086 |
| BWeb depois_19:00 | 6,326 |
| Levantamento TSE após 17h10 | 24,268 |

## Por UF

| UF | TSE após 17h10 | BWeb após 17h10 | Diferença |
|---|---:|---:|---:|
| AC | 33 | 0 | -33 |
| AL | 241 | 91 | -150 |
| AM | 347 | 0 | -347 |
| AP | 47 | 14 | -33 |
| BA | 3,787 | 2,108 | -1,679 |
| CE | 408 | 161 | -247 |
| DF | 696 | 289 | -407 |
| ES | 105 | 36 | -69 |
| GO | 205 | 63 | -142 |
| MA | 865 | 374 | -491 |
| MG | 740 | 240 | -500 |
| MS | 97 | 0 | -97 |
| MT | 268 | 9 | -259 |
| PA | 701 | 292 | -409 |
| PB | 579 | 405 | -174 |
| PE | 1,872 | 1,035 | -837 |
| PI | 237 | 87 | -150 |
| PR | 243 | 90 | -153 |
| RJ | 5,713 | 4,036 | -1,677 |
| RN | 238 | 84 | -154 |
| RO | 102 | 0 | -102 |
| RR | 43 | 0 | -43 |
| RS | 220 | 68 | -152 |
| SC | 98 | 41 | -57 |
| SE | 187 | 100 | -87 |
| SP | 6,093 | 3,371 | -2,722 |
| TO | 103 | 37 | -66 |

## Perguntas a esclarecer junto ao TSE

- Qual é a definição operacional de 'permanecer aberta após 17h10' no levantamento de 27/10?
- Foi utilizado DT_ENCERRAMENTO, hora do último evento de voto, impressão do BU ou outra marca?
- Que seções foram excluídas e por quais códigos de situação, origem do voto ou fuso?
- Os dados do BWeb e do levantamento foram extraídos da mesma versão e no mesmo instante?
- Há dicionário de campos com critérios de ajuste de horário de Brasília e contingências?

## Limitações

- O critério declarado pelo TSE para permanecer aberta após 17h10 pode não corresponder ao campo DT_ENCERRAMENTO.
- Os cortes alternativos são exploratórios e não constituem equivalência comprovada.
- Diferença entre totais exige documentação dos critérios, não constitui por si só irregularidade.
- Horário de encerramento não é horário de substituição nem horário de cada voto.

Fonte TSE: https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno
