markdown
<p align="center">
<img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" />
</p>

<h1 align="center">🏦 FinTrack API</h1>

<p align="center">
    <b>API REST para gestão de carteiras de investimento</b><br>
  Arquitetura limpa, domínio polimórfico e cálculo de rentabilidade unificado para múltiplas classes de ativos.
</p>

---

## 📌 Sobre o Projeto

O **FinTrack** ataca um problema real do mercado financeiro: **como consolidar e calcular rentabilidade de ativos distintos** (CDBs indexados ao CDI, Tesouro IPCA+/Selic, Ações nacionais/internacionais, FIIs e Cripto) em uma única carteira, sem perder precisão nem extensibilidade.

O desafio central foi projetar uma camada de domínio puramente polimórfica, onde cada ativo adere a um contrato único de cálculo de retorno. Isso permite adicionar novos indexadores ou tipos de ativos **sem modificar o núcleo do sistema** — aplicação prática de OOP avançado, Strategy Pattern e do Princípio Aberto/Fechado (OCP).

> 💡 Projeto construído do zero como exercício de arquitetura de software, com foco em separação estrita entre domínio e infraestrutura. O domínio financeiro foi escolhido por exigir regras de negócio rigorosas (precisão decimal, processamento cronológico de transações), tornando o desafio mais interessante do que um CRUD comum.

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Por que foi escolhida |
|--------|-----------|----------------------|
| **API** | FastAPI + Uvicorn | Geração automática de docs e tipagem nativa via Pydantic |
| **Persistência** | PostgreSQL + SQLAlchemy 2.0 + Alembic | ORM moderno com tipagem e migrations versionadas |
| **Validação** | Pydantic v2 | Validação de dados robusta e integração nativa com FastAPI |
| **Segurança** | python-jose + pwdlib | Autenticação JWT stateless: hash de senha, emissão e validação de token |
| **Testes** | pytest + httpx | Testes unitários e de integração com cliente HTTP |
| **Infra** | Docker + Docker Compose | Ambiente reproduzível em qualquer máquina |

---

## 🏗️ Arquitetura

O projeto segue a **regra de ouro da Arquitetura Limpa**: a camada de domínio **nunca** importa nada de infraestrutura — é o inverso: `app/` depende de `domain/`, nunca ao contrário.

```text
fintrack/
├── domain/                  # Lógica de negócio, Python puro
│   ├── assets/              # Hierarquia polimórfica de ativos
│   ├── portfolio/           # Transaction, Position e Portfolio
│   ├── strategies/          # Cálculo por indexador
│   └── protocols.py         # PriceSource e ReturnStrategy
├── app/                     # Infraestrutura e camada HTTP
│   ├── main.py              # Ponto de entrada da API
│   ├── config.py            # Settings via pydantic-settings
│   ├── database.py          # Engine, Session e Base
│   ├── dependencies.py      # Injeção de dependências FastAPI
│   ├── auth/                # PasswordHandler e TokenHandler
│   ├── mappers/             # Conversão ORM <-> domínio
│   ├── price_source.py      # Fonte de preços persistidos
│   ├── service/             # Services da aplicação
│   ├── errors/              # Exceções e handlers HTTP
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Contratos Pydantic
│   └── routers/             # Endpoints da API
├── alembic/                 # Migrations versionadas
├── tests/                   # Testes unitários e de integração
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
└── .env.example
```


### 🌳 Hierarquia de Domínio

```text
Asset (ABC)
├── FixedIncome (ABC)
│   ├── CDB
│   └── GovernmentBond
└── VariableIncome (ABC)
    ├── Stock (ABC)
    │   ├── NationalStock
    │   └── InternationalStock
    ├── RealEstateFund
    └── Cryptocurrency
```


Essa hierarquia é replicada na camada de persistência via **Joined Table Inheritance** (SQLAlchemy 2.0): cada classe que adiciona um campo próprio ganha uma tabela própria, ligada por chave estrangeira à tabela pai imediata, preservando o polimorfismo do domínio também no banco.

---

## 🧠 Decisões de Engenharia

| Decisão | Problema que resolve |
|---------|---------------------|
| **Strategy Pattern** | Isola a fórmula de cada indexador. Novo cálculo = nova classe, sem tocar nos ativos existentes. |
| **Factory/Registry** | Garante que cada ativo use a estratégia correta para seu indexador automaticamente. |
| **Template Method** | Centraliza validações comuns em `VariableIncome`, evitando duplicação nas subclasses. |
| **Position calculada em memória** | Preço médio e quantidade são derivados do histórico de transações — elimina risco de dessincronização. Não vira tabela própria: é recalculada a partir da lista de transações, reaproveitando a `Position` do domínio já testada. |
| **PriceSource via Protocol** | Permite trocar fontes de preço (API real vs. mock) sem acoplar o domínio a uma implementação concreta. |
| **IDs como UUID** | Identificadores não previsíveis, consistentes entre domínio e banco. |
| **Joined Table Inheritance** | Mapeia a hierarquia polimórfica de `Asset` sem colunas `NULL` sobrando (Single Table) nem duplicação de campos comuns (Concrete Table). |
| **JWT stateless via `get_current_user`** | Protege rotas sem consultar estado de sessão a cada request — a validação (assinatura + expiração) é puramente criptográfica; o usuário só é buscado no banco depois de o token já ser confirmado válido. |

