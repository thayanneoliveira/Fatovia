# FatoVia | Conectar a API oficial do Instagram

**Estado atual:** código do publicador instalado, testes locais automatizados no GitHub aprovados, JPEG público verificado. **O envio real está desabilitado por padrão.**

## Como as peças se conectam

1. O radar cria pautas documentais em `data/state.json` e gera sete JPEGs em `docs/media/`.
2. O workflow de hospedagem publica os arquivos em `https://thayanneoliveira.github.io/Fatovia/media/`.
3. O workflow [Publicacao Instagram controlada](.github/workflows/publish.yml) consulta a memória nos horários elegíveis.
4. A API Meta verifica a conta, cria sete contêineres, monta um carrossel e publica.
5. Uma transação é registrada **antes** da primeira chamada de publicação. No retorno, grava o ID do Instagram. Se uma operação falhar sem resposta conclusiva, só realiza conciliação, nunca reenvio cego.

## Passo obrigatório 1: gerar credenciais pela Meta

A conexão do Instagram via Windsor.ai no ChatGPT **não entrega uma credencial reutilizável ao GitHub**.

Use o [Meta for Developers](https://developers.facebook.com/apps/) para habilitar a **Instagram API with Instagram Login** no aplicativo que você controlar. A conta @fato.via precisa estar em modalidade profissional, e a autorização precisa incluir `instagram_business_basic` e `instagram_business_content_publish`. Se desejar ler métricas, avalie também `instagram_business_manage_insights`.

O modo alternativo, **Instagram API with Facebook Login**, exige conta profissional vinculada a uma Página e permissões como `instagram_basic`, `instagram_content_publish` e `pages_read_engagement`. Nesse caso configure o host `graph.facebook.com`. Os dois fluxos têm formatos distintos de autorização; escolha apenas um.

**Obtenha um access token válido autorizado para a própria conta @fato.via.** Também obtenha o ID do usuário profissional retornado pelo fluxo de autorização. O sistema verifica se o ID e o nome da conta coincidem antes de fazer qualquer POST.

**Nunca inclua tokens ou senhas neste repositório público, em issues, prints ou conversas.**

## Passo obrigatório 2: cadastrar segredo e variáveis no GitHub

Abra [Secrets and variables → Actions](https://github.com/thayanneoliveira/Fatovia/settings/secrets/actions).

Na aba **Secrets**, crie:

- `META_ACCESS_TOKEN`: token de acesso válido obtido pela Meta (não no ChatGPT).

Na aba **Variables**, crie:

- `META_IG_USER_ID`: identificador da conta Instagram profissional autorizada.
- `META_API_HOST`: `graph.instagram.com` para Instagram Login, ou `graph.facebook.com` para Facebook Login (opcional: assume o primeiro).
- `METRICS_ENABLED`: `true` somente se o token tiver permissão de métricas e a coleta estiver configurada.
- `IG_PUBLISH_ENABLED`: deixe `false` durante a validação de credenciais e o teste de acesso.

**Ative `IG_PUBLISH_ENABLED=true` somente depois de confirmar que a integração está autorizada e que deseja iniciar os envios reais.** Esse valor é um controle externo, portanto não precisa alterar código.

## Frequência e regras editoriais

O workflow verifica a fila **uma vez por hora entre 08h e 22h**, no fuso America/Fortaleza, sujeito aos atrasos do GitHub Actions.

O algoritmo, atualmente:
- considera o limite inicial de **até 2 posts por dia**, podendo ajustar com amostra de métricas;
- usa janelas iniciais de **09h e 19h**;
- exige pelo menos quatro horas entre posts;
- exige 7 JPEGs disponíveis, fonte governamental identificável, ementa verificável e documento relativamente recente;
- não publica sem pauta elegível;
- não envia nos dias de bloqueio registrados em `data/state.json`;
- recusa automaticamente textos marcados por alguns termos de alegações graves;
- limita a execução a **um carrossel por tentativa**, nunca sete posts separados.

Os filtros automáticos ainda **não substituem checagem humana nem asseguram precisão editorial**. Não considere a publicação em produção segura para alegações contestadas sem mecanismos adicionais de revisão e correção.

## Comandos de diagnóstico

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m fatovia.publisher status    # seguro, não faz POST
python -m fatovia.publisher probe     # verifica HTTPS e JPEG público sem Meta
python -m fatovia.publisher prepare   # só reserva pauta quando estiver habilitado e for o horário
```

Os comandos `deliver` e `reconcile` são usados pelo GitHub Actions. **Não execute `deliver` manualmente com credenciais reais** antes de entender o impacto.

Logs: [Actions](https://github.com/thayanneoliveira/Fatovia/actions).

## Recuperação

Em caso de timeout ou resultado incerto, a transação permanece registrada. O ciclo seguinte procura no Instagram pelo identificador editorial da legenda. Se encontrar, atualiza a memória; se não encontrar, mantém a operação bloqueada para aquela transação, evitando publicações repetidas.

Uma correção manual de `data/state.json` pode ser necessária para destravar falhas ambíguas. Não delete a transação em aberto sem conferir antes se o conteúdo já está publicado na conta.

## Limitações conhecidas

- Não há token da Meta cadastrado pelo assistente. Segredos exigem uma ação sua na interface do GitHub.
- A renovação automática do token ainda não foi implementada; credenciais expiradas impedirão novas publicações.
- O radar ainda utiliza principalmente os dados abertos da Câmara, não investigação ampla de fontes cruzadas.
- As métricas da conta podem demorar a chegar e são insuficientes para otimização confiável no começo.
- O workflow não agenda publicação exata ao minuto, pois o GitHub Actions pode atrasar.
- Não há garantia de postagem automática em dias sem material adequado.
- O mecanismo ainda não foi testado com uma publicação real pela API oficial; apenas testes com simulações e a hospedagem JPEG foram verificados.

## Documentação

- [Instagram Platform - Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)
- [Instagram Platform - Overview](https://developers.facebook.com/docs/instagram-platform/overview)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
