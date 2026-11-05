# FatoVia | Resultado nacional de coerência pública 2026

**Concluído em 04/11/2026.** 27 UFs + exterior (ZZ), primeiro e segundo turnos de 2026.
**Evidência primária executada:** [workflow nacional com quatro lotes](https://github.com/thayanneoliveira/Fatovia/actions/runs/41875278223).

## Resultados verificados pela auditoria FatoVia

| Critério | Total |
| --- | ---: |
| Seções com registro presidencial nos BUs web do segundo turno | 499.205 |
| Registros de seção presidencial no detalhe da apuração do segundo turno | 499.248 |
| Seções presentes nas duas publicações | 499.205 |
| Seções do BU sem correspondência no detalhe | **0** |
| Seções adicionais no detalhe (todas em ZZ) | **43** |
| Diferenças em aptos, comparecimento ou abstenções nas 499.205 seções comuns | **0** |
| Seções no detalhe do exterior sem BU presidencial e com aptos > comparecimento + abstenções | **41** |
| Seções ZZ no detalhe sem BU presidencial com equação de aptos balanceada | **2** |
| Zonas ELO identificadas no primeiro turno | 6.292 |
| Zonas ELO identificadas no segundo turno | **0** |

### Interpretação do exterior

Há 43 chaves de seção no detalhe da apuração sem linha presidencial correspondente no BU web. Dessas, 41 possuem quantitativos que não satisfazem aptos = comparecimento + abstenções, compatível com seções não instaladas que podem constar no inventário oficial. As outras duas apresentam equação balanceada:

- ZZ / município 29564 / zona 1 / seção 91.
- ZZ / município 30686 / zona 1 / seção 443.

O projeto de terceiros DataUrnas-BR, que **não reexecutamos integralmente**, relata justamente essas duas seções sem RDV e um total de 41 seções não instaladas no exterior. Trata-se de uma **explicação plausível que requer confirmação pelo campo de instalação do arquivo oficial**, não de constatação de irregularidade.

A diferença entre 499.207 seções identificadas no relatório de correspondências anterior e 499.205 seções com linhas presidenciais no BU neste teste decorre de **universos diferentes**. Não confundir duas linhas ausentes para presidente com dois votos ausentes.

### Outros cruzamentos, sem inferência causal

- Primeiro × segundo turno: 480.585 seções tiveram quantidade distinta de comparecimento e 55.722 tiveram número de aptos distinto. São mudanças esperáveis entre consultas de eleições em momentos distintos; não provas de irregularidade.
- Perfil pré-eleitoral × detalhe da apuração do segundo turno: 317.851 seções com contagem de aptos diferente. Fotografia cadastral e universo do dia da votação podem divergir; exige modelagem de TTE e agregações antes de classificar.
- ELO: os arquivos examinados apresentam 6.292 zonas de primeiro turno, **nenhuma zona de segundo turno**. O cruzamento ELO × detalhe 2T não está disponível. Não registrar zero divergências para fonte indisponível.

## Limites

- O controle de 499.205 confirma concordância **dos quantitativos agregados publicados pelo próprio TSE**, não validação individual de presença.
- Não confirma nem descarta voto atribuído a pessoa falecida.
- RDV, logs de habilitação individual e documentação de custódia exigem etapa própria.
- O TSE é fonte institucional comum aos arquivos; concordância não equivale a fonte física independente.

## Rastreabilidade

- [Código de coleta e cruzamento multi-UF](./auditar_coerencia_lote.py)
- [Consolidador nacional](./consolidar_coerencia_nacional.py)
- [Teste adicional focalizado nos sete últimos territórios](./conferir_bu_detalhe_7ufs.py)
- [Referência anterior, validação de identidade das urnas](https://github.com/thayanneoliveira/Fatovia/actions/runs/41840015604)
- [Resumo DataUrnas-BR, terceiro](https://github.com/alissonlinneker/DataUrnas-BR/blob/main/data/parquet/2026/t2/rdv_nacional_resumo.json)

**Conclusão restrita:** 0 diferenças nos quantitativos de aptos, comparecimento e abstenções das seções presidenciais comuns às duas publicações oficiais; 43 diferenças de cobertura documental no exterior, cuja natureza operacional requer confirmação.
