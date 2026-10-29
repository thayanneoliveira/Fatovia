# FATOVIA AUDITA | Urnas e atividade registrada depois das 17h

Segundo turno presidencial de 25/10/2026. Cruzamento de BU, correspondência CEFT e registros do log da urna.

## Síntese

- 2.673 seções brasileiras com equipamento efetivado diferente do previsto no CEFT.
- 118 dessas seções com encerramento BWeb depois de 17h10.
- 83 das 118 com eventos de votação na urna efetivada antes de 17h.
- 28 com eventos de voto na urna anterior antes de 17h e na urna efetivada apenas depois de 17h.
- 7 sem evento de votação atribuível à urna efetivada nos logs publicados.

**Não é possível inferir a hora exata da substituição a partir de CEFT ou do primeiro voto registrado na urna efetivada.**

## 28 seções para pedido de esclarecimento

| UF | Cidade | Município / zona / seção | Encerramento | Eventos urna anterior antes de 17h | Eventos urna efetivada após 17h | Urna efetivada |
|---|---|---|---|---:|---:|---|
| AL | PALMEIRA DOS ÍNDIOS | 28258/10/85 | 17:49:01 | 265 | 2 | 1769245 |
| BA | LAURO DE FREITAS | 36854/180/19 | 19:00:45 | 325 | 9 | 1668737 |
| BA | LAURO DE FREITAS | 36854/180/288 | 19:01:44 | 327 | 3 | 1668918 |
| BA | SALVADOR | 38490/1/1 | 19:01:26 | 332 | 3 | 2380929 |
| BA | SERRINHA | 39098/150/269 | 17:26:14 | 194 | 13 | 1674375 |
| BA | SIMÕES FILHO | 39136/33/100 | 19:00:45 | 323 | 6 | 1664439 |
| CE | FORTALEZA | 13897/114/51 | 17:17:18 | 315 | 7 | 2452531 |
| CE | JAGUARETAMA | 14354/72/96 | 17:21:58 | 74 | 14 | 1818768 |
| CE | MARACANAÚ | 15857/122/233 | 17:33:58 | 302 | 3 | 2285803 |
| CE | CRUZ | 15890/30/208 | 17:17:42 | 271 | 3 | 2207397 |
| CE | VARJOTA | 98574/65/153 | 17:50:25 | 273 | 4 | 1657912 |
| ES | CARIACICA | 56251/34/142 | 19:00:26 | 224 | 2 | 1760781 |
| GO | TRINDADE | 96253/49/159 | 17:35:54 | 261 | 4 | 1665159 |
| MA | CAROLINA | 7536/26/73 | 17:21:26 | 262 | 8 | 2307161 |
| MA | SERRANO DO MARANHÃO | 8524/107/89 | 17:42:33 | 74 | 1 | 2129006 |
| MG | MARIANA | 47996/171/90 | 17:49:02 | 206 | 8 | 1674424 |
| MG | MONTES CLAROS | 48658/317/419 | 17:15:07 | 322 | 5 | 2061321 |
| MG | SANTA RITA DO SAPUCAÍ | 51918/248/32 | 17:12:41 | 233 | 8 | 2103134 |
| PA | SANTA IZABEL DO PARÁ | 5290/36/67 | 17:16:17 | 284 | 8 | 1805416 |
| PE | CABO DE SANTO AGOSTINHO | 23574/121/209 | 19:05:12 | 351 | 1 | 2171243 |
| PR | ARAUCÁRIA | 74357/50/390 | 17:29:25 | 215 | 1 | 2142598 |
| PR | CAMPO LARGO | 74810/9/93 | 17:16:02 | 281 | 1 | 2092750 |
| PR | PONTA GROSSA | 77771/14/51 | 19:02:08 | 284 | 1 | 2066392 |
| RN | NATAL | 17612/3/122 | 19:00:53 | 340 | 5 | 1794136 |
| RS | BAGÉ | 85316/142/263 | 17:54:33 | 240 | 15 | 1681151 |
| SP | GUARUJÁ | 64750/310/303 | 17:10:21 | 270 | 10 | 2146123 |
| SP | GUARULHOS | 64777/395/48 | 17:21:46 | 279 | 15 | 1812142 |
| SP | SÃO PAULO | 71072/255/113 | 17:50:10 | 288 | 3 | 2047245 |

## Sete seções sem eventos de voto atribuíveis à urna efetivada

| UF | Cidade | Município / zona / seção | Encerramento | Eventos de outra urna antes de 17h |
|---|---|---|---|---:|
| BA | RUY BARBOSA | 38458/87/193 | 18:58:49 | 242 |
| ES | SANTA MARIA DE JETIBÁ | 57932/9/112 | 19:43:21 | 304 |
| MG | ARAGUARI | 40690/16/264 | 18:35:09 | 114 |
| MG | CHAPADA GAÚCHA | 41882/320/185 | 23:04:42 | 96 |
| PE | MACAPARANA | 24791/90/24 | 17:22:25 | 243 |
| SP | CAMPO LIMPO PAULISTA | 62936/344/131 | 18:27:24 | 212 |
| SP | LIMEIRA | 66397/399/48 | 17:33:35 | 201 |

## Limitações

- A diferença entre urna prevista e efetivada não fornece o instante da troca.
- Horários de encerramento do BWeb não reproduziram as contagens agregadas oficiais de seções após 17h10. A metodologia necessita reconciliação antes de atribuir seções à prorrogação.
- O primeiro voto após 17h numa urna pode ocorrer mesmo quando o equipamento foi substituído antes das 17h.
- A urna pode ter logs incompletos por procedimentos de contingência; ausência de registros não é prova de troca tardia.
- Os quatro arquivos de cada seção examinada tiveram SHA-512 coincidente com os valores declarados no VSC, sem validação da cadeia de certificados.
- A Resolução TSE 23.751/2026 prevê substituição durante a votação por contingência, com registro em ata e comunicação pelo Ocorre JE.

## Pedidos de esclarecimento documental

Solicitar aos TREs as atas de mesa, lançamentos Ocorre JE, registros de contingência, instantes de substituição e logs originais dos equipamentos das 35 seções destacadas.
Solicitar ao TSE a metodologia de normalização de horários e definição de seções encerradas depois de 17h10.

## Fontes

- Evidências por UF: docs/auditoria/horarios-e-contingencias-2026/atividade/
- Correspondências e horários por UF: docs/auditoria/horarios-e-contingencias-2026/ufs/
- https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026
- https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno
