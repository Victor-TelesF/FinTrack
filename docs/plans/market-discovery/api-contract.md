# Contrato pretendido — pesquisa e primeira compra

Estado em 02/10/2026: contrato de descoberta/primeira compra da etapa 0, **implementado até identidade do catálogo e migration na etapa 3a**. Etapas 1, 2a e 2b também concluídas. Rotas atuais estão em [docs/api.md](../../api.md). A próxima etapa autorizável é o cadastro transacional na primeira compra (3b); a remoção administrativa continua posterior.

## Saúde operacional — implementada na etapa 1

| Rota pública, sem JWT | Contrato implementado |
|---|---|
| `GET /health/live` | 200, `{"status":"alive"}`; sem consulta ao banco ou provedor. |
| `GET /health/ready` | 200, `{"status":"ready"}` se `SELECT 1` concluir; 503, `{"status":"unavailable"}` em falha/TLS/pool/timeout. |

Sem detalhes do driver, credenciais, hostname privado ou stacktrace nas respostas. Prazo total configurável, padrão 3 s; usa o pool da API. Readiness valida conectividade, não cotação nem revisão de schema: release explícita deve preceder a API. Endpoints fora do OpenAPI por serem operacionais; snapshot dos contratos de produto preservado. Configuração URL/TLS/pool e sequência release/API estão em [operação](../../operacao.md). Estas adições não antecipam a etapa 2a/2b.

## Tipos e autenticação

As duas novas rotas exigem o JWT do FinTrack em `Authorization: Bearer <token>`. A chave brapi fica exclusivamente no backend. Tipos iniciais: `national_stock` e `real_estate_fund`. Pesquisa e cadastro novo de cripto ficam pendentes de uma fonte gratuita; os tipos antigos continuam em carteiras existentes.

## Identidade do catálogo — etapa 3a

Ticker identifica um ativo no catálogo local por `upper(btrim(ticker))`. Novos registros são gravados em maiúsculas, com espaços externos removidos; lookups e upserts usam a mesma forma. Um índice único de expressão no PostgreSQL rejeita duplicidades por case/espaços. Ativos antigos mantêm seus IDs e a grafia original do ticker; a migration não os renomeia nem os deduplica.

Se a migration encontrar mais de uma linha para a mesma identidade normalizada, ela aborta com a quantidade de grupos conflitantes antes de alterar o schema ou as linhas. `asset.name` usa `TEXT`, sem limite de 50 caracteres; o downgrade só reduz o campo se todos os nomes couberem no tamanho antigo, sem truncamento.

O serviço get-or-create não confirma a transação do chamador. Em disputa concorrente, trata a violação do índice dentro de savepoint e devolve o registro compatível já criado. Um ticker igual com tipo, moeda ou identidade externa incompatíveis não atualiza o registro existente; o nome/preço/metadados já cadastrados também não são substituídos por um candidato concorrente.

## MarketAsset

| Campo | Tipo e regra |
|---|---|
| `ticker` | String; símbolo canônico confirmado pelo provedor, sem mapear renomes/conversões silenciosamente. |
| `name` | String não vazia fornecida pelo provedor; não inventar razão social quando ele fornecer apenas o ticker. |
| `asset_type` | `national_stock` ou `real_estate_fund`, por `assetType`/`subType`. |
| `quote_currency` | `BRL` nesta entrega, confirmada no metadado/cotação. |
| `quote` | Objeto abaixo ou `null` quando a pesquisa não trouxer cotação válida. |

Cotação: `price` decimal positivo/finito como string; `currency`; `source` (inicialmente `brapi`); `quoted_at` ISO 8601 UTC ou `null`; `fetched_at` ISO 8601 UTC da consulta pelo backend. Horário da consulta não substitui horário de mercado. Não retornar `from_cache` como novo requisito de descoberta nem imprimir segredos. Os schemas v2 existentes mantêm seu próprio contrato.

## GET /assets/search

Exemplo: `/assets/search?q=HGLG&type=real_estate_fund&page=1&limit=20`.

| Parâmetro | Contrato inicial |
|---|---|
| `q` | Obrigatório; strip; 1–50 caracteres após normalização. Busca parcial por ticker/nome conforme cobertura do provedor. |
| `type` | Obrigatório; um dos dois tipos suportados. Uma família por página evita totais incorretos ao misturar mercados. |
| `page` | Inteiro >= 1, padrão 1. |
| `limit` | Inteiro 1–100, padrão 20. |

Mapear `national_stock` para `type=stock&subType=stock`; `real_estate_fund` para `type=fund&subType=fii`. Garantir classificação dos itens e paginação do conjunto suportado, não filtrar uma página ampla e reaproveitar totais errados. Subtipo desconhecido ou resposta inconsistente é falha de contrato do provedor; nunca anunciar ETF/unit/BDR como ação/FII.

Resposta 200 (exemplo sintético, preços/horários não são cotação real):

```json
{
  "items": [{
    "ticker": "HGLG11",
    "name": "HGLG11",
    "asset_type": "real_estate_fund",
    "quote_currency": "BRL",
    "quote": {
      "price": "150.25",
      "currency": "BRL",
      "source": "brapi",
      "quoted_at": null,
      "fetched_at": "2026-10-02T12:00:00Z"
    }
  }],
  "page": 1,
  "limit": 20,
  "total_items": 1,
  "total_pages": 1,
  "has_next_page": false
}
```

