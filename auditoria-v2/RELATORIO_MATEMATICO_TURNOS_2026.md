# Auditoria matemática 2026: variação dos votos entre turnos

**Execução:** 05/11/2026. **Fonte primária:** 56 arquivos nacionais e territoriais EA20 publicados pelo TSE, eleição presidencial 1º turno (código 6257, 04/10/2026) e 2º turno (código 6258, 25/10/2026). 27 UFs e exterior (ZZ), mais os dois arquivos BR de referência. **Resultado da execução:** SUCESSO, sem erros de invariantes ou de soma UF→BR.

**Código reproduzível:** [analise_matematica_turnos_2026.py](./analise_matematica_turnos_2026.py); [GitHub Actions](https://github.com/thayanneoliveira/Fatovia/actions/runs/42035906009). Os arquivos JSON do artefato registram os SHA-256 de todas as respostas originais, URLs e numeradores/denominadores. Este relatório não inclui dados pessoais.

## 1. Dois balanços contábeis que fecham exatamente

| Indicador | 1º turno | 2º turno | Variação |
| --- | ---: | ---: | ---: |
| Comparecimento | 125.275.835 | 128.236.074 | +2.960.239 |
| Votos válidos | 119.300.788 | 124.082.273 | +4.781.485 |
| Brancos | 2.300.798 | 1.430.496 | -870.302 |
| Nulos totais | 3.674.249 | 2.723.305 | -950.944 |
| Brancos + nulos | 5.975.047 | 4.153.801 | -1.821.246 |
| Lula | 53.879.538 | 64.256.232 | +10.376.694 |
| Flávio | 56.104.503 | 59.826.041 | +3.721.538 |
| Demais candidatos | 9.316.747 | 0 | -9.316.747 |

- **Identidade 1**: delta de válidos = delta do comparecimento - delta de brancos/nulos = 2.960.239 - (-1.821.246) = **4.781.485**.
- **Identidade 2**: ganho absoluto dos finalistas = votos nos outros candidatos no 1º turno + delta de válidos = 9.316.747 + 4.781.485 = **14.098.232**.
- **Hipótese não identificável**: não é possível inferir a origem individual dos votos de Lula, Flávio, branco/nulo ou abstenção por margem de votos.

## 2. Outra identidade que explica por que as correlações parecem fortes

Para cada UF, medindo participações em porcentagens dos votos válidos:
1T: pL1 + pF1 + pOutros1 = 100.
2T: pL2 + pF2 = 100.
Logo: **(pL2-pL1) + (pF2-pF1) = pOutros1**.

Isto cria uma associação matemática entre a participação dos outros candidatos no 1º turno e os ganhos de participação dos dois finalistas, independentemente de identificarmos transferências individuais.

Nas 28 unidades (Pearson sem ponderação, descritivo):
- r(outros1 em % válidos, aumento da participação percentual de Lula) = **+0,79922**.
- r(outros1 em % válidos, aumento da participação percentual de Flávio) = **+0,89376**.
- r(variação de participação/comparecimento pp, aumento de participação de Lula pp) = **+0,25427**.

Essas correlações **não estimam transferência de votos** e não têm interpretação causal. A relação entre as duas variações de participação e os outros candidatos é, em larga medida, imposta pela identidade composicional.

## 3. Heterogeneidade territorial

- **9 UFs** tiveram redução líquida de comparecimento do primeiro para o segundo turno: AC, AM, AP, MA, PA, PI, RO, RR e TO.
- No Acre: comparecimento -34.676, brancos+nulos +2.162, votos válidos -36.838. Lula +9.743, Flávio -15.092 e outros candidatos tinham 31.489 votos no 1º turno. Confere: 9.743 - 15.092 - 31.489 = -36.838.
- Em São Paulo: comparecimento +932.397, brancos+nulos -443.107, válidos +1.375.504.
- Cinco UFs tiveram aumento de brancos+nulos (AC, AM, DF, ES, TO), contrapondo a redução líquida nacional.

## 4. Eleitorado total e universo das seções instaladas

No arquivo nacional do TSE para 2º turno:
- eleitores aptos contabilizados no arquivo: 158.745.502;
- eleitores em seções instaladas: 158.745.079;
- diferença: 423 (campo esni do JSON oficial);
- comparecimento + abstenção = 128.236.074 + 30.509.005 = 158.745.079.

O [portal de dados abertos do TSE](https://dadosabertos.tse.jus.br/dataset/resultados-2026) adverte ainda que 39 registros de transferência temporária ficaram duplicados entre origem e destino no total cadastral, logo o total efetivo de pessoas aptas é 158.745.463, e não 158.745.502. A diferença remanescente de 384 entre total efetivo e registros de seções instaladas demanda classificação pelo inventário de seções; não deve ser chamada de voto irregular.

## 5. Limites e próximos testes

- Nenhum voto individual foi rastreado ou associado a uma pessoa falecida; BU e EA20 são totalizadores agregados.
- A variação líquida de comparecimento de 2.960.239 não significa que apenas 2.960.239 pessoas novas participaram do 2º turno; pode haver pessoas que compareceram no 1º e faltaram no 2º, compensadas por outras no sentido oposto.
- Até mesmo os limites contábeis do fluxo "outros candidatos do 1º turno → Lula no 2º turno" são **0 a 9.316.747**, diante dos totais nacionais sem vínculo individual. Ambos os extremos são matematicamente possíveis, pois o eleitorado fora desse grupo é maior que o total de votos finais de Lula.
- Próxima etapa: estudar padrões regionais em dados por zona/seção, confundir menos contagem com inferência causal, comparar seções com fluxos de voto em trânsito, e combinar evidências externas independentes. Não transformar correlação espacial em alegação de fraude.

**Status científico:** contas consistentes, origem dos votos não identificada, nenhuma inferência de fraude a partir desta análise.
