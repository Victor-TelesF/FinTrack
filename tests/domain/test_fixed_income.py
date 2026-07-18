"""
Testes para FixedIncome (ABC), CDB e GovernmentBond.

Cobre:
- FixedIncome.real_rate (Equação de Fisher)
- Validação de rate e maturity_date
- CDB: liquidity_type, index_type, strategy sincronizada após troca de indexador
- GovernmentBond: liquidity_type, bond_index_type, strategy sincronizada
"""
from decimal import Decimal
from datetime import date

import pytest

from domain.assets.fixed_income import CDB
from domain.assets.fixed_income import GovernmentBond
from domain.assets.fixed_income import FixedIncome
from domain.enums import LiquidityType, IndexType, BondIndexType
from domain.exceptions import (
    InvalidRateError,
    InvalidMaturityError,
    InvalidLiquidityError,
    InvalidIndexTypeError,
)
from domain.return_context import ReturnContext, MarketRates


@pytest.fixture(autouse=True)
def _freeze_reference_date(monkeypatch, frozen_today):
    """Congela reference_date() para tornar maturity_date determinística."""
    monkeypatch.setattr(
        "domain.assets.fixed_income.fixed_income.reference_date",
        lambda: frozen_today,
    )


class TestFixedIncomeRealRate:
    def test_real_rate_fisher_equation(self):
        # (1 + 0.10) / (1 + 0.05) - 1 ≈ 0.047619...
        result = FixedIncome.real_rate(Decimal("0.10"), Decimal("0.05"))
        assert result == pytest.approx(Decimal("0.047619"), abs=Decimal("0.00001"))

    def test_real_rate_rejects_non_decimal_nominal(self):
        with pytest.raises(InvalidRateError):
            FixedIncome.real_rate(0.10, Decimal("0.05"))

    def test_real_rate_rejects_zero_or_negative_nominal(self):
        with pytest.raises(InvalidRateError):
            FixedIncome.real_rate(Decimal("0"), Decimal("0.05"))


class TestCDB:
    def test_creates_with_valid_data(self, future_date):
        cdb = CDB(
            name="CDB Banco X", ticker="CDBX", current_price=Decimal("1000"),
            rate=Decimal("0.12"), maturity_date=future_date, fgc_covered=True,
            liquidity_type=LiquidityType.DIARIA, index_type=IndexType.CDI,
        )
        assert cdb.index_type == IndexType.CDI

    def test_maturity_date_in_the_past_raises(self, past_date):
        with pytest.raises(InvalidMaturityError):
            CDB(
                name="CDB Banco X", ticker="CDBX", current_price=Decimal("1000"),
                rate=Decimal("0.12"), maturity_date=past_date, fgc_covered=True,
                liquidity_type=LiquidityType.DIARIA, index_type=IndexType.CDI,
            )

    def test_invalid_liquidity_type_raises(self, future_date):
        with pytest.raises(InvalidLiquidityError):
            CDB(
                name="CDB Banco X", ticker="CDBX", current_price=Decimal("1000"),
                rate=Decimal("0.12"), maturity_date=future_date, fgc_covered=True,
                liquidity_type="diaria",  # string, não Enum
                index_type=IndexType.CDI,
            )

    def test_strategy_resyncs_when_index_type_changes(self, future_date):
        """Regressão do bug identificado na revisão do Gemini: trocar
        index_type via setter deve atualizar a strategy usada no cálculo."""
        cdb = CDB(
            name="CDB Banco X", ticker="CDBX", current_price=Decimal("1000"),
            rate=Decimal("0.12"), maturity_date=future_date, fgc_covered=True,
            liquidity_type=LiquidityType.DIARIA, index_type=IndexType.CDI,
        )
        context_cdi = ReturnContext(market_rates=MarketRates(cdi_rate=Decimal("1.0")))
        result_before = cdb.calculate_return(context_cdi)
        assert result_before == Decimal("0.12")  # CDI: rate * cdi_rate(1.0)

        cdb.index_type = IndexType.PREFIXADO
        context_any = ReturnContext()
        result_after = cdb.calculate_return(context_any)
        assert result_after == Decimal("0.12")  # Prefixado: sempre retorna rate

    def test_invalid_index_type_raises(self, future_date):
        with pytest.raises(InvalidIndexTypeError):
            CDB(
                name="CDB Banco X", ticker="CDBX", current_price=Decimal("1000"),
                rate=Decimal("0.12"), maturity_date=future_date, fgc_covered=True,
                liquidity_type=LiquidityType.DIARIA, index_type="cdi",  # string, não Enum
            )


class TestGovernmentBond:
    def test_creates_with_valid_data(self, future_date):
        bond = GovernmentBond(
            name="Tesouro Selic", ticker="LFT", current_price=Decimal("100"),
            rate=Decimal("0.01"), maturity_date=future_date,
            liquidity_type=LiquidityType.DIARIA, bond_index_type=BondIndexType.SELIC,
        )
        assert bond.bond_index_type == BondIndexType.SELIC

    def test_strategy_resyncs_when_bond_index_type_changes(self, future_date):
        bond = GovernmentBond(
            name="Tesouro Selic", ticker="LFT", current_price=Decimal("100"),
            rate=Decimal("0.01"), maturity_date=future_date,
            liquidity_type=LiquidityType.DIARIA, bond_index_type=BondIndexType.SELIC,
        )
        bond.bond_index_type = BondIndexType.PREFIXADO
        result = bond.calculate_return(ReturnContext())
        assert result == Decimal("0.01")  # Prefixado: sempre retorna rate
