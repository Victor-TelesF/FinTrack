"""
Fixtures compartilhadas para a suíte de testes do domínio FinTrack.

IMPORTANTE: ajuste os imports em cada arquivo de teste para o caminho real
dos seus módulos (chutei `app.domain.*` com base na estrutura vista no
VS Code). Os monkeypatches de `reference_date` também assumem que cada
módulo faz `from ...reference_date import reference_date` (ou caminho
relativo equivalente) — se o nome do import mudar, ajuste o alvo do patch.
"""
from datetime import date
from decimal import Decimal

import pytest


# Data de referência fixa para tornar os testes determinísticos,
# independente de quando forem executados.
FROZEN_TODAY = date(2026, 6, 1)


@pytest.fixture
def frozen_today():
    return FROZEN_TODAY


@pytest.fixture
def past_date():
    """Uma data no passado em relação a FROZEN_TODAY — válida para transaction_date."""
    return date(2026, 1, 5)


@pytest.fixture
def future_date():
    """Uma data no futuro em relação a FROZEN_TODAY — válida para maturity_date."""
    return date(2030, 1, 1)


@pytest.fixture
def fake_price_source():
    """
    Implementação simples de PriceSource (Protocol) para testes,
    sem precisar de mock de biblioteca externa nenhuma.
    """
    class FakePriceSource:
        def __init__(self, prices: dict[str, Decimal]):
            self._prices = prices

        def get_latest_price(self, ticker: str) -> Decimal:
            if ticker not in self._prices:
                raise KeyError(f"Preço não disponível para o ticker {ticker}")
            return self._prices[ticker]

    return FakePriceSource
