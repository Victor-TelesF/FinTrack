# Operação e atualização

## Configuração do backend

Use [.env.example](../.env.example) como referência local. No Render, mantenha as variáveis no serviço existente. Não envie `.env` nem chaves para o repositório ou para o frontend.

| Configuração | Finalidade |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` | Conexão do banco. O código não lê `DATABASE_URL`. |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Assinatura e validade do JWT. Preservar a chave mantém as sessões existentes válidas até sua expiração. |
| `ADMIN_KEY` | Acesso ao cadastro administrativo de ativos. |
| `FRONTEND_ORIGINS` | Origens autorizadas pelo CORS, separadas por vírgula. |
| `BRAPI_TOKEN` | Chave de cotações, sem prefixo `Bearer`; o adaptador monta o header. |

Os padrões do serviço de cotações são timeout de 10 s, cache de 1800 s, até 1000 entradas, lote de um ativo e concorrência externa de uma chamada. Podem ser configurados pelas variáveis `PRICE_*` do exemplo. Confira a cobertura e os limites da conta contratada; esses parâmetros não garantem cotação em tempo real nem cota suficiente para qualquer volume de uso.

Cache, deduplicação, tratamento de 429 e rate limit de autenticação são locais ao processo. Comece com um processo/réplica. A sessão de leitura do banco permanece aberta durante a busca de cotações; a validação funcional não substitui teste de carga.

## Atualizar o serviço no Render

1. Revisar o commit candidato, executar o CI e preservar a imagem anterior. Obter backup restaurável do banco existente e ensaiar o upgrade numa cópia.
2. Manter a configuração atual de banco, JWT e CORS. Adicionar `BRAPI_TOKEN` ao backend. O frontend atual continua utilizando as rotas anteriores.
3. Usar o Dockerfile da raiz. O `start.sh` executa `alembic upgrade head` e inicia Uvicorn em `0.0.0.0:8000`. O Render recomenda a variável `PORT` e normalmente detecta portas alternativas; o script atual ainda fixa 8000. Ver [documentação de portas](https://render.com/docs/web-services#port-binding).
4. Conferir a revisão Alembic `9d2a6c4e8f10` e os fluxos de cadastro/login, catálogo, compra/venda, histórico e avaliação legada.
5. Revisar metadados dos ativos, validar as leituras v2 e atualizar o frontend em seguida. Monitorar 422/503, latência, conexões do banco e consumo do provedor.

O Compose padrão é de desenvolvimento: monta o código e publica a porta do PostgreSQL. A imagem de produção deve funcionar sem esse volume e sem `--reload`. O health check atual em `/openapi.json` verifica HTTP, não a disponibilidade do banco ou da brapi.

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
docker compose -p fintrack-release-check -f docker-compose.validation.yml up --build --wait --wait-timeout 120
docker compose -p fintrack-release-check -f docker-compose.validation.yml exec -T web python -m scripts.check_release
docker compose -p fintrack-release-check -f docker-compose.validation.yml stop -t 30 web
docker compose -p fintrack-release-check -f docker-compose.validation.yml logs --no-color web
docker compose -p fintrack-release-check -f docker-compose.validation.yml down --volumes
```

O script verifica migrations, usuário não-root, ausência de dependências dev e fluxo HTTP. Conferir `Application shutdown complete` no encerramento. A remoção acima é exclusiva do projeto descartável; não usar `down --volumes` no banco da aplicação.

Com token configurado, `uv run --locked python -m scripts.check_brapi` realiza uma consulta controlada de BBDC4 e HGLG11 e verifica o cache. Consome chamadas reais; não integra o CI. Não imprime token nem resposta bruta.

## Retorno à versão anterior

Primeiro, retornar a interface às leituras legadas, identificadas como preço cadastrado. A migration é aditiva, mas **o Alembic da imagem anterior não reconhece a revisão nova**.

Para conservar o schema, a imagem anterior deve iniciar diretamente Uvicorn, substituindo efetivamente seu `ENTRYPOINT`. Em Docker, o comando de referência é `--entrypoint /opt/venv/bin/uvicorn`, com `app.main:app --host 0.0.0.0 --port 8000` após a imagem. Ensaiar o procedimento na infraestrutura de destino; mudar somente argumentos de execução pode não substituir um entrypoint fixo.

Suspender alterações administrativas durante esse retorno. O código antigo desconhece os metadados e suas validações; novos cadastros podem exigir revisão antes de retomar v2.

Se for indispensável remover as colunas, exportar seus valores e executar `alembic downgrade 72768f7801ec` **com a imagem nova**, antes de iniciar a antiga. Isso remove os metadados de cotação. Não executar downgrade até `base`: uma migration histórica deixa o enum `transaction_type_enum` no banco. Restauração de backup exige considerar transações posteriores.

## Pendências conhecidas

- A URL de banco é concatenada sem escape; senhas com `@` podem ser interpretadas incorretamente. Corrigir a construção da URL e seu uso no Alembic antes de adotar esse tipo de credencial.
- Erros de validação de autenticação podem refletir a senha recebida em `detail[].input`; sanitização ainda pendente.
- Porta configurável e prontidão com verificação do banco são melhorias pendentes.
- Compatibilidade local do código anterior foi verificada com dependências da imagem candidata; restauração e retorno com a imagem efetivamente publicada ainda precisam ser ensaiados no destino.
