"""
Testes para VariableIncome (ABC), Stock/NationalStock/InternationalStock,
RealEstateFund e Cryptocurrency.

Cobre:
- Guard manual: VariableIncome não pode ser instanciada diretamente
- Subclasses concretas não são afetadas pelo guard
- calculate_return: validação de purchase_price
- RealEstateFund: soma rentabilidade da cota + dividendos
- Currency correta por tipo de ação
"""
from decimal import Decimal

import pytest

from domain.assets.variable_income.variable_income import VariableIncome
from domain.assets.variable_income.national_stock import NationalStock
from domain.assets.variable_income.international_stock import InternationalStock
from domain.assets.variable_income.real_estate_fund import RealEstateFund
from domain.assets.variable_income.cryptocurrency import Cryptocurrency
from domain.enums import Currency
from domain.exceptions import InvalidPurchasePriceError, InvalidValueError
from domain.return_context import ReturnContext


class TestVariableIncomeGuard:
    def test_direct_instantiation_raises_type_error(self):
        with pytest.raises(TypeError, match="VariableIncome"):
            VariableIncome(name="Teste", ticker="TST", current_price=Decimal("10"))

    @pytest.mark.parametrize("cls,kwargs", [
        (NationalStock, {}),
        (InternationalStock, {}),
        (RealEstateFund, {}),
        (Cryptocurrency, {}),
    ])
    def test_concrete_subclasses_instantiate_normally(self, cls, kwargs):
        instance = cls(name="Teste", ticker="TST", current_price=Decimal("10"), **kwargs)
        assert instance.ticker == "TST"


class TestVariableIncomeCalculateReturn:
    def test_non_decimal_purchase_price_raises(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("40"))
        context = ReturnContext(purchase_price=30.0)  # float, não Decimal
        with pytest.raises(InvalidPurchasePriceError):
            stock.calculate_return(context)

    def test_zero_purchase_price_raises(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("40"))
        context = ReturnContext(purchase_price=Decimal("0"))
        with pytest.raises(InvalidPurchasePriceError):
            stock.calculate_return(context)

    def test_standard_capital_gain_formula(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("40"))
        context = ReturnContext(purchase_price=Decimal("20"))
        # (40 - 20) / 20 = 1.0 (100% de valorização)
        assert stock.calculate_return(context) == Decimal("1.0")


class TestStockCurrency:
    def test_national_stock_currency_is_brl(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("40"))
        assert stock.currency == Currency.BRL

    def test_international_stock_currency_is_usd(self):
        stock = InternationalStock(name="Apple", ticker="AAPL", current_price=Decimal("190"))
        assert stock.currency == Currency.USD


class TestRealEstateFund:
    def test_return_combines_quota_gain_and_dividends(self):
        fund = RealEstateFund(name="HGLG11", ticker="HGLG11", current_price=Decimal("110"))
        context = ReturnContext(purchase_price=Decimal("100"), dividends_received=Decimal("5"))
        # rentabilidade da cota: (110-100)/100 = 0.10
        # rentabilidade dividendos: 5/100 = 0.05
        # total esperado: 0.15
        assert fund.calculate_return(context) == Decimal("0.15")

    def test_non_decimal_dividends_raises(self):
        fund = RealEstateFund(name="HGLG11", ticker="HGLG11", current_price=Decimal("110"))
        context = ReturnContext(purchase_price=Decimal("100"), dividends_received=5.0)
        with pytest.raises(InvalidValueError):
            fund.calculate_return(context)

    def test_negative_dividends_warns_but_does_not_raise(self):
        fund = RealEstateFund(name="HGLG11", ticker="HGLG11", current_price=Decimal("110"))
        context = ReturnContext(purchase_price=Decimal("100"), dividends_received=Decimal("-1"))
        with pytest.warns(UserWarning):
            fund.calculate_return(context)


class TestCryptocurrency:
    def test_uses_standard_capital_gain_formula(self):
        crypto = Cryptocurrency(name="Bitcoin", ticker="BTC", current_price=Decimal("400000"))
        context = ReturnContext(purchase_price=Decimal("350000"))
        expected = (Decimal("400000") - Decimal("350000")) / Decimal("350000")
        assert crypto.calculate_return(context) == expected
