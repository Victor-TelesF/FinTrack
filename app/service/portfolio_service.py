from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload, selectin_polymorphic
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.exceptions import (
    InvalidPortfolioTransactionError,
    PortfolioNotFoundError,
)
from app.mappers.asset_mapper import AssetMapper
from app.models import (
    AssetModel,
    PortfolioModel,
    TransactionModel,
    CDBModel,
    GovernmentBondModel,
    NationalStockModel,
    InternationalStockModel,
    RealEstateFundModel,
    CryptocurrencyModel,
)
from app.schemas.transaction_schema import TransactionCreate
from domain.enums import TransactionType
from domain.exceptions import FinTrackError

from domain.portfolio.portfolio import Portfolio
from domain.protocols import PriceRequest, PriceSource


class PortfolioService:

    def __init__(self, db: AsyncSession, price_source: PriceSource):
        self._db = db
        self._price_source = price_source

    async def list_for_user(self, user_id: UUID) -> list[PortfolioModel]:
        statement = select(PortfolioModel).where(PortfolioModel.user_id == user_id)
        result = await self._db.execute(statement)
        return list(result.scalars().all())

    async def list_transactions(self, portfolio_id: UUID, user_id: UUID) -> list[TransactionModel]:
        await self._get_owned_portfolio(portfolio_id, user_id)
        statement = (
            select(TransactionModel)
            .where(TransactionModel.id_portfolio == portfolio_id)
            .options(
                selectinload(TransactionModel.asset).options(
                    selectin_polymorphic(AssetModel, [
                        CDBModel,
                        GovernmentBondModel,
                        NationalStockModel,
                        InternationalStockModel,
                        RealEstateFundModel,
                        CryptocurrencyModel,
                    ])
                )
            )
            .order_by(
                TransactionModel.transaction_date,
                TransactionModel.transaction_sequence,
            )
        )
        result = await self._db.execute(statement)
        transactions = list(result.scalars().all())
        payloads = []
        for t in transactions:
            payloads.append({
                "id_transaction": t.id_transaction,
                "asset": {
                    "id": t.asset.id,
                    "name": t.asset.name,
                    "ticker": t.asset.ticker,
                    "current_price": t.asset.current_price,
                },
                "quantity": t.quantity,
                "price": t.price,
                "transaction_type": t.transaction_type,
                "transaction_date": t.transaction_date,
            })
        return payloads

    async def get_user_portfolio(self, user_id: UUID) -> PortfolioModel:
        statement = (
            select(PortfolioModel)
            .where(PortfolioModel.user_id == user_id)
            .order_by(PortfolioModel.id_portfolio)
            .options(
                selectinload(PortfolioModel.transactions).options(
                    selectinload(TransactionModel.asset).options(
                        selectin_polymorphic(AssetModel, [
                            CDBModel,
                            GovernmentBondModel,
                            NationalStockModel,
                            InternationalStockModel,
                            RealEstateFundModel,
                            CryptocurrencyModel,
                        ])
                    )
                )
            )
        )
        result = await self._db.execute(statement)
        portfolio = result.scalars().first()
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    async def positions(self, user_id: UUID):
        portfolio_model = await self.get_user_portfolio(user_id)
        portfolio = self._rebuild_domain_portfolio(portfolio_model)
        price_source = self._price_source
        asset_models = {
            transaction.asset_id: transaction.asset
            for transaction in portfolio_model.transactions
        }
        assets_by_ticker = {
            model.ticker: model for model in asset_models.values()
        }
        # build batch requests
        requests = [
            PriceRequest(
                ticker=position.asset.ticker,
                asset_type=assets_by_ticker[position.asset.ticker].asset_type,
                external_price_id=assets_by_ticker[position.asset.ticker].external_price_id,
            )
            for position in portfolio.positions.values()
        ]

        prices = await price_source.get_latest_prices(requests)

        result = []
        for position in portfolio.positions.values():
            current_price = prices.get(position.asset.ticker)
            cost_basis = position.quantity * position.average_price
            market_value = position.quantity * current_price
            pnl = market_value - cost_basis
            return_percentage = (pnl / cost_basis * 100) if cost_basis else 0
            model = assets_by_ticker[position.asset.ticker]
            asset_payload = {
                "id": model.id,
                "name": model.name,
                "ticker": model.ticker,
                "current_price": model.current_price,
                "asset_type": model.asset_type,
                "rate": getattr(model, "rate", None),
                "maturity_date": getattr(model, "maturity_date", None),
                "fgc_covered": getattr(model, "fgc_covered", None),
                "liquidity_type": getattr(model, "liquidity_type", None),
                "index_type": getattr(model, "index_type", None),
                "bond_index_type": getattr(model, "bond_index_type", None),
            }

            result.append({
                "asset": asset_payload,
                "quantity": position.quantity,
                "average_price": position.average_price,
                "current_price": current_price,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "pnl": pnl,
                "return_percentage": return_percentage,
            })
        return result

    async def summary(self, user_id: UUID):
        positions = await self.positions(user_id)
        total_cost = sum((item["cost_basis"] for item in positions), start=0)
        total_equity = sum((item["market_value"] for item in positions), start=0)
        total_pnl = total_equity - total_cost
        return {
            "total_cost": total_cost,
            "total_equity": total_equity,
            "total_pnl": total_pnl,
            "return_percentage": (total_pnl / total_cost * 100) if total_cost else 0,
        }

    async def add_transaction(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        transaction_data: TransactionCreate,
        transaction_type: TransactionType,
    ) -> TransactionModel:
        portfolio_model = await self._get_owned_portfolio(portfolio_id, user_id)
        asset_model = await self._get_asset(transaction_data.ticker)
        domain_portfolio = self._rebuild_domain_portfolio(portfolio_model)
        existing_position = domain_portfolio.positions.get(asset_model.ticker)
        domain_asset = (
            existing_position.asset
            if existing_position is not None
            else AssetMapper.to_domain(asset_model)
        )

        try:
            if transaction_type is TransactionType.BUY:
                domain_portfolio.buy(
                    domain_asset,
                    transaction_data.quantity,
                    transaction_data.price,
                    transaction_data.transaction_date,
                )
            else:
                domain_portfolio.sell(
                    domain_asset,
                    transaction_data.quantity,
                    transaction_data.price,
                    transaction_data.transaction_date,
                )
        except FinTrackError as exc:
            raise InvalidPortfolioTransactionError(str(exc)) from exc

        model = TransactionModel(
            asset_id=asset_model.id,
            id_portfolio=portfolio_id,
            quantity=transaction_data.quantity,
            price=transaction_data.price,
            transaction_type=transaction_type,
            transaction_date=transaction_data.transaction_date,
            asset=asset_model,
        )
        self._db.add(model)
        await self._db.commit()
        await self._db.refresh(model)
        return {
            "id_transaction": model.id_transaction,
            "asset": {
                "id": asset_model.id,
                "name": asset_model.name,
                "ticker": asset_model.ticker,
                "current_price": asset_model.current_price,
            },
            "quantity": model.quantity,
            "price": model.price,
            "transaction_type": model.transaction_type,
            "transaction_date": model.transaction_date,
        }

    async def _get_owned_portfolio(self, portfolio_id: UUID, user_id: UUID) -> PortfolioModel:
        statement = select(PortfolioModel).where(
            PortfolioModel.id_portfolio == portfolio_id,
            PortfolioModel.user_id == user_id,
        ).options(
            selectinload(PortfolioModel.transactions).options(
                selectinload(TransactionModel.asset).options(
                    selectin_polymorphic(AssetModel, [
                        CDBModel,
                        GovernmentBondModel,
                        NationalStockModel,
                        InternationalStockModel,
                        RealEstateFundModel,
                        CryptocurrencyModel,
                    ])
                )
            )
        )
        result = await self._db.execute(statement)
        portfolio = result.scalar_one_or_none()
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    async def _get_asset(self, ticker: str) -> AssetModel:
        statement = select(AssetModel).where(AssetModel.ticker == ticker)
        result = await self._db.execute(statement)
        asset = result.scalar_one_or_none()
        if asset is None:
            raise InvalidPortfolioTransactionError("Ativo não encontrado")
        return asset

    def _rebuild_domain_portfolio(self, portfolio_model: PortfolioModel) -> Portfolio:
        portfolio = Portfolio(str(portfolio_model.id_portfolio), portfolio_model.id_portfolio)
        asset_cache: dict[UUID, object] = {}
        transactions = sorted(
            portfolio_model.transactions,
            key=lambda transaction: (
                transaction.transaction_date,
                transaction.transaction_sequence,
            ),
        )
        for transaction in transactions:
            asset = asset_cache.setdefault(
                transaction.asset_id,
                AssetMapper.to_domain(transaction.asset),
            )
            if transaction.transaction_type is TransactionType.BUY:
                portfolio.buy(
                    asset,
                    transaction.quantity,
                    transaction.price,
                    transaction.transaction_date,
                    transaction.transaction_sequence,
                )
            else:
                portfolio.sell(
                    asset,
                    transaction.quantity,
                    transaction.price,
                    transaction.transaction_date,
                    transaction.transaction_sequence,
                )
        return portfolio