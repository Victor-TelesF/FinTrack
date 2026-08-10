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
def list_portfolios(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return service.list_for_user(current_user.user_id)


@router.post("/buy", response_model=TransactionRead)
def buy_asset(
    transaction_data: TransactionCreate,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = service.get_user_portfolio(current_user.user_id)
    return service.add_transaction(
        portfolio.id_portfolio,
        current_user.user_id,
        transaction_data,
        TransactionType.BUY,
    )


@router.post("/sell", response_model=TransactionRead)
def sell_asset(
    transaction_data: TransactionCreate,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = service.get_user_portfolio(current_user.user_id)
    return service.add_transaction(
        portfolio.id_portfolio,
        current_user.user_id,
        transaction_data,
        TransactionType.SELL,
    )


@router.get("/transactions", response_model=list[TransactionRead])
def list_user_transactions(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = service.get_user_portfolio(current_user.user_id)
    return service.list_transactions(portfolio.id_portfolio, current_user.user_id)


@router.get("/positions", response_model=list[PositionRead])
def list_positions(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return service.positions(current_user.user_id)


@router.get("/summary", response_model=PortfolioSummaryRead)
def get_summary(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return service.summary(current_user.user_id)


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionRead])
def list_transactions(
    portfolio_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return service.list_transactions(portfolio_id, current_user.user_id)