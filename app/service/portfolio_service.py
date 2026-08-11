from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.price_source import DatabasePriceSource


class PortfolioService:

    def __init__(self, db: Session):
        self._db = db

    def list_for_user(self, user_id: UUID) -> list[PortfolioModel]:
        statement = select(PortfolioModel).where(PortfolioModel.user_id == user_id)
        return list(self._db.execute(statement).scalars().all())

    def list_transactions(self, portfolio_id: UUID, user_id: UUID) -> list[TransactionModel]:
        self._get_owned_portfolio(portfolio_id, user_id)
        statement = (
            select(TransactionModel)
            .where(TransactionModel.id_portfolio == portfolio_id)
            .order_by(
                TransactionModel.transaction_date,
                TransactionModel.created_at,
                TransactionModel.id_transaction,
            )
        )
        return list(self._db.execute(statement).scalars().all())

    def get_user_portfolio(self, user_id: UUID) -> PortfolioModel:
        statement = (
            select(PortfolioModel)
            .where(PortfolioModel.user_id == user_id)
            .order_by(PortfolioModel.id_portfolio)
        )
        portfolio = self._db.execute(statement).scalars().first()
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    def positions(self, user_id: UUID):
        portfolio_model = self.get_user_portfolio(user_id)
        portfolio = self._rebuild_domain_portfolio(portfolio_model)
        price_source = DatabasePriceSource(self._db)
        asset_models = {
            transaction.asset_id: transaction.asset
            for transaction in portfolio_model.transactions
        }
        assets_by_ticker = {
            model.ticker: model for model in asset_models.values()
        }
        result = []
        for position in portfolio.positions.values():
            current_price = price_source.get_latest_price(position.asset.ticker)
            cost_basis = position.quantity * position.average_price
            market_value = position.quantity * current_price
            pnl = market_value - cost_basis
            return_percentage = (pnl / cost_basis * 100) if cost_basis else 0
            result.append({
                "asset": assets_by_ticker[position.asset.ticker],
                "quantity": position.quantity,
                "average_price": position.average_price,
                "current_price": current_price,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "pnl": pnl,
                "return_percentage": return_percentage,
            })
        return result

    def summary(self, user_id: UUID):
        positions = self.positions(user_id)
        total_cost = sum((item["cost_basis"] for item in positions), start=0)
        total_equity = sum((item["market_value"] for item in positions), start=0)
        total_pnl = total_equity - total_cost
        return {
            "total_cost": total_cost,
            "total_equity": total_equity,
            "total_pnl": total_pnl,
            "return_percentage": (total_pnl / total_cost * 100) if total_cost else 0,
        }

    def add_transaction(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        transaction_data: TransactionCreate,
        transaction_type: TransactionType,
    ) -> TransactionModel:
        portfolio_model = self._get_owned_portfolio(portfolio_id, user_id)
        asset_model = self._get_asset(transaction_data.ticker)
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
        self._db.commit()
        self._db.refresh(model)
        return model

    def _get_owned_portfolio(self, portfolio_id: UUID, user_id: UUID) -> PortfolioModel:
        statement = select(PortfolioModel).where(
            PortfolioModel.id_portfolio == portfolio_id,
            PortfolioModel.user_id == user_id,
        )
        portfolio = self._db.execute(statement).scalar_one_or_none()
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    def _get_asset(self, ticker: str) -> AssetModel:
        statement = select(AssetModel).where(AssetModel.ticker == ticker)
        asset = self._db.execute(statement).scalar_one_or_none()
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
                transaction.created_at,
                transaction.id_transaction,
            ),
        )
        for transaction in transactions:
            asset = asset_cache.setdefault(
                transaction.asset_id,
                AssetMapper.to_domain(transaction.asset),
            )
            if transaction.transaction_type is TransactionType.BUY:
                portfolio.buy(asset, transaction.quantity, transaction.price, transaction.transaction_date)
            else:
                portfolio.sell(asset, transaction.quantity, transaction.price, transaction.transaction_date)
        return portfolio