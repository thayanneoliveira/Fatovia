# FatoVia | Auditoria cruzada de coerência eleitoral 2026

**Escopo:** eleição presidencial, primeiro e segundo turnos de 2026. Piloto inicial: Acre (AC). **Apenas dados públicos, sem dados identificáveis de eleitores.**

## 1. Objetivo e inferências permitidas

Cruzar informações registradas para a mesma UF/município/zona/seção e cargo, distinguindo:
- concordância documental (números iguais sob a mesma definição);
- diferença entre universos/snapshots (a reconciliar);
- ausência/insuficiência de dados (bloqueio da conclusão);
- alegação individual de pessoa falecida (não testável com dados públicos).

**Atenção:** votos computados, presença, eleitorado apto e boletins têm definições diferentes. Voto em trânsito, agregação de seções, cargos com votação distinta, cédulas em contingência e geração em datas diferentes podem explicar diferenças.

## 2. Mapa dos controles

| Código | Hipótese falsificável | Fonte primária | Chave e tipo de confronto | Estado |
| --- | --- | --- | --- | --- |
| C01 | BU web 2º turno vs detalhe de apuração 2º turno | TSE (BU web + detalhe votação seção 2026) | UF/mun/zona/seção, presidente, aptos/comparecimento/abstenções; diferenças e ausências | piloto AC iniciado, resultado não homologado |
| C02 | Dados ELO vs soma de seção | TSE ELO 2026 e detalhe de apuração | UF/mun/zona/turno, aptos/comparecimento/abstenções | piloto AC iniciado, resultado não homologado |
| C03 | Perfil de eleitorado pré-eleição × eleitorado de BU | TSE perfil eleitorado seção 2026 + BU | UF/mun/zona/seção; aptos e cobertura biométrica agregada, com cautela por datas | piloto AC iniciado, resultado não homologado |
| C04 | Primeiro turno × segundo turno | TSE detalhe votação seção 2026 | mesma seção/cargo, aptos e comparecimento; não pressupõe estabilidade | piloto AC iniciado, resultado não homologado |
| C05 | Reconciliação FatoVia × auditoria terceira | Repositórios FatoVia + DataUrnas-BR | 28 unidades, número de seções por UF | **concluído: 0 diferenças entre 28 contagens de seção** |
| C06 | RDV digital × BU da mesma seção | pacote TSE, decodificador ASN.1 e assinaturas | recontagem de votos por cargo em seção | **ainda não reproduzido pelo FatoVia**, terceiro relata 0 divergências nas 499.205 seções com RDV disponível |
| C07 | Eventos de habilitação/voto × BU × log de contingência | logs de urna e BUs oficiais | urna/seção e cronologia | pendente de execução FatoVia |
| C08 | Óbito anterior × comparecimento individual | SIRC/Infodip/INSS e ELO sob controle institucional | inscrição com identidades validadas | depende de TSE/TRE; minuta complementar pronta e NÃO protocolada |

## 3. Código e evidências

- Validador principal: [auditar_coerencia_2026.py](./auditar_coerencia_2026.py)
- Testes sintéticos: [tests/test_coerencia.py](./tests/test_coerencia.py)
- Execução [GitHub Actions C01–C04](https://github.com/thayanneoliveira/Fatovia/actions/runs/41865253168) (verificar estado atual; não pressupor sucesso).
- Diagnóstico de falso positivo decorrente de comparar dois cargos diferentes no BU: [script corrigido](./obitos_comparecimento_piloto.py), execução [41864536931](https://github.com/thayanneoliveira/Fatovia/actions/runs/41864536931).
- [Resultado C05 em JSON](./CONFRONTO_EXTERNO_SECOES_2026.json), inclui hash de versões dos arquivos de resultado usados.
- [Minuta de pedido institucional ao TSE](./MINUTA_COMPLEMENTAR_TSE_OBITOS_COMPARECIMENTO_2026.md), não enviada.

## 4. Fontes oficiais e qualidade

- BU web do segundo turno: recurso do TSE com hash SHA-512 de referência.
- Detalhe da votação por seção 2026: arquivo nacional, coluna de cargo filtrada para Presidente.
- Comparecimento e Abstenção 2026: sistema ELO, perfil por município/zona e características (não por eleitor nominal).
- Perfil eleitorado por seção 2026: fotografia cadastral anterior ao pleito, com biometria agregada.
- RDV e log: arquivos transmitidos para totalização, com limite de cobertura a registros em situação Totalizado.

Todos têm origem institucional no TSE, ainda que subsistemas distintos. Não são evidência física independente.

## 5. Régua de publicação responsável

Só divulgar contagens de diferenças para C01–C04 após CI completar e manifesto ter status COMPLETE_FOR_PUBLIC_AGGREGATE_RECONCILIATION. Se houver falha de download, campo ausente, chave conflitante ou dado incompleto, publicar o bloqueio, **não** publicar zero divergências. Não utilizar número de seções como denominador de cidadãos, nem classificar diferença estatística como fraude.

Nenhum CPF, nome, número de título ou histórico nominal de comparecimento deve ser coletado ou colocado no repositório público.

**Definição de bom o suficiente:** piloto AC reprodutível e com proveniência, verificação de cobertura e erros bloqueantes antes de escalar para todas as UFs. A etapa individual de óbitos só poderá ser tratada como concluída com acesso autorizado e revisão de falsos positivos.
