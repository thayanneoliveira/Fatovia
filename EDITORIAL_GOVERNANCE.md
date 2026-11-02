# FatoVia | Padrão visual e gate editorial (02/11/2026)

## Padrão de marca verificado

Referências: capas anteriores do perfil @fato.via publicadas em 26 a 29/10/2026,
como "Fim da 6x1", "Lula quer regular as redes", "Ganhou. E agora?" e "Energia limpa".
Inspeção da paleta das capas via dados de mídia da conta no Instagram.

- Cor de fundo dominante: **#123E31** (verde profundo), aproximadamente 68% a 75% das capas históricas inspecionadas.
- Título: **serifado editorial**, creme **#F5F1E7**, com destaques verde claro **#B5D39F**.
- Textos explicativos e labels: sans-serif, creme e apoio verde claro.
- Barra/cabeçalho: marca **FATOVIA**, linha editorial, categoria e paginação.
- Proporção: **4:5**, JPEG 1080 × 1350 para feed e carrossel.
- Contraste alto e texto legível; cada card deve apresentar ideia clara sem excesso de elementos.

**Rejeitar capas claras como identidade primária**. O formato anterior publicado em
02/11/2026 com fundo #F5F1E6 ocupando cerca de 72% da área foi identificado como
um desvio da identidade do perfil. O renderer principal foi corrigido e existe teste
de regressão em `tests/test_brand.py`.

## Gate pré-publicação obrigatório

1. Confirmar conta de destino como `fato.via` via dado vivo do Instagram, não só o
   nome armazenado pelo conector.
2. Consultar insights recentes (alcance, visualizações, salvamentos, compartilhamentos,
   engajamento por publicação) e histórico de posts antes de selecionar temas.
3. Se a amostra for insuficiente, registrar explicitamente o uso de hipóteses editoriais.
   Não chamar essas hipóteses de temas vencedores nem alegar otimização estatística.
4. Verificar se o assunto e os fatos são atuais e documentados com fontes confiáveis.
   Distinguir proposta, lei, execução, impacto e hipóteses.
5. Comparar as capas finais com pelo menos três capas históricas reais do perfil e
   verificar fundo verde, tipografia, espaçamento e paginação.
6. Executar testes de geração e abrir amostra visual das artes finais antes de publicar.
7. Conferir URL JPEG pública, ordem dos sete cards, legenda, fontes, duplicidade e limites.
8. Publicar somente após os gates acima e obter confirmação do Instagram, registrando
   media_id/permalink e os dados da decisão.
9. Quando um erro editorial for detectado após a publicação, não republicar automaticamente:
   corrigir arquivos, documentar causa e decidir com a pessoa responsável o que fazer com
   a postagem existente.

## Primeiro retrato dos insights (02/11/2026)

- Conta: 4 seguidores; 14 publicações após o lote de 3 carrosséis.
- Publicações anteriores: alcance por postagem de 1 a 5 contas, visualizações de 3 a 34,
  apenas 1 curtida e zero salvamentos e compartilhamentos nos resultados consultados.
- Isso **não** permite inferir horário, assunto ou formato ideal.
- Usar métricas como observação inicial, continuar testes e evitar declarar crescimento,
  viralização ou padrão vencedor sem dados.

## Desvio registrado em 02/11/2026

Três carrosséis foram publicados pela integração Windsor.ai sem consulta prévia a insights
e sem checagem visual do histórico. A decisão utilizou apenas relevância editorial,
e a capa foi gerada pelo template antigo, dominado por creme.
Posteriormente, foram consultados insights da conta e comparadas as capas antigas,
constatando-se divergência visual. Os três posts já publicados não podem ter suas
imagens substituídas no próprio carrossel por meio da integração disponível.
Novas versões foram renderizadas, mas não foram republicadas nem os originais apagados.
