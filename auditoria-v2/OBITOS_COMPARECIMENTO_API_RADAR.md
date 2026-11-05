# FatoVia | Radar de APIs e limites: óbitos × comparecimento eleitoral 2026

**Data:** 04/11/2026. **Questão verificável:** houve registro de comparecimento em 25/10/2026 vinculado a inscrição cujo titular tinha óbito confirmado anterior à votação?

## Mapa de recursos

| Fonte / projeto | Acesso | Informação | Comparecimento nominal? |
| --- | --- | --- | --- |
| [TSE Dados Abertos](https://dadosabertos.tse.jus.br/dataset/comparecimento-e-abstencao-2026) | público | perfis agregados de comparecimento e abstenção | não |
| [TSE BU web](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna) | público | comparecimento/abstenção por seção | não |
| [TSE detalhe da apuração](https://dadosabertos.tse.jus.br/dataset/resultados-2026) | público | comparecimento/abstenção por seção | não |
| [TSE logs](https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao) | público | eventos por seção, horário e modalidade de habilitação | não |
| [esteleicao GitHub](https://github.com/ralbuque/esteleicao) | código aberto | analisa logs, horário, habilitações e abstenção por seção | não |
| [mcp-brasil GitHub](https://github.com/Mcp-Brasil/mcp-brasil) | código aberto | cliente de resultados e eleições | não |
| [tse-eleicoes GitHub](https://github.com/olegantonov/tse-eleicoes) | código aberto | cliente CKAN / DivulgaCandContas | não |
| [Barramento do Registro Civil](https://api.hml.barramento.registrocivil.org.br/docs/) | credenciais/autorização | óbito por CPF e em lote | óbito individual sim; votação não |
| [Transparência Registro Civil](https://transparencia.registrocivil.org.br/registros) | público | volume de óbitos regional e temporal | não |
| [TSE → INSS (prova de vida)](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/comparecimento-a-votacao-nas-eleicoes-2026-pode-ser-utilizado-como-prova-de-vida-do-inss) | acesso institucional | informação individual de comparecimento para evento de prova de vida | sim, sob autorização |

**Resultado:** não foi localizada API pública comprovada para CPF/título → comparecimento em 25/10/2026. APIs públicas em repositórios do GitHub não conferem acesso a bases internas. Não usar segredos vazados, endpoints privados ou contornar autenticação.

## O que a auditoria pode executar com acesso público

O script obitos_comparecimento_piloto.py confronta, por seção/turno, as quantidades de aptos, comparecimento e abstenção dos BU web com o detalhe da apuração do TSE.

**Limite:** consistência de quantitativos agregados jamais prova nem descarta voto atribuído a pessoa falecida, pois não contém identidade dos eleitores.

## Cruzamento nominal que a Justiça Eleitoral pode realizar sob controle

1. Inscrições com óbito efetivo anterior a 25/10/2026 e data de comunicação (Infodip, INSS ou SIRC), após resolução de CPF e homônimos.
2. Histórico cadastral, cancelamento FASE 019, impedimentos e geração dos cadernos da respectiva seção.
3. Registro individual de comparecimento no segundo turno, com tratamento separado de justificativas.
4. Casos coincidentes: habilitação (biometria ou manual), ocorrência, caderno e ata. Revisão humana e cadeia de custódia.

## Perguntas precisas ao TSE: dados preexistentes ou procedimento autorizado

- Há relatórios/rotinas preexistentes que batam óbitos confirmados anteriores a 25/10/2026 com comparecimento individual do segundo turno? Disponibilizar metodologia, datas de atualização e contagem nacional/UF, **sem CPF ou nomes**.
- Quantas inscrições com óbito anterior ao pleito tiveram comparecimento registrado? Dessas, quantas coincidiram por identificadores confiáveis, quantas foram descartadas como erro e quantas permaneceram sem explicação?
- Entre ocorrências validadas, quantas envolveram biometria ou habilitação manual? Há atas e diligências que expliquem o evento?
- Como são tratadas as comunicações tardias no Infodip após a geração do caderno?
- Existe fluxo para auditoria independente controlada em ambiente TRE/TSE, sem extração de dados identificáveis?

A solicitação deverá priorizar documentos e dados preexistentes e indicar inexistência quando aplicável. Resultados com pequenas contagens podem exigir supressão para prevenir reidentificação.

## Fontes de referência

- [Justiça Eleitoral, procedimentos Infodip e impedimentos (atualização 03/11/2026)](https://www.justicaeleitoral.jus.br/fato-ou-boato/checagens/2026/voto-espirita-e-falso-que-mesarios-votaram-no-lugar-de-eleitores-mortos-ou-ausentes-apos-as-17h)
- [TSE, integração de comparecimento com INSS](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/comparecimento-a-votacao-nas-eleicoes-2026-pode-ser-utilizado-como-prova-de-vida-do-inss)
- [TSE, Resolução 22.166/2006 sobre cruzamento de óbitos INSS](https://www.tse.jus.br/legislacao/compilada/res/2006/resolucao-no-22-166-de-9-de-marco-de-2006)
- [TSE, comparecimento e abstenção 2026](https://dadosabertos.tse.jus.br/dataset/comparecimento-e-abstencao-2026)
- [Registro Civil, API com autenticação](https://api.hml.barramento.registrocivil.org.br/docs/)

**Política de divulgação:** nenhum número de “pessoas falecidas que votaram” será publicado sem validação individual por órgão competente e revisão de falsos positivos.
