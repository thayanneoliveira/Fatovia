# Algenib — homologacao em laboratorio

Aprovacao de voz: 26/11/2026. O modelo candidato e gemini-3.8-flash-tts, ainda nao comprovado como o modelo exato usado no AI Studio. Usar somente projeto dedicado Free Tier sem faturamento associado. A variavel de verificacao e uma atestacao operacional, nao uma consulta de billing: nao protege se o projeto for posteriormente convertido em pago. O operador deve verificar no AI Studio antes de habilitar e manter faturamento desligado. Nao usar chaves de projetos pagos.

Referencia: https://ai.google.dev/gemini-api/docs/speech-generation e https://ai.google.dev/gemini-api/docs/pricing .

## Ensaio real, separado de CI e publicacao

1. Confirmar modelo no AI Studio, projeto Free Tier e ausencia de billing.
2. Criar chave do projeto dedicado e guardar em secret FATOVIA_GEMINI_API_KEY. Nao incluir em commit, log ou chat.
3. Somente depois, setar FATOVIA_GEMINI_FREE_TIER_VERIFIED=true no ambiente de teste e executar:
   python -m fatovia.narration --script /tmp/script.txt --cache /tmp/fatovia-tts-private
4. Ouvir WAV e comparar ao piloto aprovado. Validar transcricao integral, qualidade, sotaque e ritmo. Nao publicar.
5. Integrar ao gerador audiovisual V5, validar de ponta a ponta, vincular hashes, preservar revisoes e gates. Somente entao marcar api_homologated e homologacao V5.
6. Em falha de quota ou credencial, adiar o Reel; nao substituir voz nem bloquear carrosseis. Sem retries automaticos nesta etapa.

CI usa exclusivamente mocks, sem chave e sem chamadas externas. O adaptador nao e ainda um renderizador V5 autonomo, nem a verificacao de WAV garante fidelidade da transcricao. A branch nao habilita publicacao nem altera main.
