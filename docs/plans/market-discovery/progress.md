# Progresso — pesquisa de mercado

## 02/10/2026 — etapa 0

**Autorização:** texto anexado definiu inspeção/plano na primeira conversa e uma etapa por conversa. Usuário pediu manter brapi inicialmente e facilitar outras fontes. Após verificar acesso a cripto, confirmou: manter tudo gratuito e deixar cripto pendente de uma fonte gratuita.

**Concluído:** lidos AGENTS/continuidade/plano/relatório da v2; conferidos Git, configuração, serviços de catálogo/carteira/cotações, contratos, migrations, testes, Docker e CI. Criados plano, contrato, progresso e handoff. Nenhuma implementação funcional, migration, dependência, commit, push ou deploy nesta etapa.

**Base:** branch `feature/v2-async-prices`, HEAD `80a6af7`. Árvore limpa no início. Histórico atual já contém a v2 em commits; os registros de `fcfd48b` com alterações locais descrevem sessões anteriores. Os documentos da v2 e AGENTS são ignorados pelo Git por decisão anterior; os quatro arquivos de `docs/plans/market-discovery/` estão fora dessas regras e prontos para versionamento.

### Verificações executadas nesta sessão

| Verificação | Resultado e limite |
|---|---|
| Git/inspeção estática | Branch/HEAD/histórico e arquivos relevantes conferidos. Sem consulta remota ao GitHub. |
| Baseline sem banco | **188 passed in 1.03s**, `tests/domain` + `tests/prices`. Respostas brapi simuladas; não valida rotas SQL/migrations. |
| Documentação oficial | Tickers, cotação, crypto/available, autenticação, planos, frequência e OpenAPI consultados. Referências no [plano](plan.md). |
| Cripto com chave configurada | `/api/v2/crypto/available?search=BTC` e `/api/v2/crypto?coin=BTC&currency=BRL`: **403** em ambos. Chave usada somente em header, nunca exibida ou persistida nos documentos. |
| Tickers autenticados | HGLG11 com `type=fund&subType=fii`: **200**, BRL, subtipo fii, um resultado e paginação consistente. |
| Tickers públicos | PETR4: **200**, PETR4/PETR4F; HGLG11: **200**, um FII; BOVA11 com filtro FII: **200**, zero itens. Não prova cobertura geral do catálogo. |

Comando executado para a baseline, com valores sintéticos:

```bash
POSTGRES_USER=fintrack_test POSTGRES_PASSWORD=fintrack_test \
POSTGRES_HOST=localhost POSTGRES_PORT=15435 POSTGRES_DB=fintrack_test \
SECRET_KEY=synthetic-test-key ALGORITHM=HS256 ACCESS_TOKEN_EXPIRE_MINUTES=30 \
ADMIN_KEY=test-admin-key BRAPI_TOKEN= UV_CACHE_DIR=/tmp/fintrack-uv-cache \
uv run --locked pytest -q tests/domain tests/prices
```

### Achados incorporados ao plano

- Cripto brapi não está disponível na conta configurada; nenhuma assinatura autorizada. Não tratar existência do endpoint como gratuidade/cobertura confirmada.
- Usar listagem v2 com `assetType`/`subType`, filtros no provedor e paginação verdadeira; não inferir FII por ticker terminando em 11.
- Separar limites HTTP compartilhados, contrato de descoberta e registro de capacidades; reaproveitar protocolo de cotações/cache/Decimal.
- Ticker sem unicidade no PostgreSQL impede garantir cadastro concorrente; etapa 3a adicionada antes do fluxo de primeira compra. Duplicidades históricas não serão corrigidas automaticamente.
- Separar release do entrypoint; configurar URL/TLS/pool e health nas etapas autorizadas, sem provisionar AWS.

### Não executado / pendências

