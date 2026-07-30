"""
Testes para a classe base Asset (ABC).

Cobre:
- Asset não pode ser instanciada diretamente (é ABC com @abstractmethod)
- Validação de name (tipo, vazio, só espaços, normalização via strip)
- Validação de ticker (tipo, vazio, só espaços, normalização via strip)
- Validação de current_price (Decimal, > 0)
- __repr__ polimórfico
"""
from decimal import Decimal

import pytest

from domain.assets.asset import Asset
from domain.assets.variable_income import NationalStock
from domain.exceptions import InvalidValueError, InvalidPriceError


class TestAssetCannotBeInstantiatedDirectly:
    def test_direct_instantiation_raises_type_error(self):
        with pytest.raises(TypeError):
            Asset(name="Teste", ticker="TST", current_price=Decimal("10"))


class TestAssetNameValidation:
    def test_non_string_name_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name=123, ticker="PETR4", current_price=Decimal("35"))

    def test_empty_name_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name="", ticker="PETR4", current_price=Decimal("35"))

    def test_whitespace_only_name_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name="   ", ticker="PETR4", current_price=Decimal("35"))

    def test_name_is_stripped(self):
        stock = NationalStock(name="  Petrobras  ", ticker="PETR4", current_price=Decimal("35"))
        assert stock.name == "Petrobras"


class TestAssetTickerValidation:
    def test_non_string_ticker_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name="Petrobras", ticker=1234, current_price=Decimal("35"))

    def test_empty_ticker_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name="Petrobras", ticker="", current_price=Decimal("35"))

    def test_whitespace_only_ticker_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name="Petrobras", ticker="   ", current_price=Decimal("35"))

    def test_ticker_is_stripped(self):
        stock = NationalStock(name="Petrobras", ticker="  PETR4  ", current_price=Decimal("35"))
        assert stock.ticker == "PETR4"


class TestAssetCurrentPriceValidation:
    def test_non_decimal_price_raises(self):
        with pytest.raises(InvalidValueError):
            NationalStock(name="Petrobras", ticker="PETR4", current_price=35.5)  # float, não Decimal

    def test_zero_price_raises(self):
        with pytest.raises(InvalidPriceError):
            NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("0"))

    def test_negative_price_raises(self):
        with pytest.raises(InvalidPriceError):
            NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("-5"))

    def test_price_can_be_updated_via_setter(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("35"))
        stock.current_price = Decimal("40")
        assert stock.current_price == Decimal("40")

    def test_price_setter_rejects_invalid_value(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("35"))
        with pytest.raises(InvalidPriceError):
            stock.current_price = Decimal("-1")


class TestAssetRepr:
    def test_repr_uses_concrete_class_name(self):
        stock = NationalStock(name="Petrobras", ticker="PETR4", current_price=Decimal("35"))
        assert "NationalStock" in repr(stock)
        assert "PETR4" in repr(stock)
