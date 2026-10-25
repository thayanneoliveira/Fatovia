# FatoVia | Motor editorial autônomo

Projeto de monitoramento documental de políticas públicas, com fontes oficiais, histórico de publicações, prevenção de repetição e produção automática de carrosséis.

**Estado inicial: modo seguro. A publicação no Instagram não está ativada.**

## Fases

1. **Radar:** consultar propostas e tramitações em fonte oficial, salvar pautas novas.
2. **Produção:** criar 7 JPEGs no formato 1080×1350 e legenda com rastreabilidade.
3. **Memória:** manter IDs, versões e 3 posts históricos já publicados no @fato.via.
4. **Aprendizado:** comparar métricas, desde que a coleta esteja conectada e haja amostra.
5. **Distribuição:** habilitar hospedagem pública e API Meta após testes ponta a ponta e revisão de segurança.

## Executar
```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m fatovia report
python -m fatovia scan
```

## Segurança
- Dados oficiais não equivalem a comprovação de viabilidade ou implementação.
- Nada é publicado automaticamente no Instagram nesta versão.
- Conteúdo sem fonte verificável não entra na fila.
- O sistema não ranqueia candidatos nem recomenda voto.
- Sem fontes válidas, gera relatório e não inventa publicações.
- Credenciais nunca devem ser armazenadas em arquivos versionados.

## Atenção: repositório privado
O GitHub Pages gratuito pode não estar disponível neste repositório privado. Não altere a visibilidade sem avaliar o impacto. Hospedagem das imagens será configurada separadamente.

Este repositório será aprimorado gradualmente, começando pelo teste do radar e das imagens.