Sem suíte completa, PostgreSQL, migrations, container/build, TLS real, CI remoto, frontend ou deploy nesta sessão. Não consultar banco de produção nem afirmar que esses itens foram validados. **324 testes** e cotações autenticadas ação/FII continuam evidência histórica da v2, não resultado desta etapa.

Próxima ação: etapa 1 após autorização explícita. Pesquisa/detalhe/cadastro/admin seguem inalterados no código. Cripto ficará em outro escopo com fonte gratuita validada.

Verificação documental final: **7 arquivos, 60 links locais e 2 blocos JSON conferidos**, sem erros de links, JSON ou whitespace; `git diff --check` aprovado. Git ao encerrar: README modificado e `docs/plans/` novo, sem staging/commit. Os dois registros locais ignorados da v2 foram atualizados; relatórios anteriores preservados. Nenhum arquivo funcional alterado.

## 02/10/2026 — branch dedicada

Usuário pediu criar outra branch antes de começar a refatoração. Criada e selecionada **`refactor/market-discovery`**, a partir de `feature/v2-async-prices`/`80a6af7`, com `git switch -c refactor/market-discovery`. README e documentos sem commit preservados; handoff/plano/continuidade atualizados com a branch atual. A primeira tentativa foi bloqueada pelo sandbox de `.git` somente leitura; execução autorizada fora do sandbox concluiu a criação.

Conferidos branch, HEAD, base e `git diff --check`; nenhum teste da aplicação repetido nesta alteração de Git/documentação. Nenhum commit ou push. Etapa 0 permanece concluída; etapa 1 continua aguardando autorização explícita.

## 02/10/2026 — etapa 2a

**Autorização:** usuário pediu seguir para a etapa 2 após leitura do handoff e do plano; a execução ficou restrita a 2a, preservando o limite de 2b/3a/3b e sem iniciar separações de produto fora do escopo.

**Implementação:** `app/price_sources/types.py` recebeu contratos pequenos de descoberta (`MarketAsset`, `MarketAssetSearchResult`, `MarketProviderCapability`), e `app/price_sources/brapi_source.py` recebeu classificação por `assetType`/`subType`, paginação, resposta de busca, resolução exata por ticker e capacidade explícita do provedor. `QuoteService` passou a expor `search_market()` e `resolve_market()` e reaproveita o mesmo rate limit/semáforo do adaptador, mantendo cache e falhas compatíveis com as cotações.

**Verificações executadas nesta sessão:**

| Verificação | Resultado |
|---|---|
| Suíte focada de preços | **63 passed** em `tests/prices` com `uv run pytest -q tests/prices` |
| Validação cruzada de domínio e preços | **188 passed** em `tests/domain tests/prices` com `uv run pytest -q tests/domain tests/prices` |
| Sanidade de descoberta | pesquisa e resolução exata para `HGLG11`/`real_estate_fund` validadas em cliente HTTP simulado, sem chamadas individuais por item e sem persistência em banco |

**Limites e continuidade:** sem rotas de mercado/asset-router/primeira compra, sem contrato de 2b, sem migrations 3a/3b e sem admin. O próximo avanço permitido requer autorização explícita para a etapa 2b.

## 02/10/2026 — etapa 2b

**Autorização:** o usuário solicitou continuar com a etapa 2b e, ao confirmar que o Docker Desktop estava disponível, a validação foi executada no ambiente real do app.

**Implementação concluída no branch atual:** `app/routers/asset_router.py` adicionou `GET /assets/search` e `GET /assets/market/{ticker}`; `app/schemas/asset_schema.py` definiu os schemas de resposta `MarketAssetRead`, `MarketAssetSearchRead` e `MarketQuoteRead`; a integração do `QuoteService` foi mantida sem alterar o catálogo local. As rotas ficam antes de `/{asset_id}` e preservam autenticação JWT do FinTrack.

**Verificações executadas nesta sessão:**

