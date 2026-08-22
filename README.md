markdown
<p align="center">
<img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <a href="https://github.com/Victor-TelesF/fintrack/actions/workflows/ci.yml">
    <img src="https://github.com/Victor-TelesF/fintrack/actions/workflows/ci.yml/badge.svg" />
  </a>
  <!-- Se o arquivo não se chamar ci.yml, troca o caminho acima pelo nome real do arquivo em .github/workflows/ -->
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" />
</p>

<h1 align="center">🏦 FinTrack API</h1>

<p align="center">
    <b>API REST para consolidar rentabilidade de ativos diferentes numa única carteira</b><br>
  CDBs indexados ao CDI, Tesouro Selic/IPCA+, ações, FIIs e cripto — cada um com sua própria fórmula de retorno, tratados de forma unificada.
</p>

<p align="center">
  <a href="https://fintrack-ye2t.onrender.com/docs"><b>🔗 API rodando ao vivo — Swagger interativo</b></a>
</p>

<!--
Opcional: GIF curto (5-10s) mostrando login → POST /portfolios/buy → GET /portfolios/summary
gravado a partir do link acima. Ferramentas: Peek (Linux), ScreenToGif (Windows).
-->

<p align="center">
  <a href="#-como-executar">Como rodar</a> ·
  <a href="#-endpoints-principais">Endpoints</a> ·
  <a href="#-decisões-de-engenharia">Decisões técnicas</a> ·
  <a href="#-o-que-aprendi">O que aprendi</a>
</p>

---

## 📌 Por que este projeto existe

Consolidar uma carteira com CDB, Tesouro e ações num só número de rentabilidade não é trivial: cada tipo de ativo calcula retorno de um jeito diferente (indexador × taxa, valorização de cota + dividendo, ganho de capital simples). Tratar tudo com `if/else` funciona até o terceiro tipo de ativo — depois disso vira uma fonte constante de bugs cada vez que um indexador novo entra.

O FinTrack é minha resposta a esse problema: uma API onde cada classe de ativo sabe calcular o próprio retorno, e adicionar um indexador novo não exige tocar em nada que já existe e já está testado.

---

## 🛠️ Stack

| Camada | Tecnologia | Por que |
|--------|-----------|---------|
| API | FastAPI + Uvicorn | Tipagem nativa via Pydantic, docs automáticas |
| Persistência | PostgreSQL + SQLAlchemy 2.0 + Alembic | ORM tipado, migrations versionadas |
| Autenticação | python-jose + pwdlib | JWT stateless, hash de senha com salt |
| Testes | pytest + httpx | Unitários de domínio + integração via API |
| Infra | Docker Compose | Ambiente reproduzível |

---

## 🏗️ Arquitetura

Regra que segui do início ao fim: `domain/` (Python puro, sem framework) nunca importa nada de `app/` (FastAPI, SQLAlchemy). A dependência é sempre numa direção só.

```text
fintrack/
├── domain/          # Regras de negócio, zero dependência externa
│   ├── assets/       # Hierarquia de ativos e cálculo de retorno
│   ├── portfolio/     # Transaction, Position, Portfolio
│   └── strategies/    # Uma classe por indexador (CDI, IPCA, Selic, Prefixado)
├── app/              # FastAPI, banco, autenticação
│   ├── routers/        # Endpoints
│   ├── service/          # Regras de aplicação (orquestra domínio + banco)
│   ├── models/            # SQLAlchemy
│   └── mappers/            # Converte ORM ↔ domínio
├── alembic/          # Migrations
└── tests/            # domain/ testado sem banco nenhum; app/ testado via API
```

**Por que separar assim:** a suíte de testes do domínio inteiro roda sem subir Postgres — dá pra validar toda a lógica de cálculo de rentabilidade em milissegundos, sem depender de infraestrutura.

```text
Asset (ABC)
├── FixedIncome (ABC) ── CDB, GovernmentBond
└── VariableIncome (ABC) ── Stock (NationalStock, InternationalStock), RealEstateFund, Cryptocurrency
```

---

## 🧠 Decisões de Engenharia

Em vez de listar padrões pelo nome, aqui está o problema que cada um resolveu de fato:

| Problema real | Decisão | Sem isso... |
|---|---|---|
| Cada indexador (CDI, IPCA, Selic, taxa fixa) calcula retorno com uma fórmula diferente, e novos indexadores vão continuar aparecendo | Strategy Pattern: uma classe por fórmula, escolhida via registry | Toda vez que um indexador novo entrasse, eu precisaria editar um `if/elif` gigante e arriscar quebrar os já existentes |
| Preço médio e quantidade da carteira podem ficar dessincronizados do histórico de transações se forem guardados como colunas separadas | `Position` recalcula tudo a partir da lista de transações, em memória | Um bug de update em background podia deixar o preço médio mostrado errado sem nenhum erro visível |
| O domínio precisa buscar preço de mercado, mas não pode depender de como esse preço é obtido (banco hoje, API externa amanhã) | `PriceSource` como `Protocol` — o domínio só conhece a interface | Trocar a fonte de preço exigiria reescrever a lógica de cálculo de P&L, não só a integração |
| Cada tipo de ativo tem colunas próprias (CDB tem `fgc_covered`, ação tem `currency`), mas todos compartilham `name`/`ticker`/`current_price` | Joined Table Inheritance no SQLAlchemy | Ou eu teria uma tabela com dezenas de colunas `NULL` pra maioria das linhas, ou duplicaria os campos comuns em cada tabela |

