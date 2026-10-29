# FATOVIA AUDITA | Identificação biométrica e voto por seção | 2026

**Status: EXECUTADO_COM_RESSALVAS**

**UFs incorporadas:** 28/28

**Unidades pendentes:** nenhuma

- Seções válidas (Brasil sem exterior): **497,897**.
- Habilitações sem biometria: **8,632,488** (não significa votos irregulares).
- Taxa sobre comparecimento: **6.7518%**.
- Associação bruta ponderada: **0.06409**.

## Estimativas por 10 pontos percentuais de taxa de identificação sem biometria

| Modelo | n seções | Municípios | Estimativa em pp | IC95% (pp) |
|---|---:|---:|---:|---|
| municipio_fe | 497,897 | 5,571 | +0.227 | [-0.544, +0.998] |
| municipio_fe_mais_controles | 497,897 | 5,571 | -0.091 | [-0.799, +0.618] |
| sensibilidade_sem_pesos | 497,897 | 5,571 | -0.124 | [-0.755, +0.507] |
| sensibilidade_100_validos_min | 492,559 | 5,571 | -0.078 | [-0.792, +0.636] |
| sensibilidade_corte_cauda_99percentil | 492,930 | 5,570 | -0.226 | [-1.099, +0.646] |

## UFs

| UF | Seções | Taxa sem biometria | Associação ajustada (pp por +10pp) |
|---|---:|---:|---:|
| AC | 2,270 | 4.994% | +0.133 |
| AL | 7,101 | 6.962% | +1.044 |
| AM | 8,157 | 5.427% | -0.461 |
| AP | 1,914 | 4.578% | Não estimável |
| BA | 35,476 | 7.453% | +1.013 |
| CE | 23,765 | 7.125% | +2.793 |
| DF | 6,969 | 4.502% | Não estimável |
| ES | 9,844 | 6.284% | +1.134 |
| GO | 15,686 | 6.638% | +1.691 |
| MA | 18,093 | 6.295% | +1.538 |
| MG | 52,062 | 6.807% | +1.151 |
| MS | 7,106 | 7.247% | -3.544 |
| MT | 8,287 | 6.597% | -1.462 |
| PA | 20,827 | 5.559% | +0.412 |
| PB | 10,712 | 7.266% | +1.649 |
| PE | 21,418 | 6.525% | +1.577 |
| PI | 10,225 | 9.003% | +1.829 |
| PR | 27,142 | 6.988% | -0.253 |
| RJ | 37,675 | 7.445% | +1.460 |
| RN | 8,115 | 8.099% | +0.773 |
| RO | 4,698 | 6.266% | -0.575 |
| RR | 1,519 | 4.098% | Não estimável |
| RS | 27,547 | 8.453% | -2.433 |
| SC | 17,326 | 7.510% | -1.710 |
| SE | 5,923 | 6.968% | +0.215 |
| SP | 103,656 | 5.964% | -3.411 |
| TO | 4,384 | 4.946% | +0.772 |

## Limitações

- Trata-se de inferência ecológica. Não existe vínculo entre votos individuais e identificação biométrica.
- Nem uma associação estatística nem sua ausência provam ou descartam fraude.
- O modelo controla diferenças fixas entre municípios e tamanho/comparecimento de seções; não controla todos os fatores de confusão.
- Os dados foram validados por hash e são publicados pelo TSE. Não há auditoria de identificação pessoal.
- Arquivos por UF estão nos artefatos da execução do GitHub Actions.