| Verificação | Resultado |
|---|---|
| Banco do projeto com Docker | `docker compose -f docker-compose.yml up -d db` levou o serviço `fintrack-db-1` a ficar pronto e aceitar conexão locais |
| Teste de rotas de mercado | `uv run pytest -q tests/app/routers/test_asset_router.py tests/prices/test_brapi_source.py` → **47 passed** em 2,78 s |
| Modo de execução real | Banco `fintrack_test_db` foi criado localmente antes da execução para satisfazer as fixtures do app |

**Limites e continuidade:** a etapa 2b foi confirmada no ambiente real do app e não houve alteração de domínio/admin ou migração 3a/3b. O trabalho continua restrito a pesquisa e detalhe do mercado, sem abrir a próxima etapa sem nova autorização explícita.

## 02/10/2026 — etapa 1

**Autorização:** usuário pediu ler AGENTS/handoff, executar somente etapa 1, preservar decisões, testar, atualizar os quatro documentos e parar antes da 2a. Proibidos commit, push, deploy e provisão AWS. Autorização concluída nesta sessão, sem avançar descoberta/cadastro/admin.

**Estado inicial:** `refactor/market-discovery`, HEAD `80a6af7`; README modificado e `docs/plans/` novo, sem staging. Lidos AGENTS, handoff, plano, contrato e progresso; estado conferido contra os arquivos da etapa. WIP documental preservado. Registros da v2 permanecem históricos; seus apontadores de retomada foram alinhados ao handoff atual.

### Implementação e decisões técnicas

- `app/config.py`: `sqlalchemy.URL.create` por componentes e `DATABASE_URL` SecretStr prioritária; aceita schemas PostgreSQL e normaliza para psycopg. Query externa conservada e prioritária sobre defaults separados, incluindo TLS/timeout. Senha por componentes literal, senha na URL percent-encoded. Senhas protegidas, diagnóstico sem query/senha e mensagens de validação sem entrada; JWT/admin omitidos da serialização de Settings.
- TLS seguro por padrão: `verify-full`, CA explícita e hostname TCP. Local aceita `disable` explícito; modos intermediários rejeitados, sem fallback. API e Alembic recebem a mesma URL. Alembic passa URL diretamente, sem interpolar `%`, com NullPool e dispose em finally.
- Pool da API configurável, padrões 3 conexões, overflow 0, espera 10 s e pre-ping; timeout libpq 5 s. Readiness tem deadline total 3 s e usa esse pool. Orçamento documentado: 3 API + 1 release + 3 reserva = 7; duas réplicas durante atualização = 10. Valores de planejamento, sem medir limite RDS.
- `release.sh` só migra; `start.sh` só Uvicorn, um worker, `PORT`/8000 e exec. Dockerfile usa CMD substituível, mantém usuário não-root/instalação no-dev e consulta readiness. Compose local espera db/release; CI/roteiro de validação executam release uma vez e iniciam web com no-deps. Novo Compose externo requer banco existente e CA em runtime; não provisiona recursos.
- Health público, fora do Swagger: liveness sem IO externo; readiness SELECT 1, 200/503 com corpo mínimo. Shutdown existente preservado. Mercado, primeira compra, admin, regras financeiras e migrations existentes não foram alterados.
- README/guias de operação e contribuição alinhados. Comando de teste local limpa DATABASE_URL e desabilita TLS explicitamente no banco sintético; `.env`/`.env.test` pessoais preservados. Render documentado com release separada; pre-deploy é recurso pago, não assumido para o serviço gratuito. Nenhuma mudança remota feita nem assinatura solicitada.

### Verificações executadas nesta sessão