---

## 💻 Exemplo de Uso

A camada de domínio é totalmente funcional e testável de forma independente — sem banco de dados, sem servidor HTTP:

```python
from decimal import Decimal
from datetime import date
from domain.assets.variable_income import NationalStock
from domain.portfolio.portfolio import Portfolio

# Configuração
petr4 = NationalStock(
    name="Petrobras",
    ticker="PETR4",
    current_price=Decimal("35.50")
)
portfolio = Portfolio(wallet_id="user-123")

# Operação
portfolio.buy(
    asset=petr4,
    quantity=Decimal("100"),
    price=Decimal("30.00"),
    buy_date=date(2026, 1, 5)
)

# Resultados
print(portfolio.positions["PETR4"].average_price)  # 30.00
# portfolio.get_total_pnl(price_source) calcula o lucro com uma PriceSource.
```

---

## ✅ Testes

```bash
# Rodar todos os testes
pytest

# Com cobertura
pytest --cov=domain --cov=app --cov-report=html

# Verbose
pytest -v
```

**Resultado atual:** 156 testes com **100% de aprovação**, cobrindo:
- Processamento cronológico de preço médio (compras e vendas intercaladas)
- Proteção contra saldo insuficiente
- Cálculo de rentabilidade por indexador (CDI, IPCA, Selic, Prefixado)
- Hierarquia polimórfica de ativos e sincronização de estratégia após troca de indexador
- Autenticação: hash/verificação de senha, emissão e validação de token JWT, registro e login via API, e resolução de usuário autenticado a partir do token (`get_auth_user`)
- Catálogo de ativos com upsert administrativo e leitura autenticada
- Compra, venda, histórico, posições, preço médio, P&L e resumo da carteira

---

## 🚀 Como Executar

### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [Git](https://git-scm.com/)

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/Victor-TelesF/fintrack.git
cd fintrack

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais do PostgreSQL

# 3. Suba a aplicação com Docker
# O serviço web executa as migrations antes de iniciar a API.
docker compose up --build

# 4. Acesse a API
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

Para aplicar migrations manualmente depois de uma alteração:

```bash
docker compose exec web alembic upgrade head
```

### Variáveis de ambiente (.env)

O projeto usa `pydantic-settings` para ler a configuração — veja `.env.example` para o modelo completo:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-a-strong-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=fintrack

SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_KEY=replace-with-a-long-random-admin-key
```

---

## 📋 Roadmap

- [x] Modelagem polimórfica de ativos (CDB, Tesouro, Ações, FIIs, Cripto)
- [x] Cálculo de rentabilidade com Strategy Pattern
- [x] Gestão de carteiras, transações e posições (domínio puro)
- [x] Persistência com SQLAlchemy 2.0 + Joined Table Inheritance
- [x] Migrations com Alembic
- [x] Schemas Pydantic (Create/Read)
- [x] Autenticação JWT (registro, login, dependência de usuário autenticado)
- [x] Service layer e mapeamento ORM ↔ domínio
- [x] Endpoints REST de ativos, carteiras, transações, posições e resumo
- [x] 156 testes unitários e de integração
- [ ] Refresh token (access token curto + revogação de sessão)
- [ ] Alertas de preço (Observer Pattern)

### Endpoints principais

| Método | Endpoint | Autenticação |
|--------|----------|--------------|
| `POST` | `/auth/register` | Não |
| `POST` | `/auth/login` | Não |
| `GET` | `/assets` | JWT |
| `GET` | `/assets/{asset_id}` | JWT |
| `POST` | `/admin/assets` | `X-Admin-Key` |
| `GET` | `/portfolios` | JWT |
| `POST` | `/portfolios/buy` | JWT |
| `POST` | `/portfolios/sell` | JWT |
| `GET` | `/portfolios/transactions` | JWT |
| `GET` | `/portfolios/positions` | JWT |
| `GET` | `/portfolios/summary` | JWT |

Ativos são cadastrados ou atualizados exclusivamente pelo endpoint administrativo. O payload aceita uma lista mista de CDBs, títulos públicos, ações, FIIs e criptomoedas. O usuário comum apenas consulta o catálogo e registra operações usando o ticker.

---

## 🎓 O que Aprendi

- Como isolar 100% a lógica de negócio de frameworks, tornando o domínio testável sem banco de dados ou servidor HTTP.
- Aplicação prática do **Princípio Aberto/Fechado (OCP)**: adicionar um novo indexador ou tipo de ativo sem modificar código existente.
- Mapeamento de herança polimórfica para banco relacional com **Joined Table Inheritance**.
- Importância de `Decimal` sobre `float` em cálculos financeiros para evitar erros de arredondamento silenciosos.
- Como projetar testes que validam regras de negócio complexas de forma isolada, incluindo regressões (ex: processamento cronológico de transações fora de ordem de inserção).
- Como compor dependências do FastAPI em cadeia (`Depends` encadeado) para autenticação JWT stateless, mantendo a lógica de negócio (consulta ao banco) fora da camada de wiring.

---

## 🤝 Créditos

Desenvolvido por [@Victor_TelesF](https://github.com/Victor-TelesF).

---

## 📝 Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE) para mais informações.