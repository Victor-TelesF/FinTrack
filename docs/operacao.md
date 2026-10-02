# Operação e atualização

## Configuração do backend

Use [.env.example](../.env.example) como referência local. No Render, mantenha as variáveis no serviço existente. Não envie `.env` nem chaves para o repositório ou para o frontend.

| Configuração | Finalidade |
|---|---|
| `DATABASE_URL` | URL externa, com precedência sobre os componentes; aceita `postgres://`, `postgresql://` ou `postgresql+psycopg://`, sempre usando psycopg. Senha na URL deve ser percent-encoded. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` | Alternativa por componentes; senha literal, sem escape. URL construída com `sqlalchemy.URL.create`, compartilhada pela API e pelo Alembic. Porta padrão 5432. |
| `DATABASE_SSLMODE`, `DATABASE_SSLROOTCERT` | Padrão seguro `verify-full`, com caminho explícito para CA e hostname TCP. `disable` é aceito explicitamente para o banco local. Outros modos são rejeitados. |
| `DATABASE_CONNECT_TIMEOUT` | Timeout libpq, padrão 5 s. |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT` | Padrões 3, 0 e 10 s; API com pre-ping, Alembic com NullPool. |
| `DATABASE_READY_TIMEOUT` | Prazo total da consulta de prontidão, incluindo espera pelo pool; padrão 3 s. |
| `PORT` | Porta Uvicorn; padrão 8000, um worker. |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Assinatura e validade do JWT. Preservar a chave mantém as sessões existentes válidas até sua expiração. |
| `ADMIN_KEY` | Acesso ao cadastro administrativo de ativos. |
| `FRONTEND_ORIGINS` | Origens autorizadas pelo CORS, separadas por vírgula. |
| `BRAPI_TOKEN` | Chave de cotações, sem prefixo `Bearer`; o adaptador monta o header. |

Os padrões do serviço de cotações são timeout de 10 s, cache de 1800 s, até 1000 entradas, lote de um ativo e concorrência externa de uma chamada. Podem ser configurados pelas variáveis `PRICE_*` do exemplo. Confira a cobertura e os limites da conta contratada; esses parâmetros não garantem cotação em tempo real nem cota suficiente para qualquer volume de uso.

Cache, deduplicação, tratamento de 429 e rate limit de autenticação são locais ao processo. Comece com um processo/réplica. A sessão de leitura do banco permanece aberta durante a busca de cotações; a validação funcional não substitui teste de carga.

### Precedência, TLS e segredos

`DATABASE_URL` vazia usa os componentes. Quando preenchida, suas opções de query têm precedência sobre `DATABASE_SSLMODE`, `DATABASE_SSLROOTCERT` e `DATABASE_CONNECT_TIMEOUT`; demais opções, como `application_name` e `options`, são conservadas. API e release recebem o mesmo objeto URL, sem interpolação de `%` pelo ConfigParser do Alembic. Não imprima a URL bruta: o diagnóstico `settings.redacted_database_url` mascara a senha e omite a query; erros de configuração não incluem valores de entrada.

