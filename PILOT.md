# Piloto documental FatoVia

Preparado em 14/11/2026. A ativação administrativa foi confirmada em [43639888649](https://github.com/thayanneoliveira/Fatovia/actions/runs/43639888649); o relatório inicial do piloto registra zero publicações. O gate externo continua obrigatório. Este documento não concede autorização adicional.

- Janela proposta: 15 a 21/11/2026 (horário de Brasília).
- Máximo: quatro carrosséis no total, dois por dia, janelas das 09h e 17h.
- Somente os oito itens auditados no preflight 43639559303, por identidade, versão e hashes.
- Gate IG_PUBLISH_ENABLED continua obrigatório. Nenhum LLM livre ou dossiê fora do escopo.
- Revalidar parecer fresco, origem, arquivos locais e hospedados antes de qualquer POST.
- Reconciliar transação ambígua sem repetir POST.
- Encerramento automático por tempo ou quantidade; não muda automaticamente para quatro posts diários.
- Para interromper: definir IG_PUBLISH_ENABLED=false. Uma chamada já em curso não é cancelada por esta alteração.
- Antes de ativar, verificar a execução dos testes e a existência de histórico consistente. Após o piloto, avaliar qualidade e métricas; não inferir tendências a partir de quatro posts.

Segregação funcional, não segregação forte de identidade: o repositório público e seus mantenedores ainda podem modificar código e pareceres.

## Avaliação operacional

O workflow de inteligência coleta métricas em janelas [24h,31h) e [72h,79h) após cada publicação. O relatório `data/pilot_report.json` separa os posts registrados no piloto das publicações históricas, distingue janelas perdidas de métricas zero e indica transações que exigem atenção. Os registros são públicos no repositório. A avaliação não autoriza a próxima fase e quatro publicações não bastam para otimizar horários ou inferir efeitos causais.
