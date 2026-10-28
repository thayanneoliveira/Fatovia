# FATOVIA AUDITA | Presidente, 2º turno 2026

## Implementação

Mecanismo **separado do motor editorial** que utiliza apenas dados oficiais publicados pelo TSE, sem tokens da Meta, modelos de linguagem ou dependências externas.

1. Descobre no catálogo CKAN os 28 pacotes de Boletim de Urna do segundo turno (27 UFs + exterior ZZ).
2. Baixa cada ZIP via HTTPS e confere seu SHA-512 contra o arquivo oficial de checksum.
3. Lê o CSV sem extração integral; filtra NR_TURNO=2 e cargo Presidente.
4. Reconta votos por UF, município, zona, seção e número do votável. Sinaliza duplicatas, votos que não correspondem ao comparecimento e erros de formato.
5. Soma totais por UF e nacionalmente.
6. Consulta a outra base do TSE, "Presidente - Votação por seção eleitoral - 2026", para comparar totais por UF e número.
7. Publica relatório Markdown e JSON com URLs de origem, hashes e ocorrências.

**Limites:** duas bases do próprio TSE. A conferência entre elas não prova autenticidade dos BUs impressos, ausência de fraude, intenção individual de voto, cadeia de custódia, nem segurança do sistema de votação.

## Resultados possíveis

- **CONFERENCIA_CONSISTENTE**: 28 UFs, SHA512 válido em todas, nenhuma inconsistência por seção, todos os totais compatíveis com a outra base.
- **DIVERGENCIAS_DE_TOTALIZACAO**: bases completas e hashes conferidos, mas diferenças entre conjuntos, exigindo investigação.
- **INCONCLUSIVO**: arquivo ou UF ausente, erro de integridade, duplicidade, soma incompatível, referência ausente ou falha técnica.

O programa nunca infere fraude automaticamente.

## Executar

1. Acesse [GitHub Actions, auditoria 2026](https://github.com/thayanneoliveira/Fatovia/actions/workflows/auditoria-2t-2026.yml).
2. Selecione **Run workflow** na branch main.
3. O workflow analisa no máximo 3 estados em paralelo, consolida o país e publica JSON e Markdown em docs/auditoria.

O workflow é **manual inicialmente**. Para evitar grandes gastos de tráfego e de minutos, não há agendamento automático. Os ZIPs ficam apenas no armazenamento temporário de cada execução; o repositório recebe somente relatórios compactos. As franquias do GitHub e o acesso ao TSE podem limitar a execução.

Após a primeira execução, arquivos públicos esperados:

- docs/auditoria/2026-2t-presidente.md
- docs/auditoria/2026-2t-presidente.json

## Rodar localmente (Python 3.12+)

~~~bash
python -m unittest discover -s tests -p 'test_auditoria.py' -v
python -m auditoria catalogo
python -m auditoria uf --uf MA --out work/states/MA.json
python -m auditoria consolidar --states work/states --out work/report
~~~

**Atenção:** consolidar exige 28 resultados estaduais. Só o MA produz um relatório INCONCLUSIVO.

As saídas discriminam números dos votáveis, inclusive brancos e nulos quando presentes. Não tratam todos os números como votos válidos.

## Próxima etapa de auditoria externa

- Validar o esquema 2026 com uma primeira execução real. Testes sintéticos não provam a compatibilidade com o formato atualizado.
- Fazer amostragem de BUs impressos fotografados por observadores independentes, com origem e metodologia documentadas.
- Conferir assinaturas/QR Codes e analisar eventuais seções anuladas, agregadas ou com apuração especial.
- Os RDVs, logs, assinaturas individuais e o software da urna **não** são analisados nesta versão.

Fontes: https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna e https://dadosabertos.tse.jus.br/dataset/resultados-2026
