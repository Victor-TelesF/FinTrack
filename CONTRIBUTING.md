# Contribuir com o FinTrack

Use Python 3.13 e `uv sync --locked` para instalar as dependências. O [README](README.md) descreve como iniciar a aplicação; os [contratos](docs/api.md) e o [guia de operação](docs/operacao.md) detalham os comportamentos públicos.

## O que entra no GitHub

| Versionar | Manter local |
|---|---|
| `app/`, `domain/` e migrations em `alembic/` | `.env`, `.env.test` e outros `.env.*` com credenciais. |
| Testes e contratos com dados sintéticos | Bancos locais, dumps, backups e dados de usuários. |
| `pyproject.toml`, `uv.lock` e `.python-version` | `.venv`, caches, cobertura, logs e builds. |
| Dockerfile, Compose, CI e configuração compartilhada de desenvolvimento | Chaves privadas, certificados com chave e `secrets/`. |
| `.env.example` com placeholders, sem valores reais | Configuração pessoal de editor e ferramentas de assistência. |
| README, licença e guias públicos de API/operação | Planejamento, relatórios de sessões e registros locais de continuidade. |

`.gitignore` define exclusões do Git; `.dockerignore` define exclusões do contexto da imagem. Um não substitui o outro. O template `.env.example` é público de propósito. Os contratos de `tests/contracts/` também são públicos: usam dados sintéticos e servem de referência de compatibilidade.

Os arquivos locais de planejamento/continuidade são preservados na máquina e não estarão disponíveis em um clone novo. Os guias públicos precisam ser suficientes para instalar, testar e operar o projeto sem esses registros.

Antes de criar um commit, confira `git status --short` e `git diff --cached`. Use `git check-ignore -v caminho` para descobrir qual regra exclui um arquivo. Regras de ignore não retiram arquivos já versionados nem apagam histórico; não use `git add -f` para contornar exclusões de segredos.

## Testes

Domínio, sem banco:

```bash
uv run --locked pytest tests/domain -q
```

Para a suíte completa, crie **um PostgreSQL exclusivo e descartável**. As fixtures criam/removem tabelas; nunca use o banco da aplicação. Exemplo com credenciais exclusivamente sintéticas e porta local 15435 livre:

```bash
docker run -d --name fintrack-contrib-test-db \
  -e POSTGRES_USER=fintrack_test -e POSTGRES_PASSWORD=fintrack_test \
  -e POSTGRES_DB=fintrack_test -p 127.0.0.1:15435:5432 postgres:15-alpine
```

Aguarde `docker exec fintrack-contrib-test-db pg_isready -U fintrack_test -d fintrack_test` indicar que o banco aceita conexões. Depois:

```bash
POSTGRES_USER=fintrack_test POSTGRES_PASSWORD=fintrack_test \
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=15435 POSTGRES_DB=fintrack_test \
DATABASE_URL= DATABASE_SSLMODE=disable \
SECRET_KEY=synthetic-test-key ALGORITHM=HS256 ACCESS_TOKEN_EXPIRE_MINUTES=30 \
ADMIN_KEY=test-admin-key BRAPI_TOKEN= uv run --locked pytest -q
```

Essas variáveis têm precedência sobre `.env` e `.env.test`; `DATABASE_URL=` força os componentes sintéticos e `DATABASE_SSLMODE=disable` é explícito para este PostgreSQL local. Adicione essas opções a configurações locais de teste anteriores; não use `disable` no banco externo. Os testes de cotações usam respostas simuladas. Testes específicos de migrations validam upgrade do zero e com dados antigos; a criação de tabelas das fixtures HTTP não substitui essa verificação. Testes TLS opt-in são pulados nesta execução comum; o [harness TLS](docs/operacao.md#validar-tls-sem-docker) cria seu próprio servidor/certificados e executa esses testes junto da suíte completa.

Ao terminar, remova somente o recurso descartável criado acima:

```bash
docker stop fintrack-contrib-test-db
docker rm -v fintrack-contrib-test-db
```

A [validação da imagem](docs/operacao.md#validar-a-imagem-isoladamente) reproduz o job de produção do CI, sem credenciais reais.

## Mudanças e commits

- Mantenha cálculos e regras de domínio independentes de FastAPI, SQLAlchemy e HTTPX.
- Preserve `Decimal`, isolamento de usuários e os contratos existentes. Atualize documentação e testes quando mudar comportamento público.
- Não altere contratos de referência apenas para acomodar uma regressão.
- Separe commits por responsabilidade e use Conventional Commits em inglês, por exemplo `feat(prices): add bounded quote cache` ou `test(portfolio): cover concurrent sales`.
- Inclua evidências de testes realmente executados e indique suas limitações. Não trate execução local como CI remoto ou validação de produção.
- Commit local, push e deploy são ações distintas. Revise a branch e a configuração de deploy automático antes de publicar.
