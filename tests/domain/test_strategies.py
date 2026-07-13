"""
Testes para as classes de Strategy (CDIStrategy, IPCAStrategy, SelicStrategy,
FixedRateStrategy) e o registry (get_strategy_for).
"""
from decimal import Decimal

import pytest

from app.domain.strategies.cdi import CDIStrategy
from app.domain.strategies.ipca import IPCAStrategy
from app.domain.strategies.selic import SelicStrategy
from app.domain.strategies.prefixada import FixedRateStrategy
from app.domain.strategies.registry import get_strategy_for
from app.domain.enums import IndexType, BondIndexType
from app.domain.exceptions import CdiRateError, IpcaRateError, SelicRateError, InvalidIndexTypeError
from app.domain.return_context import ReturnContext, MarketRates


class TestCDIStrategy:
    def test_calculates_rate_times_cdi(self):
        strategy = CDIStrategy()
        context = ReturnContext(market_rates=MarketRates(cdi_rate=Decimal("1.1")))
        assert strategy.calculate(Decimal("0.10"), context) == Decimal("0.11")

    def test_missing_cdi_rate_raises(self):
        strategy = CDIStrategy()
        context = ReturnContext(market_rates=MarketRates())
        with pytest.raises(CdiRateError):
            strategy.calculate(Decimal("0.10"), context)

    def test_missing_market_rates_raises(self):
        strategy = CDIStrategy()
        context = ReturnContext()
        with pytest.raises(CdiRateError):
            strategy.calculate(Decimal("0.10"), context)


class TestIPCAStrategy:
    def test_calculates_rate_plus_ipca(self):
        strategy = IPCAStrategy()
        context = ReturnContext(market_rates=MarketRates(ipca_rate=Decimal("0.04")))
        assert strategy.calculate(Decimal("0.05"), context) == Decimal("0.09")

    def test_missing_ipca_rate_raises(self):
        strategy = IPCAStrategy()
        context = ReturnContext(market_rates=MarketRates())
        with pytest.raises(IpcaRateError):
            strategy.calculate(Decimal("0.05"), context)


class TestSelicStrategy:
    def test_calculates_rate_times_selic(self):
        strategy = SelicStrategy()
        context = ReturnContext(market_rates=MarketRates(selic_rate=Decimal("1.0")))
        assert strategy.calculate(Decimal("0.01"), context) == Decimal("0.01")

    def test_missing_selic_rate_raises(self):
        strategy = SelicStrategy()
        context = ReturnContext(market_rates=MarketRates())
        with pytest.raises(SelicRateError):
            strategy.calculate(Decimal("0.01"), context)


class TestFixedRateStrategy:
    def test_returns_rate_unchanged(self):
        strategy = FixedRateStrategy()
        context = ReturnContext()
        assert strategy.calculate(Decimal("0.12"), context) == Decimal("0.12")


class TestStrategyRegistry:
    @pytest.mark.parametrize("index_type,expected_cls", [
        (IndexType.CDI, CDIStrategy),
        (IndexType.IPCA, IPCAStrategy),
        (IndexType.PREFIXADO, FixedRateStrategy),
        (BondIndexType.SELIC, SelicStrategy),
        (BondIndexType.IPCA, IPCAStrategy),
        (BondIndexType.PREFIXADO, FixedRateStrategy),
    ])
    def test_returns_correct_strategy_instance(self, index_type, expected_cls):
        strategy = get_strategy_for(index_type)
        assert isinstance(strategy, expected_cls)

    def test_invalid_index_type_raises(self):
        with pytest.raises(InvalidIndexTypeError):
            get_strategy_for("cdi")  # string solta, não Enum

    def test_ipca_from_index_type_and_bond_index_type_do_not_collide(self):
        """IndexType.IPCA e BondIndexType.IPCA têm o mesmo .value ('ipca'),
        mas são membros de Enums diferentes — o registry não deve confundi-los."""
        strategy_1 = get_strategy_for(IndexType.IPCA)
        strategy_2 = get_strategy_for(BondIndexType.IPCA)
        assert isinstance(strategy_1, IPCAStrategy)
        assert isinstance(strategy_2, IPCAStrategy)
