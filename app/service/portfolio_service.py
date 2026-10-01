from __future__ import annotations

from uuid import UUID
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, raiseload, with_polymorphic

from app.errors.exceptions import (
    InvalidPortfolioTransactionError,
    PortfolioNotFoundError,
)
from app.mappers.asset_mapper import AssetMapper
from app.models import AssetModel, PortfolioModel, TransactionModel
from app.schemas.transaction_schema import TransactionCreate
from domain.enums import TransactionType
from domain.exceptions import FinTrackError
from domain.portfolio.portfolio import Portfolio
from app.price_source import InMemoryPriceSource


portfolio_asset = with_polymorphic(AssetModel, "*", flat=True)


class PortfolioService:

    def __init__(self, db: AsyncSession):
        self._db = db

    async def list_for_user(self, user_id: UUID) -> list[PortfolioModel]:
        statement = select(PortfolioModel).where(PortfolioModel.user_id == user_id)
        return list((await self._db.execute(statement)).scalars().all())

    async def list_transactions(self, portfolio_id: UUID, user_id: UUID) -> list[TransactionModel]:
        await self._get_owned_portfolio(portfolio_id, user_id)
        return await self._load_transactions(portfolio_id)

    async def _load_transactions(self, portfolio_id: UUID) -> list[TransactionModel]:
        # One batch includes all asset subclasses and their registered prices.
        statement = (
            select(TransactionModel)
            .where(TransactionModel.id_portfolio == portfolio_id)
            .options(joinedload(TransactionModel.asset.of_type(portfolio_asset)), raiseload("*"))
            .order_by(TransactionModel.transaction_date, TransactionModel.transaction_sequence)
            .execution_options(populate_existing=True)
        )
        return list((await self._db.scalars(statement)).all())

    async def get_user_portfolio(self, user_id: UUID) -> PortfolioModel:
        statement = (
            select(PortfolioModel)
            .where(PortfolioModel.user_id == user_id)
            .order_by(PortfolioModel.id_portfolio)
        )
        portfolio = (await self._db.execute(statement)).scalars().first()
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    async def _load_positions(self, user_id: UUID):
        portfolio_model = await self.get_user_portfolio(user_id)
        transactions = await self._load_transactions(portfolio_model.id_portfolio)
        portfolio = self._rebuild_domain_portfolio(portfolio_model.id_portfolio, transactions)
        asset_models = {
            transaction.asset_id: transaction.asset
            for transaction in transactions
        }
        assets_by_ticker = {
            model.ticker: model for model in asset_models.values()
        }
        return portfolio.positions, assets_by_ticker

    @staticmethod
    def _value_position(position, current_price: Decimal):
        quantity = position.quantity
        average_price = position.average_price
        cost_basis = quantity * average_price
        market_value = quantity * current_price
        pnl = market_value - cost_basis
        return {
            "quantity": quantity,
            "average_price": average_price,
            "current_price": current_price,
            "cost_basis": cost_basis,
            "market_value": market_value,
            "pnl": pnl,
            "return_percentage": (pnl / cost_basis * 100) if cost_basis else 0,
        }

    async def positions(self, user_id: UUID):
        positions, assets_by_ticker = await self._load_positions(user_id)
        price_source = InMemoryPriceSource({
            ticker: model.current_price for ticker, model in assets_by_ticker.items()
        })
        result = []
        for position in positions.values():
            current_price = price_source.get_latest_price(position.asset.ticker)
            result.append({
                "asset": assets_by_ticker[position.asset.ticker],
                **self._value_position(position, current_price),
            })
        return result

    async def summary(self, user_id: UUID):
        positions = await self.positions(user_id)
        return self._summarize(positions)

    @staticmethod
    def _summarize(positions):
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
        # Authentication may already have started this session's transaction.
        # Lock before reading history; commit releases the lock only after the insert.
        # Any failed validation/write rolls back the complete operation.
        try:
            portfolio_model = await self._get_owned_portfolio(portfolio_id, user_id, for_update=True)
            asset_model = await self._get_asset(transaction_data.ticker)
            transactions = await self._load_transactions(portfolio_id)
            domain_portfolio = self._rebuild_domain_portfolio(portfolio_model.id_portfolio, transactions)
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
            await self._db.flush()
            # Reload database numeric scale before commit, preserving the HTTP contract.
            await self._db.refresh(model, attribute_names=["quantity", "price"])
            await self._db.commit()
            return model

        except BaseException:
            await self._db.rollback()
            raise

    async def _get_owned_portfolio(
        self, portfolio_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> PortfolioModel:
        statement = select(PortfolioModel).where(
            PortfolioModel.id_portfolio == portfolio_id,
            PortfolioModel.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update()
        portfolio = (await self._db.execute(statement)).scalar_one_or_none()
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    async def _get_asset(self, ticker: str) -> AssetModel:
        statement = select(portfolio_asset).where(portfolio_asset.ticker == ticker)
        asset = (await self._db.execute(statement)).scalar_one_or_none()
        if asset is None:
            raise InvalidPortfolioTransactionError("Ativo não encontrado")
        return asset

    def _rebuild_domain_portfolio(
        self, portfolio_id: UUID, transactions: list[TransactionModel]
    ) -> Portfolio:
        portfolio = Portfolio(str(portfolio_id), portfolio_id)
        asset_cache: dict[UUID, object] = {}
        transactions = sorted(
            transactions,
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