| Verificação | Resultado e limite |
|---|---|
| URL/configuração/unitários/domínio/preços | Primeira execução: **219 passed in 1.31s**, sem banco; depois incluídos casos adicionais de URL/pool/TLS. Credenciais sempre sintéticas. |
| Suíte completa com TLS | Execução final: **364 passed, 302 warnings in 35.47s**, PostgreSQL **18.6**, loopback, descartável, senha especial e SCRAM. Warnings existentes de `python-jose`/`utcnow`, sem alteração de autenticação. |
| TLS real, API e Alembic | CA/hostname corretos aceitos, `pg_stat_ssl` confirma TLS nas conexões sync/async. CA errada e hostname IP incompatível rejeitados em migrations/API; readiness retorna 503 sem detalhes. Conexão sem TLS rejeitada pelo servidor. |
| Migrations | Upgrade vazio até `9d2a6c4e8f10` via URL TLS com senha especial; testes existentes também verificaram upgrade populado/downgrade/reaplicação e preservação de dados. Nenhuma migration nova. |
| Pool/readiness | Defaults/customização/pre-ping/NullPool verificados; pool real de uma conexão saturado retorna 503 dentro do prazo e recupera 200 após liberação, sem conexão vazada. |
| Runtime sem dev | `uv sync --locked --no-dev` em `/tmp/fintrack-stage1-runtime`; API real iniciada antes da release **não criou alembic_version**. Depois release TLS via `sh release.sh`, API via `sh start.sh`/porta efêmera, `scripts.check_release` aprovado: usuário não-root, sem pytest/dev, fluxo register/login/catalog/buy/sell/legacy/v2/history/CORS/503, **0 chamadas externas**. Shutdown gracioso real antes/depois da release, sem senha no log sintético. Isso valida runtime, não imagem. |
| Contratos | Suíte HTTP legada/v2 e snapshot OpenAPI existentes aprovados, sem regenerar baselines. Rotas de saúde fora do Swagger. |
| Compose/shell | `docker.exe compose ... config --quiet` aprovado nos três arquivos; `sh -n start.sh release.sh` aprovado. Sintaxe validada sem containers. |
| Documentação oficial | SQLAlchemy URL, SSL libpq, Alembic, ordem Compose e comandos/portas Render consultados; links no plano/guia. Sem consulta brapi real nesta etapa. |

O Docker CLI inicialmente falhou no sandbox WSL; fora do sandbox, confirmou **daemon indisponível** (`dockerDesktopLinuxEngine` ausente). Não criar/parar recursos existentes para contornar. Como alternativa de validação, baixados pacotes Ubuntu PostgreSQL 18.6/client/libpq e bibliotecas numa pasta em `/tmp`, extraídos sem instalar serviço/sistema. Harness [scripts/test_postgres_tls.py](../../../scripts/test_postgres_tls.py) gera seu próprio cluster/certificados, executa testes e encerra/remove somente seu diretório temporário. Nenhum volume/container novo foi criado.

Primeiro ensaio adicional sem dev falhou porque o harness resolveu o symlink do executável Python para o Python base, fora do venv (`httpx` ausente). Corrigido preservando o caminho absoluto do venv; execução final da suíte + ensaio no-dev **concluiu com exit 0**. Primeiro comando do Compose externo não recebeu a variável Linux no Docker Windows; repetição com `WSLENV=DATABASE_CA_FILE/p` validou a sintaxe. Esses erros não foram tratados como defeitos da API.

### Reprodução e limites

Binários extraídos nesta sessão em `/tmp/fintrack-stage1-pg/root/usr/lib/postgresql/18/bin`, bibliotecas em `/tmp/fintrack-stage1-pg/root/usr/lib/x86_64-linux-gnu`. Esses caminhos são auxiliares locais, não configuração de deployment. Com dependências/binários disponíveis:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/fintrack-stage1-runtime UV_CACHE_DIR=/tmp/fintrack-uv-cache uv sync --locked --no-dev
LD_LIBRARY_PATH=/tmp/fintrack-stage1-pg/root/usr/lib/x86_64-linux-gnu \
POSTGRES_USER=synthetic POSTGRES_PASSWORD=synthetic POSTGRES_HOST=localhost \
POSTGRES_PORT=15436 POSTGRES_DB=synthetic DATABASE_URL= DATABASE_SSLMODE=disable \
SECRET_KEY=synthetic ALGORITHM=HS256 ACCESS_TOKEN_EXPIRE_MINUTES=30 \
ADMIN_KEY=synthetic BRAPI_TOKEN= UV_CACHE_DIR=/tmp/fintrack-uv-cache \
uv run --locked python -m scripts.test_postgres_tls \
  --pg-bin /tmp/fintrack-stage1-pg/root/usr/lib/postgresql/18/bin \
  --runtime-python /tmp/fintrack-stage1-runtime/bin/python
