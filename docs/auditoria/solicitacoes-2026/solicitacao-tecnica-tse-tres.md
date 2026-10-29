# FATOVIA AUDITA | Solicitação técnica de esclarecimentos à Justiça Eleitoral

**Objeto:** preservação e fornecimento de registros documentais de seções eleitorais identificadas em conferências públicas do segundo turno presidencial de 25/10/2026.

**Finalidade:** verificar a rastreabilidade das contingências, dos logs, da identificação das urnas e da transmissão/totalização; não formular imputação de irregularidade, não solicitar dados de votantes e não questionar o conteúdo de votos individuais.

## Apresentação resumida

- Seções brasileiras identificadas para solicitação dirigida aos TREs: **47**. Uma seção pode integrar mais de uma categoria de verificação.
- **28** seções com eventos de outra urna antes das 17h e da urna efetivada apenas depois das 17h. Isso não determina quando houve substituição.
- **7** seções sem evento atribuível à urna efetivada nos logs públicos examinados.
- **6** diferenças entre contagem de eventos no log publicado e comparecimento do BU, embora RDV e BU tenham coincidido.
- **11** casos históricos de ausência de identificação da urna efetivada entre eventos do log, com sobreposição possível com as 35 seções.
- **Uma seção de São Paulo** teve arquivo log.jez ausente no pacote bruto disponibilizado.
- **29** seções de apuração especial no exterior serão tratadas separadamente por dependerem de procedimento próprio.
- As 16 antigas falhas de transporte e leitura já foram reprocessadas, por isso não integram os pedidos como inconsistências eleitorais.

## Pedidos dirigidos aos TREs competentes

Para cada seção do cadastro abaixo, solicita-se, preferencialmente em formato digital com identificação de origem e integridade:

1. **Ata da Mesa Receptora** integral e eventuais anexos, com descrição das interrupções, horários das ocorrências e providências adotadas.
2. **Registros Ocorre JE**, com instante da abertura e encerramento da ocorrência, motivo, identificador da urna inicialmente usada, de contingência e identificação da zona/seção.
3. **Registro de substituição ou contingência**, quando houver, com cronologia, ordem de serviço, número de equipamento e dados não pessoais necessários para reconstruir o evento.
4. **Logs originais disponíveis dos equipamentos envolvidos**, quando previstos para fiscalização, com indicação do critério de compilação/extração, lacunas e eventuais limitações de preservação.
5. **Identificação das mídias e evidência de custódia**, quando houver movimentação para recuperação de arquivos, com datas, justificativas e documentação de autorização.
6. **Esclarecimento sobre registros de votação na urna efetivada apenas depois das 17h**, destacando-se que primeiro voto depois desse horário não equivale à hora da troca.

## Pedidos dirigidos ao TSE

1. **Dicionário e método** da apuração divulgada em 27/10 sobre seções que permaneceram abertas após 17h10, incluindo campo usado, fuso, exclusões e forma de deduplicação.
2. **Relatórios de totalização** que identifiquem BUs pendentes, motivos, decisões e seções cujo BU foi produzido em urna substituta (SISTOT).
3. **Logs do Transportador, RecArquivos e banco de totalização** e descrição dos códigos de status, de forma a distinguir produção, recepção, rejeição, reprocessamento e totalização.
4. **Esclarecimento dos formatos especiais do exterior**, abrangendo 29 seções com arquivos não reconhecidos pelo comparador convencional e duas entradas CEFT sem BU correspondente.
5. **Metodologia de vinculação Gedai ↔ CEFT**, identificando quais eventos de preparação podem ser ligados inequivocamente ao número físico do equipamento e quais registros não são publicados.

## Relação de seções por TRE

### AL (1 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| PALMEIRA DOS ÍNDIOS | 28258 | 10 | 85 | TRANSICAO_TEMPORAL |

### BA (8 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CONDE | 34711 | 21 | 178 | LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO |
| IBOTIRAMA | 35653 | 173 | 235 | LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO |
| LAURO DE FREITAS | 36854 | 180 | 19 | TRANSICAO_TEMPORAL |
| LAURO DE FREITAS | 36854 | 180 | 288 | TRANSICAO_TEMPORAL |
| RUY BARBOSA | 38458 | 87 | 193 | LOG_EFETIVADA_SEM_EVENTOS, CEFT_URNA_AUSENTE_DOS_LOGS |
| SALVADOR | 38490 | 1 | 1 | TRANSICAO_TEMPORAL |
| SERRINHA | 39098 | 150 | 269 | TRANSICAO_TEMPORAL |
| SIMÕES FILHO | 39136 | 33 | 100 | TRANSICAO_TEMPORAL |

### CE (5 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CRUZ | 15890 | 30 | 208 | TRANSICAO_TEMPORAL |
| FORTALEZA | 13897 | 114 | 51 | TRANSICAO_TEMPORAL |
| JAGUARETAMA | 14354 | 72 | 96 | TRANSICAO_TEMPORAL |
| MARACANAÚ | 15857 | 122 | 233 | TRANSICAO_TEMPORAL |
| VARJOTA | 98574 | 65 | 153 | TRANSICAO_TEMPORAL |

### ES (2 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CARIACICA | 56251 | 34 | 142 | TRANSICAO_TEMPORAL |
| SANTA MARIA DE JETIBÁ | 57932 | 9 | 112 | LOG_EFETIVADA_SEM_EVENTOS |