Busca sem resultado: `items: []`, `total_items: 0`, `total_pages: 0`, `has_next_page: false`, preservando page/limit pedidos. Página além do fim retorna 200 com lista vazia, totais válidos do conjunto e `has_next_page: false`.

A pesquisa funciona com catálogo vazio, sem criar ativos. Utilizar cotação resumida já fornecida pela listagem, se válida; nenhuma chamada individual de preços por item. `quoted_at` ausente permanece `null`. Cache de pesquisa não persiste instrumentos no banco.

## GET /assets/market/{ticker}

Exemplo: `/assets/market/PETR4`. Normalizar espaços/case; validar símbolo com a capacidade do provedor. Resolver identidade por metadados e selecionar **correspondência exata**; PETR4 não pode ser substituída por PETR4F nem por um renome.

Resposta 200: um `MarketAsset`. Após confirmar o tipo suportado/BRL e atividade, consultar cotação completa com o adaptador existente. Identidade/moeda/preço precisam ser válidos. Se a cotação necessária falhar, responder 503; não substituir por preço de operação ou zero. Nenhuma persistência nessa rota.

Registrar `/search` e `/market/{ticker}` antes de `/{asset_id}`. `GET /assets` e `GET /assets/{asset_id}` continuam lendo exclusivamente registros locais.

## Erros novos

Novos erros esperados usam corpo mínimo `{"detail": "mensagem"}`. Falhas Pydantic mantêm o formato padrão de validação. Não alterar os erros legados de autenticação, compra/venda ou v2 para acomodar descoberta.

| Condição | Status e detalhe pretendido |
|---|---|
| JWT ausente/inválido | 401 conforme contrato atual do FinTrack. |
| Query/ticker sintaticamente inválido; tipo não suportado na query | 422, validação FastAPI/Pydantic. |
| Ticker não existe no provedor | 404, `Ativo de mercado não encontrado`. Busca sem resultado é 200. |
| Ticker existe mas instrumento não é suportado | 422, `Tipo de ativo de mercado não suportado`. |
| Renome/conversão/identidade ambígua/inatividade | 422, `Identidade de ativo de mercado exige revisão`. |
| Credencial externa ausente, 401 ou 403 do provedor | 503, `Fonte de dados de mercado indisponível`. Nunca retornar mensagem de JWT expirado. |
| Timeout, rede, 5xx, JSON inválido, moeda/preço incompatíveis | 503, `Fonte de dados de mercado indisponível`. |
| Limite externo 429 | 503, `Limite da fonte de dados de mercado atingido`; `Retry-After` sanitizado quando disponível. Não confundir com 429 de login do usuário. |

Não expor corpo bruto, URL com credenciais, nomes de variáveis secretas ou stacktrace. Respeitar cooldown/limite compartilhado com cotações.

## POST /portfolios/buy e /portfolios/sell

Preservar payload e resposta `TransactionRead` existentes; não adicionar tipo, provedor ou metadados obrigatórios enviados pelo cliente.

```json
{
  "ticker": "PETR4",
  "quantity": "2",
  "price": "35.50",
  "transaction_date": "2026-10-02"
}
```

Se ativo local existir, usar o registro/histórico atual, sem recadastro nem atualização de preço/tipo/moeda por uma compra. Se ausente **na compra**, validar no provedor, confirmar tipo suportado, obter metadados/cotação, depois cadastrar e gravar compra atomicamente. Ticker canônico novo em uppercase; não reescrever tickers antigos de carteiras.

`price` permanece preço da operação, inclusive quando difere da cotação. `current_price` inicial do catálogo usa a cotação validada; as leituras legadas continuam usando esse preço cadastrado. As leituras v2 buscam mercado e mantêm origem/horários/totais por moeda. Uma compra posterior não altera a avaliação de outros usuários por sobrescrever preço cadastrado.

Erros de descoberta se aplicam à compra de ticker novo. Falha de validação/transação deve desfazer também o novo ativo. Reconsulta/constraint tratam concorrência sem duplicidade. Não manter lock de carteira durante HTTP; resolver primeiro, adquirir locks/revalidar depois.

Venda mantém regra atual: exige ativo local e saldo; ticker ausente não dispara descoberta/cadastro, retorna a falha legada. Operações com tipos antigos continuam funcionando como antes. Remover admin somente após verificar esse fluxo; não oferecer outra API administrativa nesta entrega.

## Compatibilidade e evolução

Preservar `GET /portfolios/transactions`, positions/summary legados e `GET /api/v2/portfolios/positions|summary`, UUIDs, datas, quantidades, preços e ordem persistida. Não regenerar snapshots antigos para esconder regressões.

Novo provedor deve preencher estes objetos e implementar descoberta/cotações, sendo selecionado por registro/capacidade. Adicionar fonte não exige mudar os cálculos de carteira. Antes de cripto, decidir identidade quando houver símbolo compartilhado entre moedas/mercados e moeda dos custos; não inferir essas informações de posições antigas.