---

## 💻 Exemplo de uso

A camada de domínio funciona isolada — sem banco, sem servidor HTTP:

```python
from decimal import Decimal
from datetime import date
from domain.assets.variable_income import NationalStock
from domain.portfolio.portfolio import Portfolio

petr4 = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("35.50"))
portfolio = Portfolio(wallet_id="user-123")

portfolio.buy(asset=petr4, quantity=Decimal("100"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))

print(portfolio.positions["PETR4"].average_price)  # 30.00
```

---

## ✅ Testes

```bash
pytest                                          # todos
pytest --cov=domain --cov=app --cov-report=html # com cobertura
```

Mais de 160 testes, a maioria de domínio (sem banco) e o resto de integração via API. CI no GitHub Actions roda a suíte a cada push/PR contra um Postgres real em container, aplicando as migrations do zero antes de testar — não é só um lint, é a suíte completa validando contra o schema real do banco.

**Um bug real que a suíte pegou:** minha primeira versão de `average_price` processava as transações na ordem em que chegavam no banco. Um teste de regressão simulou uma venda entre duas compras da mesma ação e o preço médio deu errado — porque a venda "resetava" o cálculo em vez de simplesmente reduzir a quantidade sem afetar o preço médio. A correção foi ordenar sempre por `transaction_date` antes de calcular, nunca confiar na ordem de inserção. Ficou como teste de regressão (`test_sell_between_two_buys_does_not_corrupt_average`) pra nunca mais quebrar silenciosamente.

---

## 🚀 Como Executar

### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [Git](https://git-scm.com/)

```bash
git clone https://github.com/Victor-TelesF/fintrack.git
cd fintrack
cp .env.example .env   # edite com suas credenciais do Postgres
docker compose up --build
```

- API: `http://localhost:8000`
- Docs interativas: `http://localhost:8000/docs`

Para aplicar migrations manualmente:
```bash
docker compose exec web alembic upgrade head
```

🔗 **Ambiente ao vivo (sem precisar rodar nada):** [fintrack-ye2t.onrender.com/docs](https://fintrack-ye2t.onrender.com/docs) — Swagger interativo, dá pra testar os endpoints direto no navegador. *(Plano free do Render: se ninguém acessou nos últimos minutos, o primeiro request pode levar ~30s pra "acordar" o serviço.)*

---

## 📋 Endpoints principais

| Método | Endpoint | Autenticação |
|--------|----------|--------------|
| `POST` | `/auth/register` | Não |
| `POST` | `/auth/login` | Não |
| `GET` | `/assets` | JWT |
| `POST` | `/admin/assets` | `X-Admin-Key` |
| `GET` | `/portfolios` | JWT |
| `POST` | `/portfolios/buy` | JWT |
| `POST` | `/portfolios/sell` | JWT |
| `GET` | `/portfolios/positions` | JWT |
| `GET` | `/portfolios/summary` | JWT |

Exemplo de compra:
```json
{
  "ticker": "PETR4",
  "quantity": "10",
  "price": "35.50",
  "transaction_date": "2026-08-01"
}
```

Valores financeiros trafegam como strings decimais (evita perda de precisão no JSON/JavaScript). Erros seguem `{ "detail": "mensagem" }`, com `401`/`403`/`404`/`409`/`422` conforme o caso.

---

## 🎓 O que Aprendi

- **`Decimal`, nunca `float`, em cálculo financeiro.** Erro de arredondamento silencioso em dinheiro é o tipo de bug que só aparece em produção, meses depois.
- **Testar domínio isolado antes de integrar economiza tempo de debug.** Achar o bug de preço médio num teste unitário de domínio levou minutos; achar o mesmo bug via API, com banco no meio, teria levado muito mais.
- **Ordem cronológica de eventos de negócio não pode depender de ordem de inserção no banco.** Parece óbvio escrito assim, mas só ficou óbvio depois do bug acima.
- **Usei assistentes de IA (Claude Code, com revisão via GPT/Kimi) para partes de infraestrutura mais mecânicas** — rotas, mappers ORM, migrations — sempre a partir de uma spec que eu escrevi antes e revisando o código gerado linha a linha. Aprendi que isso acelera a digitação, mas não substitui entender o problema: mais de uma vez rejeitei uma "correção" sugerida porque ela escondia o sintoma em vez de resolver a causa.
- Ainda não sei se a modelagem de domínio que fiz aqui aguenta bem, por exemplo, ativos com múltiplas moedas de forma limpa — é uma pergunta em aberto que quero investigar.

---

## 📋 Próximos Passos

- [ ] Migrar o backend para async (SQLAlchemy async engine, rotas e services assíncronos)
- [ ] Substituir a fonte de preço atual (lida do próprio banco) por um provedor de mercado real

---

## 🤝 Contato

[@Victor_TelesF](https://github.com/Victor-TelesF)
<!-- TODO: adicionar link do LinkedIn -->

---

## 📝 Licença

MIT. Veja [`LICENSE`](LICENSE).