Para banco externo, configure o hostname real coberto pelo certificado, `verify-full` e a CA correspondente. Monte a CA somente em runtime, legível pelo usuário não-root. Se essas opções estiverem na query, o caminho de `sslrootcert` deve ser o caminho dentro do container. O Compose externo usa `/run/certs/postgres-ca.pem`. Não mantenha `sslmode=disable` numa URL externa: a query prevalece sobre o ambiente do Compose. O código não faz fallback para TLS sem validação. Referências: [URL SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/engines.html#creating-urls-programmatically) e [SSL libpq](https://www.postgresql.org/docs/current/libpq-ssl.html).

No RDS futuro, usar a CA oficial apropriada e o endpoint real da instância. Nenhum endpoint RDS, recurso AWS ou segredo de produção foi criado ou testado nesta etapa. Credenciais/JWT/brapi permanecem em runtime; não passá-los por build args nem copiar `.env` para a imagem.

### Orçamento de conexões

Capacidade máxima da API: `réplicas × processos × (pool_size + max_overflow)`. Com uma réplica/worker e os padrões, são **3 conexões**. A readiness usa o mesmo pool. Reservar mais **1** para uma release e pelo menos **3** para administração/observabilidade: orçamento inicial **7**; durante sobreposição de duas réplicas, **10**. Conferir o limite real e outros consumidores antes de publicar; esses valores são um orçamento, não medição de RDS. `NullPool` encerra a conexão da release ao terminar. Múltiplos workers também multiplicam os limites locais da brapi.

### Release e healthchecks

`sh release.sh` executa apenas `alembic upgrade head`, propagando falha. `sh start.sh` inicia somente Uvicorn, com `exec`, `PORT` e um worker. O Dockerfile usa `CMD`, permitindo substituir o comando pela release sem herdar um entrypoint que inicia a API. Executar uma release por atualização, antes de liberar a API; um reinício da API não migra o banco.

| Endpoint público | Resposta | Uso |
|---|---|---|
| `GET /health/live` | 200, `{"status":"alive"}` | Processo HTTP; sem banco ou chamada externa. |
| `GET /health/ready` | 200, `{"status":"ready"}` ou 503, `{"status":"unavailable"}` | `SELECT 1` com prazo curto; falha de conexão/TLS/pool não expõe detalhes. |

São endpoints operacionais fora do Swagger. A readiness verifica conectividade, não versão do schema nem brapi; a release é uma condição separada. O container consulta readiness. Shutdown continua encerrando serviço de cotações, HTTPX e engine.

O Compose local executa `db → release → web`, com TLS local desabilitado explicitamente. Para ensaiar com um PostgreSQL externo **já existente e descartável**, use [docker-compose.external.yml](../docker-compose.external.yml), `.env` com credenciais desse banco e `DATABASE_CA_FILE` apontando para a CA no host. Os comandos abaixo só devem ser executados nesse ambiente preparado:

```bash
docker compose -f docker-compose.external.yml build
docker compose -f docker-compose.external.yml run --rm --no-deps release
docker compose -f docker-compose.external.yml up -d --no-deps --wait web
```

Se a release falhar, não executar o último comando. Esse Compose não cria banco, recursos AWS ou workflow de produção.

## Atualizar o serviço no Render

1. Revisar o commit candidato, executar o CI e preservar a imagem anterior. Obter backup restaurável do banco existente e ensaiar o upgrade numa cópia.
2. Preservar banco, JWT e CORS. Configurar URL/TLS/CA conforme o banco existente e adicionar `BRAPI_TOKEN` ao backend. O frontend atual continua utilizando as rotas anteriores.
3. Usar o Dockerfile da raiz, com comando da API `sh /app/start.sh`; a porta respeita `PORT`. A release é `sh /app/release.sh`, executada uma vez antes da API. O [pre-deploy do Render](https://render.com/docs/deploys#pre-deploy-command) está disponível em serviços pagos; não pressupor esse recurso no plano gratuito nem contratar um plano. Sem pre-deploy, preparar uma release manual controlada com a imagem candidata e a mesma configuração, em ambiente autorizado com acesso ao banco, antes de liberar a revisão. Não recolocar migrations no startup ou no build. Ver [portas](https://render.com/docs/web-services#port-binding).
4. Conferir a revisão Alembic `9d2a6c4e8f10` e os fluxos de cadastro/login, catálogo, compra/venda, histórico e avaliação legada.
5. Revisar metadados dos ativos, validar as leituras v2 e atualizar o frontend em seguida. Monitorar 422/503, latência, conexões do banco e consumo do provedor.

O Compose padrão é de desenvolvimento: monta o código e publica a porta do PostgreSQL. A imagem de produção deve funcionar sem esse volume e sem `--reload`. Configurar `/health/ready` como healthcheck do serviço. As instruções de Render são preparação documental; nenhuma configuração remota foi alterada nesta etapa.

### Dados antigos e migration

A migration adiciona `price_provider`, `external_price_id` e `quote_currency`. Preenche apenas BRL/USD dos tipos de ações, preservando IDs, preços e transações. Não habilita provedor nem símbolo automaticamente.

FIIs, cripto e renda fixa antigos podem permanecer sem moeda. Se estiverem em posições abertas, as leituras v2 retornam 422. Com histórico, o upsert bloqueia mudança de moeda; use uma migração de dados revisada para completar esses registros. Não adivinhe a moeda a partir do ticker.

### Atualizar o frontend

| Antes | Depois |
|---|---|
| `/portfolios/positions` | `/api/v2/portfolios/positions` |
| `/portfolios/summary` | `/api/v2/portfolios/summary` |
| Preço único do ativo | `asset.registered_price` para cadastro; `quote.price` para avaliação. |
| Total geral | Um total por item de `totals_by_currency`. |

Manter cadastro/login, catálogo, compras, vendas e histórico nas rotas atuais, com o mesmo JWT. Exibir origem e horário do preço; identificar `source=manual` como preço cadastrado e respeitar `contains_manual_prices`. Não somar moedas ou tratar cache como garantia de tempo real.

Tratar 401 como sessão expirada, 422 como configuração pendente e 503 como avaliação indisponível. Não zerar valores, apresentar totais parciais nem trocar silenciosamente pela leitura legada. Validar carteira vazia, moedas distintas, preço manual, cache e falhas do provedor antes da liberação.

## Validar a imagem isoladamente

O ambiente abaixo usa somente dados sintéticos, não carrega `.env`, não publica portas e não monta o código. Requer Compose com suporte a `--wait`.

```bash
docker compose -p fintrack-release-check -f docker-compose.validation.yml build
docker compose -p fintrack-release-check -f docker-compose.validation.yml up -d --wait db
docker compose -p fintrack-release-check -f docker-compose.validation.yml run --rm --no-deps release
docker compose -p fintrack-release-check -f docker-compose.validation.yml up -d --no-deps --wait --wait-timeout 120 web
docker compose -p fintrack-release-check -f docker-compose.validation.yml exec -T web python -m scripts.check_release
docker compose -p fintrack-release-check -f docker-compose.validation.yml stop -t 30 web
docker compose -p fintrack-release-check -f docker-compose.validation.yml logs --no-color web
docker compose -p fintrack-release-check -f docker-compose.validation.yml down --volumes
```

O script verifica migrations, usuário não-root, ausência de dependências dev e fluxo HTTP. Conferir `Application shutdown complete` no encerramento. A remoção acima é exclusiva do projeto descartável; não usar `down --volumes` no banco da aplicação.

### Validar TLS sem Docker

Com binários PostgreSQL/OpenSSL disponíveis, o harness abaixo cria um banco temporário de dados sintéticos, CA e certificado de localhost; exige TLS e senha especial. Executa a suíte completa, migrations reais e rejeições de CA/hostname. Para também ensaiar release/API/HTTP/shutdown sem dependências dev:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/fintrack-stage1-runtime UV_CACHE_DIR=/tmp/fintrack-uv-cache uv sync --locked --no-dev
UV_CACHE_DIR=/tmp/fintrack-uv-cache uv run --locked python -m scripts.test_postgres_tls \
  --pg-bin /caminho/dos/binarios/postgresql/bin \
  --runtime-python /tmp/fintrack-stage1-runtime/bin/python
```

O diretório dos binários deve conter `initdb`, `pg_ctl`, `postgres` e `createdb`, com bibliotecas disponíveis. Configuração inicial de `uv run` exige as variáveis sintéticas do projeto; não carregar credenciais de produção para esse teste. O harness para o servidor e remove seu próprio diretório temporário ao encerrar. Sem o harness, os testes TLS opt-in são pulados. Esse ensaio não substitui validar a imagem Docker nem o PostgreSQL 15 do Compose.

Com token configurado, `uv run --locked python -m scripts.check_brapi` realiza uma consulta controlada de BBDC4 e HGLG11 e verifica o cache. Consome chamadas reais; não integra o CI. Não imprime token nem resposta bruta.

## Retorno à versão anterior

Primeiro, retornar a interface às leituras legadas, identificadas como preço cadastrado. A migration é aditiva, mas **o Alembic da imagem anterior não reconhece a revisão nova**.

Para conservar o schema, a imagem anterior deve iniciar diretamente Uvicorn, substituindo efetivamente seu `ENTRYPOINT`. Em Docker, o comando de referência é `--entrypoint /opt/venv/bin/uvicorn`, com `app.main:app --host 0.0.0.0 --port 8000` após a imagem. Ensaiar o procedimento na infraestrutura de destino; mudar somente argumentos de execução pode não substituir um entrypoint fixo.

Suspender alterações administrativas durante esse retorno. O código antigo desconhece os metadados e suas validações; novos cadastros podem exigir revisão antes de retomar v2.

Se for indispensável remover as colunas, exportar seus valores e executar `alembic downgrade 72768f7801ec` **com a imagem nova**, antes de iniciar a antiga. Isso remove os metadados de cotação. Não executar downgrade até `base`: uma migration histórica deixa o enum `transaction_type_enum` no banco. Restauração de backup exige considerar transações posteriores.

## Pendências conhecidas

- Erros de validação de autenticação podem refletir a senha recebida em `detail[].input`; sanitização ainda pendente.
- Repetir build/execução/shutdown da imagem e PostgreSQL 15 quando o Docker estiver disponível. Validar TLS/CA na infraestrutura externa antes de qualquer publicação; o ensaio atual usou PostgreSQL 18.6 descartável.
- Compatibilidade local do código anterior foi verificada com dependências da imagem candidata; restauração e retorno com a imagem efetivamente publicada ainda precisam ser ensaiados no destino.
