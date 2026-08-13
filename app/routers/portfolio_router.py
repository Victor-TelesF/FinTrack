from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_portfolio_service
from app.models import UserModel
from app.schemas.portfolio_schema import PortfolioRead, PortfolioSummaryRead, PositionRead
from app.schemas.transaction_schema import TransactionCreate, TransactionRead
from app.service.portfolio_service import PortfolioService
from domain.enums import TransactionType

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioRead])
async def list_portfolios(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await service.list_for_user(current_user.user_id)


@router.post("/buy", response_model=TransactionRead)
async def buy_asset(
    transaction_data: TransactionCreate,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = await service.get_user_portfolio(current_user.user_id)
    return await service.add_transaction(
        portfolio.id_portfolio,
        current_user.user_id,
        transaction_data,
        TransactionType.BUY,
    )


@router.post("/sell", response_model=TransactionRead)
async def sell_asset(
    transaction_data: TransactionCreate,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = await service.get_user_portfolio(current_user.user_id)
    return await service.add_transaction(
        portfolio.id_portfolio,
        current_user.user_id,
        transaction_data,
        TransactionType.SELL,
    )


@router.get("/transactions", response_model=list[TransactionRead])
async def list_user_transactions(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = await service.get_user_portfolio(current_user.user_id)
    return await service.list_transactions(portfolio.id_portfolio, current_user.user_id)


@router.get("/positions", response_model=list[PositionRead])
async def list_positions(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await service.positions(current_user.user_id)


@router.get("/summary", response_model=PortfolioSummaryRead)
async def get_summary(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await service.summary(current_user.user_id)


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionRead])
async def list_transactions(
    portfolio_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return await service.list_transactions(portfolio_id, current_user.user_id)