### GO (1 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| TRINDADE | 96253 | 49 | 159 | TRANSICAO_TEMPORAL |

### MA (3 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CAROLINA | 7536 | 26 | 73 | TRANSICAO_TEMPORAL |
| SÃO JOSÉ DE RIBAMAR | 8893 | 47 | 609 | LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO |
| SERRANO DO MARANHÃO | 8524 | 107 | 89 | TRANSICAO_TEMPORAL |

### MG (5 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| ARAGUARI | 40690 | 16 | 264 | LOG_EFETIVADA_SEM_EVENTOS, CEFT_URNA_AUSENTE_DOS_LOGS |
| CHAPADA GAÚCHA | 41882 | 320 | 185 | LOG_EFETIVADA_SEM_EVENTOS, CEFT_URNA_AUSENTE_DOS_LOGS |
| MARIANA | 47996 | 171 | 90 | TRANSICAO_TEMPORAL |
| MONTES CLAROS | 48658 | 317 | 419 | TRANSICAO_TEMPORAL |
| SANTA RITA DO SAPUCAÍ | 51918 | 248 | 32 | TRANSICAO_TEMPORAL |

### PA (3 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| BELÉM | 4278 | 98 | 294 | CEFT_URNA_AUSENTE_DOS_LOGS |
| SANTA IZABEL DO PARÁ | 5290 | 36 | 67 | TRANSICAO_TEMPORAL |
| SANTA IZABEL DO PARÁ | 5290 | 36 | 441 | CEFT_URNA_AUSENTE_DOS_LOGS |

### PB (2 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CONDE | 19933 | 3 | 259 | CEFT_URNA_AUSENTE_DOS_LOGS |
| SANTA RITA | 21750 | 2 | 254 | LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO |

### PE (2 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CABO DE SANTO AGOSTINHO | 23574 | 121 | 209 | TRANSICAO_TEMPORAL |
| MACAPARANA | 24791 | 90 | 24 | LOG_EFETIVADA_SEM_EVENTOS, CEFT_URNA_AUSENTE_DOS_LOGS |

### PI (1 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| PARNAÍBA | 11533 | 3 | 216 | LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO |

### PR (3 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| ARAUCÁRIA | 74357 | 50 | 390 | TRANSICAO_TEMPORAL |
| CAMPO LARGO | 74810 | 9 | 93 | TRANSICAO_TEMPORAL |
| PONTA GROSSA | 77771 | 14 | 51 | TRANSICAO_TEMPORAL |

### RJ (1 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| SÃO GONÇALO | 58971 | 68 | 154 | CEFT_URNA_AUSENTE_DOS_LOGS |

### RN (1 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| NATAL | 17612 | 3 | 122 | TRANSICAO_TEMPORAL |

### RS (3 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| BAGÉ | 85316 | 142 | 263 | TRANSICAO_TEMPORAL |
| BOA VISTA DO INCRA | 89060 | 17 | 191 | LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO |
| VANINI | 84913 | 138 | 14 | CEFT_URNA_AUSENTE_DOS_LOGS |

### SP (6 seções)

| Cidade | Município TSE | Zona | Seção | Classes |
|---|---:|---:|---:|---|
| CAMPO LIMPO PAULISTA | 62936 | 344 | 131 | LOG_EFETIVADA_SEM_EVENTOS, CEFT_URNA_AUSENTE_DOS_LOGS |
| GUARUJÁ | 64750 | 310 | 303 | TRANSICAO_TEMPORAL |
| GUARULHOS | 64777 | 395 | 48 | TRANSICAO_TEMPORAL |
| GUARULHOS | 64777 | 395 | 298 | ARQUIVOS_DA_SECAO_AUSENTES_OU_EXTRAS |
| LIMEIRA | 66397 | 399 | 48 | LOG_EFETIVADA_SEM_EVENTOS, CEFT_URNA_AUSENTE_DOS_LOGS |
| SÃO PAULO | 71072 | 255 | 113 | TRANSICAO_TEMPORAL |

## Ressalvas e procedimento de validação

- O CEFT não contém o momento de uma substituição. Encerramento tardio de BU não prova alteração tardia da urna.
- Informações de logs e BUs em poder do mesmo órgão são fontes dependentes. Verificações independentes de BUs impressos exigem acervo externo.
- Uma contagem distinta de eventos pode refletir contingência, formato de log ou ausência de trilha, sem necessariamente indicar divergência de votos.
- A cadeia de certificados das assinaturas digitais ainda não foi verificada integralmente; SHA-512 comparado ao VSC não substitui verificação criptográfica de autenticidade.
- Os pedidos não buscam identificação biométrica pessoal nem associação de votos a eleitores.

## Base regulatória e fontes

- TSE, Resolução 23.751/2026, arts. 147, 152 e 155: https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026
- TSE, calendário eleitoral 2026, arquivos e relatórios requisitáveis por entidades fiscalizadoras: https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-760-de-2-de-marco-de-2026
- Registros públicos da análise: https://github.com/thayanneoliveira/Fatovia/tree/main/docs/auditoria/horarios-e-contingencias-2026
- Cadastro nacional de urnas e seções: https://github.com/thayanneoliveira/Fatovia/tree/main/docs/auditoria/geografia-2026
