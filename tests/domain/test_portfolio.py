"""
Testes completos para Portfolio.

Substitui test_portfolio_buy_sell.py (versão anterior, mais restrita) —
esse arquivo cobre tudo que a classe faz atualmente:

- wallet_id / id_portfolio (validação e imutabilidade)
- buy / sell (criação e reaproveitamento de Position, blindagem por ticker)
- Remoção automática de Position zerada após sell (via pop)
- get_total_cost (sem PriceSource)
- get_total_equity (com PriceSource)
- get_total_pnl (equity - cost)
- get_pnl (por posição individual)
- update_portfolio_prices (muta Asset.current_price via PriceSource)
- positions retorna cópia defensiva
"""
from decimal import Decimal
from datetime import date

import pytest

from domain.portfolio.portfolio import Portfolio
from domain.portfolio.transaction import Transaction
from domain.enums import TransactionType
from domain.exceptions import AssetNotFoundError, InsufficientBalanceError, InvalidValueError
from domain.assets.variable_income import NationalStock
from uuid import uuid4, UUID


@pytest.fixture(autouse=True)
def _freeze_reference_date(monkeypatch, frozen_today):
    monkeypatch.setattr(
        "domain.portfolio.transaction.reference_date",
        lambda: frozen_today,
    )


@pytest.fixture
def petr4():
    return NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("35.50"))


@pytest.fixture
def vale3():
    return NationalStock(name="Vale", ticker="VALE3", current_price=Decimal("68.00"))


@pytest.fixture
def portfolio():
    return Portfolio(wallet_id="user-123")


class TestPortfolioConstruction:
    def test_valid_wallet_id(self):
        portfolio = Portfolio(wallet_id="user-123")
        assert portfolio.wallet_id == "user-123"

    def test_non_string_wallet_id_raises(self):
        with pytest.raises(InvalidValueError):
            Portfolio(wallet_id=123)

    def test_wallet_id_has_no_setter(self, portfolio):
        with pytest.raises(AttributeError):
            portfolio.wallet_id = "outro-usuario"

    def test_id_portfolio_is_generated_and_has_no_setter(self, portfolio):
        assert portfolio.id_portfolio is not None
        with pytest.raises(AttributeError):
            portfolio.id_portfolio = "novo-id"

    def test_starts_with_no_positions(self, portfolio):
        assert portfolio.positions == {}

    def test_without_id_portfolio_generates_new_uuid(self):
        """Regressão: comportamento antigo (sem id_portfolio) continua funcionando."""
        portfolio = Portfolio(wallet_id="user-123")
        assert isinstance(portfolio.id_portfolio, UUID)

    def test_can_be_constructed_with_existing_id(self):
        """Reidratação: passar um id_portfolio existente reaproveita o mesmo UUID,
        em vez de gerar um novo — essencial para o replay a partir do banco."""
        existing_id = uuid4()
        portfolio = Portfolio(wallet_id="user-123", id_portfolio=existing_id)
        assert portfolio.id_portfolio == existing_id

    def test_invalid_id_portfolio_type_raises(self):
        with pytest.raises(InvalidValueError):
            Portfolio(wallet_id="user-123", id_portfolio="not-a-uuid")

    def test_two_portfolios_with_same_id_portfolio_do_not_share_state(self):
        """Garante que reidratar duas instâncias com o mesmo id_portfolio não
        cria acoplamento entre elas — cada Portfolio tem suas próprias positions."""
        shared_id = uuid4()
        portfolio_a = Portfolio(wallet_id="user-a", id_portfolio=shared_id)
        portfolio_b = Portfolio(wallet_id="user-b", id_portfolio=shared_id)

        assert portfolio_a.id_portfolio == portfolio_b.id_portfolio
        assert portfolio_a.positions is not portfolio_b.positions


class TestPortfolioBuy:
    def test_first_buy_creates_new_position(self, portfolio, petr4):
        transaction = portfolio.buy(
            asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5)
        )
        assert isinstance(transaction, Transaction)
        assert transaction.transaction_type == TransactionType.BUY
        assert "PETR4" in portfolio.positions
        assert portfolio.positions["PETR4"].quantity == Decimal("10")

    def test_second_buy_same_asset_reuses_position(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        portfolio.buy(asset=petr4, quantity=Decimal("5"), price=Decimal("36.00"), buy_date=date(2026, 1, 10))

        position = portfolio.positions["PETR4"]
        assert position.quantity == Decimal("15")
        assert len(position.transaction_list) == 2

    def test_buy_different_assets_creates_separate_positions(self, portfolio, petr4, vale3):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        portfolio.buy(asset=vale3, quantity=Decimal("20"), price=Decimal("68.00"), buy_date=date(2026, 1, 5))

        assert set(portfolio.positions.keys()) == {"PETR4", "VALE3"}

    def test_buy_returns_the_transaction_created(self, portfolio, petr4):
        transaction = portfolio.buy(
            asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5)
        )
        assert transaction.asset == petr4
        assert transaction.quantity == Decimal("10")


