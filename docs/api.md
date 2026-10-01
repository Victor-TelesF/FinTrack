# Contratos da API

O Swagger em `/docs` e o documento `/openapi.json` descrevem a versão em execução. Este guia apresenta o contrato da atualização v2, preservando as rotas anteriores.

## Autenticação

`POST /auth/register` recebe `user_name` e `password` (mínimo de oito caracteres). `POST /auth/login` recebe esses mesmos campos em **JSON**, não formulário OAuth2.

Exemplo exclusivamente local, com dados fictícios:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"user_name":"demo","password":"local-demo-password"}'

curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"user_name":"demo","password":"local-demo-password"}'
```

Use o campo `access_token` da resposta como `Authorization: Bearer <token>` nas requisições autenticadas. O cadastro cria a carteira do usuário. Login/cadastro têm limite compartilhado de cinco requisições por IP em uma janela de 60 segundos, por processo; excesso retorna 429.

## Catálogo e administração

`GET /assets` e `GET /assets/{asset_id}` exigem JWT. O cadastro/atualização em lote usa `POST /admin/assets` com o header `X-Admin-Key`, comparado ao `ADMIN_KEY` do backend.

Exemplo de corpo administrativo com preço fictício:

```json
{
  "assets": [{
    "type": "national_stock",
    "name": "Petrobras PN",
    "ticker": "PETR4",
    "current_price": "35.50",
    "quote_currency": "BRL",
    "price_provider": "brapi",
    "external_price_id": "PETR4"
  }]
}
```

| Campo | Contrato |
|---|---|
| `current_price` | Preço cadastrado obrigatório, separado do preço de compra/venda e da cotação. |
| `quote_currency` | BRL, USD, EUR ou `null`. No cadastro inicial, ações nacionais/internacionais têm BRL/USD implícitos. |
| `price_provider` | `brapi`, `manual` ou `null`. Mercado exige ação nacional ou FII em BRL. |
| `external_price_id` | Símbolo externo explícito, com letras maiúsculas e números; não é inferido do ticker interno. |

O cadastro valida a configuração sem consultar a brapi; cobertura e existência do instrumento são verificadas durante a avaliação. Omitir metadados em uma atualização preserva seus valores. Para usar preço manual, configure `price_provider: "manual"` e `external_price_id: null`.

O tipo de um ativo existente não pode mudar pelo upsert. A moeda só pode mudar enquanto não houver transações; com histórico, inclusive posição encerrada, a tentativa retorna 409 e exige migração de dados específica. Qualquer falha desfaz o lote inteiro.

## Compras, vendas e histórico

`POST /portfolios/buy` e `POST /portfolios/sell` recebem:

```json
{
  "ticker": "PETR4",
  "quantity": "10",
  "price": "30.00",
  "transaction_date": "2026-08-01"
}
```

O ticker deve existir no catálogo. Vendas acima do saldo disponível são rejeitadas. `GET /portfolios/transactions` retorna o histórico do usuário autenticado. Consulte o OpenAPI para as rotas adicionais por ID de carteira e seus schemas completos.

## Avaliação legada e v2

| Leitura | Comportamento |
|---|---|
| `GET /portfolios/positions` | Posições avaliadas pelo preço cadastrado; contrato anterior preservado. |
| `GET /portfolios/summary` | Resumo no formato anterior, sem separação de moedas. |
| `GET /api/v2/portfolios/positions` | Lista de posições abertas com cotação, moeda e origem do preço. |
| `GET /api/v2/portfolios/summary` | Totais por moeda e as cotações utilizadas nessa resposta. |

Cada posição v2 contém `asset`, `quantity`, `average_price`, `cost_basis`, `market_value`, `pnl`, `return_percentage`, `currency` e `quote`. `asset.registered_price` é o cadastro; **`quote.price` é o preço utilizado no cálculo**. Valores monetários são strings decimais; preserve a precisão no cliente.

`quote` contém `asset_id`, `price`, `currency`, `source`, `quoted_at`, `fetched_at` e `from_cache`.

- `source=brapi`: mercado ou cache válido; uma nova cotação não modifica cadastro nem transações.
- `source=manual`: preço cadastrado, com moeda definida e sem símbolo externo. `quoted_at=null`; `fetched_at` indica a leitura do cadastro, não a atualização do preço.
- `from_cache=true`: cotação reutilizada; não informa sozinha a idade do preço da fonte.

O resumo contém `totals_by_currency`, `contains_manual_prices` e `quotes`. Cada grupo contém `currency`, `total_cost`, `total_equity`, `total_pnl`, `return_percentage` e `contains_manual_prices`. BRL, USD e EUR não são somados nem convertidos automaticamente. O P&L cobre posições abertas, sem dividendos ou ganhos realizados.

Carteira vazia retorna `[]` em posições e este resumo:

```json
{
  "totals_by_currency": [],
  "contains_manual_prices": false,
  "quotes": []
}
```

Posições encerradas não exigem cotação. Cada resposta usa sua própria fotografia de preços; posições e resumo consultados separadamente podem refletir horários distintos.

## Erros

| Status | Situação |
|---|---|
| 401 | Credenciais ou JWT inválidos. |
| 403 | Chave administrativa inválida ou ausente. |
| 404 | Recurso não encontrado ou carteira não acessível ao usuário. |
| 409 | Conflito de cadastro ou alteração de moeda protegida pelo histórico. |
| 422 | Entrada inválida, operação incompatível com o saldo ou metadados de avaliação pendentes. |
| 429 | Limite de requisições de autenticação atingido. |
| 503 | Cotação necessária indisponível, inclusive token ausente para ativos configurados com brapi. |

Falhas específicas de avaliação retornam `detail` e `asset_ids`. A API não entrega totais parciais nem substitui silenciosamente uma cotação indisponível por preço manual. Erros de validação de entrada seguem a estrutura do FastAPI, com `detail` em lista; não presuma que todos os erros têm a mesma estrutura.

Compras, vendas, histórico e leituras legadas não dependem de consultar cotações externas. Veja o [guia de operação](operacao.md) antes de ativar as leituras v2 num banco existente.
