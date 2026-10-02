# Retomada — pesquisa de mercado

Atualizado em **02/10/2026**. **Etapas 1, 2a e 2b concluídas; as alterações foram organizadas em micro commits locais a pedido do usuário.** Próxima etapa é a 3a, ainda sem autorização. Etapa 1 tem limites de Docker/infraestrutura externa registrados abaixo; a etapa 2a foi validada sem entrar no fluxo de rotas de mercado, e a etapa 2b foi confirmada usando o Postgres do projeto.

**Branch de trabalho atual: `refactor/market-discovery`**, criada a pedido do usuário a partir de `feature/v2-async-prices`, em `80a6af7`. As etapas concluídas foram gravadas em commits locais; consulte `git log --oneline` para o HEAD atual e os hashes registrados em [progress.md](progress.md). Sem push, deploy ou provisão AWS.

## Leitura mínima e Git

1. Ler `AGENTS.md` e este arquivo.
2. Ler [plano](plan.md), especialmente a etapa autorizada, [contrato](api-contract.md) e último registro em [progresso](progress.md).
3. Conferir `git status --short`, `git branch --show-current` e `git log -5 --oneline`. Preservar alterações existentes; não fazer push/deploy.
4. Usar a v2 async existente como base. Os registros anteriores em `docs/continuidade-v2-async-prices.md` são históricos e apontam para este trabalho.

Base desta etapa: branch `feature/v2-async-prices`; HEAD `80a6af7`, `docs(readme): present portfolio workflows and contribution guide`. Git estava limpo antes do planejamento. A v2 já está nos commits `7c0d35e` (brapi), `4500ecb` (cache), `bcfd491` (metadados), `29a98dd` (carteira async), `9291f24` (avaliação v2) e `e791bdd` (CI/imagem). Não repetir o plano async nem tratar HEAD `fcfd48b` dos relatórios antigos como estado atual.

## Arquivos e estado ao encerrar a etapa 1 (registro histórico)

- Os quatro documentos deste diretório, preparados na etapa 0 e ainda novos para o Git, foram atualizados com resultado da etapa 1; `progress.md` conserva o histórico anterior.
- Configuração/runtime: `app/config.py`, `app/database.py`, `app/main.py`, `alembic/env.py`, `start.sh`, novo `release.sh`, `.env.example`, Dockerfile, Compose local/validação e novo `docker-compose.external.yml`, CI e `scripts/check_release.py`.
- Verificação: novos `tests/runtime/` e `scripts/test_postgres_tls.py`; fixture de `tests/prices/test_config.py` usa TLS local explicitamente desabilitado. Domínio, descoberta, cadastro, admin, dependências e arquivos de migrations preservados.
- README, `CONTRIBUTING.md` e `docs/operacao.md` alinhados a release/URL/TLS/health/testes locais. `.env`/`.env.test` pessoais preservados. Apontadores dos registros locais ignorados da v2 atualizados; relatórios anteriores preservados.
- Na ocasião, nenhum staging, commit, push, deploy, workflow AWS ativo ou recurso externo foi criado. Posteriormente, a pedido do usuário, as alterações concluídas foram commitadas localmente; dados/certificados dos ensaios ficaram somente em `/tmp` e os servidores de teste foram encerrados.

## Decisões e limites

- Gratuidade obrigatória nesta entrega; ações brasileiras e FIIs com brapi.
- Cripto foi considerada na brapi, mas a conta retornou **403** em listagem e cotação BTC. Usuário escolheu **adiar cripto até uma fonte gratuita**. Não trocar silenciosamente por CoinGecko nem assinar um plano.
- Implementar contratos pequenos de descoberta e cotações, registro explícito/capacidades e limites brapi compartilhados. Reutilizar HTTPX/lifespan/cache; domínio síncrono permanece independente de HTTP/ORM.
- Banco vazio deve permitir pesquisa; persistência ocorre apenas na primeira compra válida. Preço da operação, tipos/IDs antigos e contratos legados/v2 preservados.
- Ticker não tem constraint única: etapa 3a precede primeira compra e exige estratégia não destrutiva para duplicidades históricas. Não adivinhar moeda de cripto antiga.
- Etapas 2 e 3 divididas em 2a/2b e 3a/3b. Uma subetapa por conversa; não implementar ambas com a mesma autorização.
- AWS é preparação/documentação: sem recursos, IAM, deploy ou dados de produção. Não criar workflow de produção ativo.

## Verificações registradas

