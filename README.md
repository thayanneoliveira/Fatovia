# FatoVia | Motor editorial e publicador de Instagram (fases 1 e 2)

> **Estado: radar ativo, hospedagem JPEG testada por HTTP e publicador Meta implementado e testado com simulações. Publicação real no Instagram DESATIVADA até autorizar as credenciais.**

## Integração com Instagram (código implantado)

- [Configuração obrigatória de Meta e GitHub](INSTAGRAM_SETUP.md)
- [Workflow de publicação agendada](.github/workflows/publish.yml)
- [Testes automatizados de segurança e idempotência](tests/test_publisher.py)
- [Validação da URL pública do JPEG](https://thayanneoliveira.github.io/Fatovia/media/healthcheck.jpg)

O envio foi desenvolvido para utilizar a **Instagram API com Instagram Login** (`graph.instagram.com`, ou Facebook Login mediante configuração), validar o perfil `@fato.via`, criar carrosséis de 7 imagens e confirmar cada publicação.

**A publicação real ainda NÃO foi testada nem autorizada:** é necessário obter o token e o IG ID pelo fluxo oficial da Meta, registrá-los com segurança no GitHub e habilitar `IG_PUBLISH_ENABLED`. A conexão Windsor.ai disponível dentro do ChatGPT não fornece esse token automaticamente.

O publicador usa o limite conservador de 2 posts por dia e escolhe janelas automaticamente quando há métricas suficientes. Em erros de resposta ambígua, ele interrompe reenvios, guarda a transação e verifica se o post já existe.

## O que está funcionando

- Workflow do GitHub Actions: varreduras às 02h17, 08h17, 14h17 e 20h17 (America/Fortaleza), sujeitas a atrasos do GitHub.
- Fonte inicial: dados abertos da Câmara dos Deputados, com ementa e registro de tramitação.
- Classificação e seleção por assunto, fonte, novidade e diversidade editorial, sem ranqueamento de candidaturas.
- Memória anti-repetição por ID, versão da tramitação e resumo; histórico dos **3 posts do @fato.via** importado.
- Geração de **7 imagens JPEG 1080×1350** em verde profundo e creme, armazenadas em `docs/media/` quando houver pauta aprovada.
- Até 8 itens na fila; cada varredura prepara no máximo 2 pautas.
- Métricas opcionais da API Meta, com parâmetros conservadores na ausência de dados.
- Testes automatizados antes de cada varredura e relatório em `data/last_report.json`.
- Sincronização segura dos commits para evitar perda de atualizações por concorrência.

**Importante:** apenas a seleção documental e a produção mecânica estão implementadas. Não há ainda análise multiponte, geração por LLM, site público, publicação nem retroalimentação efetiva sem dados de métricas.

## Executar

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m fatovia report
python -m fatovia scan
python -m fatovia demo
python -m fatovia metrics
```

O comando `demo` cria arquivos de teste fictícios em `demo/cards` (não destinados ao Instagram). O comando `scan` requer acesso à API da Câmara.

## Automação agendada

Workflow: [FatoVia | Radar documental seguro](.github/workflows/editorial.yml).

No GitHub, abra **Actions**, selecione o workflow e use **Run workflow** para executar fora do agendamento.

As imagens não aparecem se nenhum assunto passar nos filtros. Isso é uma decisão intencional: não se inventam pautas para completar a meta de posts.

## Métricas (inativas até configurar)

A coleta opcional usa a API oficial Meta. Para habilitar, é necessária credencial válida em **Settings > Secrets and variables > Actions**:

- Secret: `META_ACCESS_TOKEN` obtido por fluxo oficial do seu app Meta, com permissões de leitura adequadas.
- Variable: `METRICS_ENABLED=true`.

Nunca cole o token em arquivos, issues ou conversas. A integração Windsor.ai existente no ChatGPT não transfere automaticamente credenciais para o GitHub.

## Infraestrutura de mídias públicas (fase 2)

O repositório já é público. O projeto tem um segundo workflow [FatoVia | Hospedagem pública de imagens](.github/workflows/pages.yml). Ele só publica os arquivos de `docs/`, inclusive os JPEGs. **O GitHub Pages foi ativado e o deploy personalizado passou na execução de 25/10/2026.**

**Deploy comprovado pelo GitHub Actions:** [execução bem-sucedida](https://github.com/thayanneoliveira/Fatovia/actions/runs/40246733658). O pacote contém `media/healthcheck.jpg`, `manifest.json` e `deployment-verification.txt`. URL pública publicada: https://thayanneoliveira.github.io/Fatovia/. O teste HTTP direto a partir do assistente ainda não foi possível e requer validação de cliente. O arquivo `docs/media/healthcheck.jpg` é apenas teste técnico, não pode ser publicado como post.

A página tem um catálogo `docs/manifest.json` atualizado pelo motor para facilitar inspeção e testes. Ter imagens visíveis por URL **não ativa nem autoriza** publicação no Instagram.

## Próxima fase, ainda não executada

1. Estender radar a outras fontes oficiais e monitorar alterações de propostas antigas.
2. Implantar etapa de investigação com verificações e fontes cruzadas.
3. Confirmar que o Pages publicou o JPEG de teste via HTTP.
4. Validar o primeiro post real usando credenciais da Meta (integração implementada; primeira publicação pendente).
5. Ativar aprendizado de horários e frequência com amostra suficiente.
6. Alertas, auditoria de qualidade e mecanismos de suspensão segura.

## Visibilidade e custo

O repositório está **público**. Isso permite habilitar GitHub Pages no GitHub Free; lembre que o código, a memória de pautas e os arquivos versionados ficam públicos. Nunca armazene tokens ou dados sensíveis no repositório.

Os workflows privados podem consumir a franquia gratuita de minutos do GitHub Actions. Consulte seu limite antes de elevar a frequência.

## Regras permanentes

- Sem fonte confiável, **não há postagem**.
- Proposição não equivale a lei nem comprova resultado.
- Não recomendar votos nem ranquear candidaturas.
- Impedir repetição sem mudança material, e manter rastreabilidade.
- Sem autorização expressa e infraestrutura validada, **não publicar externamente**.
- Credenciais nunca devem ser versionadas.
