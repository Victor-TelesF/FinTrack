# 🏦 FinTrack API

**API REST para gestão de carteiras de investimento com arquitetura de domínio limpa e polimórfica.**

![Python 3.13](https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

---

O **FinTrack** é uma solução robusta para investidores que buscam consolidar carteiras diversificadas. O desafio central do projeto é tratar a rentabilidade de diferentes classes de ativos (renda fixa, variável, cripto) de forma unificada e extensível.

A aplicação utiliza uma **camada de domínio puramente polimórfica**, onde cada ativo adere a um contrato único de cálculo de retorno, permitindo a expansão para novos indexadores ou tipos de ativos sem modificar o núcleo do sistema.

## 📑 Índice

- [🎯 Objetivo do Projeto](#-objetivo-do-projeto)
- [✨ Características Principais](#-características-principais)
- [🛠️ Stack Tecnológica](#-stack-tecnológica)
- [📁 Estrutura e Arquitetura](#-estrutura-e-arquitetura)
- [🌳 Domínio e Polimorfismo](#-domínio-e-polimorfismo)
- [🧠 Decisões de Engenharia](#-decisões-de-engenharia)
- [💻 Exemplo de Uso](#-exemplo-de-uso)
- [🗺️ Roadmap de Endpoints](#-roadmap-de-endpoints)
- [✅ Status e Testes](#-status-e-testes)
- [🚀 Como Executar](#-como-executar)
- [🤝 Créditos](#-créditos)

---

## 🎯 Objetivo do Projeto

Praticar **OOP Avançado** e **Arquitetura Limpa** em um cenário financeiro real. O foco está no isolamento total da lógica de negócio (domínio) em relação aos frameworks (FastAPI) e ferramentas de infraestrutura (SQLAlchemy/PostgreSQL).

## ✨ Características Principais

- **Arquitetura em Camadas:** Pasta `domain/` isolada, sem dependências externas.
- **Hierarquia de Ativos:** Implementação polimórfica abrangendo CDB, Tesouro Direto, Ações (Nacionais/Internacionais), FIIs e Cripto.
- **Cálculo de Rentabilidade:** Uso de *Strategy Pattern* para indexadores (CDI, IPCA, Selic, Prefixado).
- **Precisão Financeira:** Uso rigoroso de `Decimal` para evitar erros de arredondamento.
- **Gestão de Posições:** Cálculo dinâmico de preço médio e quantidade baseado em histórico cronológico de transações.
- **Injeção de Dependência:** Fontes de preço (`PriceSource`) injetadas via Protocolos, facilitando testes e extensibilidade.
- **Persistência Polimórfica:** Hierarquia de ativos mapeada para o banco via *Joined Table Inheritance* (SQLAlchemy 2.0), preservando o polimorfismo do domínio também na camada de dados.

## 🛠️ Stack Tecnológica

| Categoria | Tecnologia |
|---|---|
| **API Framework** | FastAPI + Uvicorn |
| **Persistência** | PostgreSQL + SQLAlchemy 2.0 + Alembic |
| **Validação** | Pydantic v2 + pydantic-settings |
| **Segurança** | JWT (`python-jose` + `pwdlib`) |
| **Testes** | pytest + httpx |
| **Linguagem** | Python 3.13 |

---

## 📁 Estrutura e Arquitetura

O projeto segue a regra de ouro: **A camada de domínio nunca importa nada de infraestrutura.**

```text
domain/                     ← Lógica de Negócio (Python Puro, irmã de app/)
├── assets/                 ← Hierarquia de Ativos e Strategy
├── portfolio/              ← Transaction, Position e Portfolio
├── strategies/             ← Registro de estratégias de rentabilidade
└── protocols.py            ← Contratos (PriceSource, ReturnStrategy)

app/
├── main.py                ← Ponto de entrada da API
├── config.py               ← Settings (pydantic-settings), lê .env
├── database.py             ← Engine, Session e Base (SQLAlchemy 2.0)
├── dependencies.py         ← Dependências FastAPI (get_db, etc.)
├── auth/                   ← Login, JWT e dependências
├── models/                 ← Tabelas SQLAlchemy (Joined Table Inheritance)
├── schemas/                 ← Validação Pydantic
└── routers/                 ← Endpoints FastAPI
```
> `domain/` fica na raiz do projeto, ao lado de `app/` — não dentro dela. A camada de domínio não depende da infraestrutura da API; é o inverso.

---

## 🌳 Domínio e Polimorfismo

### Hierarquia de Ativos
A estrutura de classes permite tratar qualquer ativo de forma genérica:
```text
Asset (ABC)
├── FixedIncome (ABC) -> CDB, GovernmentBond
└── VariableIncome (ABC) -> Stock, RealEstateFund, Cryptocurrency
```

Essa mesma hierarquia é replicada na camada de persistência via **Joined Table Inheritance**: cada classe que adiciona um campo próprio ganha uma tabela própria, ligada por chave estrangeira à tabela pai imediata, com uma coluna discriminadora resolvendo qual subclasse instanciar na leitura.

### Contrato Unificado
Todos os ativos e estratégias seguem a mesma assinatura, garantindo o Princípio de Substituição de Liskov (LSP):
```python
def calculate_return(self, context: ReturnContext) -> Decimal:
    ...
```

---

## 🧠 Decisões de Engenharia

| Decisão | Problema que resolve |
|---|---|
| **Strategy Pattern** | Isola a fórmula de cada indexador, permitindo novos cálculos sem tocar nos ativos. |
| **Factory/Registry** | Garante que o ativo use a estratégia correta para seu indexador automaticamente. |
| **Template Method** | Centraliza validações comuns em `VariableIncome`, evitando duplicação nas subclasses. |
| **Position Calculada** | Preço médio e quantidade são derivados das transações, eliminando riscos de dessincronização. |
| **Indexação por Ticker** | Evita bugs de identidade de objeto ao gerenciar posições em carteira. |
| **PriceSource via Protocol** | Permite trocar fontes de preço (API Real vs Mock) sem recriar objetos da carteira. |
| **Enums em Minúsculo** | Garante compatibilidade com serialização JSON e frontends (case-sensitive). |
| **Posição não persistida** | `posicoes` não vira tabela própria — é recalculada em memória a partir de `transacoes`, reaproveitando a `Position` do domínio já testada, em vez de duplicar a lógica em SQL. |
| **IDs como UUID** | Todas as tabelas usam `UUID` em vez de `int` autoincremento — não previsível e consistente com os identificadores já usados no domínio (`Transaction`, `Portfolio`). |
| **Joined Table Inheritance** | Mapeia a hierarquia polimórfica de `Asset` sem colunas `NULL` sobrando (Single Table) nem duplicação de campos comuns (Concrete Table). |

---

## 💻 Exemplo de Uso

A camada de domínio é totalmente funcional de forma independente:

```python
from decimal import Decimal
from domain.assets.variable_income.stock.national_stock import NationalStock
from domain.portfolio.portfolio import Portfolio

# Configuração
petr4 = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("35.50"))
portfolio = Portfolio(wallet_id="user-123")

# Operação
portfolio.buy(asset=petr4, quantity=Decimal("100"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))

# Resultados
print(portfolio.positions["PETR4"].average_price) # 30.00
print(portfolio.get_total_pnl(MyPriceSource()))   # Lucro baseado em mercado
```

---

## 🗺️ Roadmap de Endpoints

### Autenticação
- `POST /auth/register`
- `POST /auth/login`

### Gestão de Carteiras
- `GET  /carteiras/`
- `POST /carteiras/`
- `GET  /carteiras/{id}/resumo`
- `POST /carteiras/{id}/comprar`
- `POST /carteiras/{id}/vender`

### Ativos e Alertas
- `GET  /ativos/`
- `POST /alertas/`

---

## ✅ Status e Testes

- [x] **Etapa 1 — Ativos:** Concluída (Polimorfismo, Strategy, Fisher).
- [x] **Etapa 2 — Carteira:** Concluída (Transactions, Position, Portfolio).
- [ ] **Etapa 3 — Persistência:** 🚧 Em andamento — `config.py`, `database.py` e `dependencies.py` concluídos; modelos SQLAlchemy da hierarquia de ativos (Joined Table Inheritance) em progresso.
- [ ] **Etapa 4 — Autenticação:** JWT.
- [ ] **Etapa 5 — API:** Endpoints finais.

**Qualidade:** Suíte de **110 testes unitários** com 100% de sucesso, cobrindo regras de negócio complexas como processamento cronológico de preço médio e proteção contra saldo insuficiente.

---

## 🚀 Como Executar

1. Clone o repositório.
2. Configure o `.env` (Postgres).
3. `docker compose up --build`.

Acesse em `http://localhost:8000`.

---

## 🤝 Créditos

Desenvolvido por [@Victor_TelesF](https://github.com/Victor-TelesF). 
O projeto conta com apoio técnico do **Claude (Anthropic)** como revisor de arquitetura e tutor de OOP, garantindo que as decisões de design sigam as melhores práticas de mercado.

---

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.