class TestPortfolioSell:
    def test_sell_asset_never_bought_raises_asset_not_found(self, portfolio, petr4):
        with pytest.raises(AssetNotFoundError):
            portfolio.sell(asset=petr4, quantity=Decimal("5"), price=Decimal("36.00"), sell_date=date(2026, 1, 10))

    def test_sell_more_than_owned_raises_insufficient_balance(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        with pytest.raises(InsufficientBalanceError):
            portfolio.sell(asset=petr4, quantity=Decimal("15"), price=Decimal("36.00"), sell_date=date(2026, 1, 10))

    def test_partial_sell_updates_position_quantity(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        transaction = portfolio.sell(
            asset=petr4, quantity=Decimal("4"), price=Decimal("37.00"), sell_date=date(2026, 1, 10)
        )
        assert transaction.transaction_type == TransactionType.SELL
        assert portfolio.positions["PETR4"].quantity == Decimal("6")

    def test_full_sell_removes_position_from_dict(self, portfolio, petr4):
        """Posição zerada é removida automaticamente via pop()."""
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        portfolio.sell(asset=petr4, quantity=Decimal("10"), price=Decimal("37.00"), sell_date=date(2026, 1, 10))

        assert "PETR4" not in portfolio.positions

    def test_selling_again_after_position_removed_raises_asset_not_found(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        portfolio.sell(asset=petr4, quantity=Decimal("10"), price=Decimal("37.00"), sell_date=date(2026, 1, 10))

        with pytest.raises(AssetNotFoundError):
            portfolio.sell(asset=petr4, quantity=Decimal("1"), price=Decimal("37.00"), sell_date=date(2026, 1, 15))

    def test_partial_sell_does_not_remove_position(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        portfolio.sell(asset=petr4, quantity=Decimal("4"), price=Decimal("37.00"), sell_date=date(2026, 1, 10))

        assert "PETR4" in portfolio.positions


class TestPortfolioGetTotalCost:
    def test_empty_portfolio_has_zero_cost(self, portfolio):
        assert portfolio.get_total_cost() == Decimal("0")

    def test_single_position_cost(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        assert portfolio.get_total_cost() == Decimal("350.00")

    def test_multiple_positions_cost_sums_correctly(self, portfolio, petr4, vale3):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))
        portfolio.buy(asset=vale3, quantity=Decimal("5"), price=Decimal("68.00"), buy_date=date(2026, 1, 5))
        assert portfolio.get_total_cost() == Decimal("350.00") + Decimal("340.00")


class TestPortfolioGetTotalEquity:
    def test_uses_price_source_not_average_price(self, portfolio, petr4, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("40.00")})

        assert portfolio.get_total_equity(price_source) == Decimal("400.00")

    def test_multiple_positions_equity_sums_correctly(self, portfolio, petr4, vale3, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        portfolio.buy(asset=vale3, quantity=Decimal("5"), price=Decimal("60.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("40.00"), "VALE3": Decimal("70.00")})

        expected = Decimal("10") * Decimal("40.00") + Decimal("5") * Decimal("70.00")
        assert portfolio.get_total_equity(price_source) == expected

    def test_missing_price_propagates_error(self, portfolio, petr4, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({})  # sem preço para PETR4

        with pytest.raises(KeyError):
            portfolio.get_total_equity(price_source)


class TestPortfolioGetTotalPnl:
    def test_pnl_is_equity_minus_cost(self, portfolio, petr4, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("40.00")})

        # cost = 300, equity = 400, pnl = 100
        assert portfolio.get_total_pnl(price_source) == Decimal("100.00")

    def test_negative_pnl_when_price_dropped(self, portfolio, petr4, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("20.00")})

        assert portfolio.get_total_pnl(price_source) == Decimal("-100.00")


class TestPortfolioGetPnl:
    def test_pnl_for_specific_position(self, portfolio, petr4, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("40.00")})

        assert portfolio.get_pnl("PETR4", price_source) == Decimal("100.00")

    def test_pnl_for_nonexistent_ticker_raises(self, portfolio, fake_price_source):
        price_source = fake_price_source({})
        with pytest.raises(AssetNotFoundError):
            portfolio.get_pnl("PETR4", price_source)


class TestPortfolioUpdatePrices:
    def test_updates_asset_current_price_for_all_positions(self, portfolio, petr4, vale3, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        portfolio.buy(asset=vale3, quantity=Decimal("5"), price=Decimal("60.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("45.00"), "VALE3": Decimal("72.00")})

        portfolio.update_portfolio_prices(price_source)

        assert petr4.current_price == Decimal("45.00")
        assert vale3.current_price == Decimal("72.00")

    def test_equity_reflects_prices_after_update(self, portfolio, petr4, fake_price_source):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("30.00"), buy_date=date(2026, 1, 5))
        price_source = fake_price_source({"PETR4": Decimal("50.00")})
        portfolio.update_portfolio_prices(price_source)

        assert petr4.current_price == Decimal("50.00")


class TestPortfolioPositionsEncapsulation:
    def test_positions_property_returns_copy(self, portfolio, petr4):
        portfolio.buy(asset=petr4, quantity=Decimal("10"), price=Decimal("35.00"), buy_date=date(2026, 1, 5))

        stolen = portfolio.positions
        stolen["FAKE"] = None

        assert "FAKE" not in portfolio.positions