```

O harness substitui a configuração por dados sintéticos e exige TLS no cluster. Os testes TLS opt-in são pulados no pytest comum quando `FINTRACK_TLS_TEST_URL` não estiver definida. O CI existente continua testando PostgreSQL 15/local sem TLS e a imagem, com release separada; o ensaio TLS é local e não foi adicionado como workflow de produção.

**Não executado:** build/execução/shutdown da imagem candidata, fluxo Compose real/PostgreSQL 15, CI remoto, RDS/EC2/ECR/IAM, Render, frontend, backup/restauração ou deployment. Runtime no-dev aprovado não equivale a imagem aprovada; TLS de localhost não prova conectividade/CA/permissões de RDS. Repetir imagem/Compose quando houver daemon e validar infraestrutura real apenas em escopo autorizado.

**Encerramento:** etapa 1 concluída com limites de infraestrutura explicitamente registrados, conforme o aceite do plano. Quatro documentos atualizados, histórico anterior preservado; README/guia operacional e apontadores locais da v2 coerentes. Próxima ação **etapa 2a somente após autorização explícita**, sem executar 2b na mesma conversa. Sem staging, commit, push, deploy, AWS ou acesso a produção.

Verificação final documental: **9 documentos, 71 links locais e 2 blocos JSON aprovados**, sintaxe Python/YAML/shell aprovada e `git diff --check` sem erros. Sintaxe final dos três Compose aprovada depois da troca para CMD/comando de release. Branch/HEAD preservados, índice vazio e nenhum processo PostgreSQL restante. Alterações desta etapa permanecem locais, juntamente com o WIP anterior.

## 02/10/2026 — micro commits locais das etapas concluídas

**Autorização:** o usuário pediu que as mudanças fossem commitadas como micro commits. Isso substitui a restrição anterior de não commitar apenas para registrar localmente o trabalho já concluído; não autoriza push, deploy, AWS ou avanço para a etapa 3a.

**Escopo preservado:** alterações existentes das etapas 1, 2a e 2b separadas por responsabilidade. Nenhuma implementação nova nesta sessão. Os commits de implementação/documentação operacional foram:

- `e50541e feat(db): support external PostgreSQL URLs and TLS`
- `ed50771 feat(runtime): separate migrations from API startup`
- `e6841ef test(db): exercise PostgreSQL TLS integration`
- `2a3bcfb feat(market): add brapi asset discovery contracts`
- `268050e feat(api): expose authenticated market search routes`
- `b4f784d docs(runtime): explain external PostgreSQL operations`

Este registro, o plano e o handoff foram alinhados no commit documental da mesma sequência; consulte `git log --oneline` para o hash mais recente.

**Verificações nesta sessão:** `git diff --check` foi aprovado antes do staging e `git diff --cached --check` foi aprovado para cada grupo antes do respectivo commit. Não foram executados testes nesta sessão; os resultados 364 (etapa 1), 63/188 (etapa 2a) e 47 (etapa 2b) são evidências históricas das sessões correspondentes, não revalidações atuais.

**Estado de saída:** branch `refactor/market-discovery`, commits locais, sem push. A etapa 3a permanece pendente de autorização explícita; antes de uma migration, conferir colisões de ticker em banco descartável e interromper se houver dados que exijam decisão.