**364 testes aprovados em 35,47 s**, suíte completa com PostgreSQL **18.6** sintético, descartável e TLS obrigatório. URL/senha especial, precedência/redaction, pool, readiness, CA/hostname corretos/incorretos, migrations reais, concorrência, rollback e contratos legados/v2 verificados. **302 warnings existentes** de `python-jose`/`utcnow`. Snapshot OpenAPI não regenerado.

Runtime no-dev separado em `/tmp/fintrack-stage1-runtime`: API real antes da release não criou schema; depois `sh release.sh` migrou via TLS, API executou fluxo HTTP/CORS/503, ausência de dev/não-root confirmadas, shutdown gracioso real. **Zero consultas externas**. Testes adicionais corrigiram um erro de symlink no harness antes da execução final aprovada. Comandos e detalhes em [progress.md](progress.md).

Etapa 2b: banco `fintrack_test_db` local; `uv run pytest -q tests/app/routers/test_asset_router.py tests/prices/test_brapi_source.py` aprovou **47 testes em 2,78 s**. Esta evidência é da execução anterior, não foi repetida ao organizar os commits.

Docker CLI disponível, mas **daemon Docker Desktop indisponível**. Sintaxe dos três Compose e scripts shell validada; **imagem/build/Compose real/PostgreSQL 15 não executados** nesta etapa. Runtime no-dev não valida imagem. CI remoto, RDS/Render/AWS, frontend, deploy/backup/restauração e produção não testados. Não declarar esses itens aprovados.

Resultados brapi da etapa 0 (403 cripto, tickers 200) e 324 testes/imagem da v2 são históricos, não repetidos aqui. Não implementar cripto nem refazer consultas reais para continuar esta etapa.

Verificação documental final: **9 documentos, 71 links locais, 2 blocos JSON**, sintaxe Python/YAML/shell e `git diff --check` aprovados. Índice vazio, HEAD/branch preservados e nenhum processo PostgreSQL restante.

## Configuração e decisões da etapa 1

- `DATABASE_URL` não vazia vence componentes; query vence defaults TLS/timeout, mantendo outras opções. Componentes usam senha literal via URL.create; URL completa requer percent-encoding. Alembic recebe objeto URL diretamente, sem ConfigParser. Logs/erros de configuração não incluem senha/query secreta.
- TLS padrão `verify-full`, CA explícita e hostname TCP; `disable` somente explícito no fluxo local. CA deve ser montada em runtime, caminho dentro do container. Compose externo requer `DATABASE_CA_FILE` no host e usa `/run/certs/postgres-ca.pem`; uma query TLS na URL deve concordar com essa configuração.
- API: pool 3/overflow 0/timeout 10 s/pre-ping; libpq 5 s; readiness 3 s. Alembic NullPool. Um worker/réplica inicialmente; orçamento 7 conexões com release/reserva, 10 na sobreposição de duas réplicas. Limite real do destino não medido.
- API inicia somente Uvicorn por `start.sh`, respeita PORT/8000 e exec. Release única por `release.sh`; CMD Docker substituível. CI/roteiros executam release antes de web, que inicia com no-deps para não repetir migrations.
- `/health/live` 200 alive; `/health/ready` 200 ready ou 503 unavailable após SELECT 1, sem informações privadas. Fora do Swagger; readiness não atesta schema/brapi. Shutdown de serviço/HTTPX/engine preservado.
- Render: preparar comando da API/release separados. Pre-deploy pago não é pressuposto de gratuidade; execução controlada da release precisa ser definida antes de uma publicação futura autorizada. Nenhuma configuração remota alterada.

## Próxima etapa concreta (aguardando autorização)

Etapa **3a**: ler a seção correspondente no plano; conferir duplicidades e colisões de ticker normalizado em banco descartável/cópia antes de propor a migration. Preservar dados antigos; não deduplicar, renomear ou excluir automaticamente. Se houver colisões, registrar diagnóstico sem segredos e pedir decisão sobre a estratégia antes de migrar. **Não iniciar a 3a sem autorização explícita; não avançar para a 3b, remoção do admin, push, deploy ou AWS.**

Validação de imagem/Compose fica pendente até o daemon estar disponível; não bloqueia o ponto de retomada 2b permitido pelo aceite de infraestrutura da etapa 1. Não iniciar nenhum trabalho adicional nesta conversa.

Prompt para autorizar em outro chat:

> Leia AGENTS.md e docs/plans/market-discovery/handoff.md. Execute somente a etapa 3a, preserve as decisões e os dados históricos, confira duplicidades antes da migration, atualize os quatro documentos e pare antes da 3b. Não faça push, deploy nem provisione AWS.
