from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_portfolio_service, get_quote_service
from app.models import UserModel
from app.schemas.valuation_schema import (
    PortfolioValuationRead, PositionValuationRead, ValuationErrorRead,
)
from app.service.portfolio_service import PortfolioService
from app.service.quote_service import QuoteService

router = APIRouter(
    prefix="/api/v2/portfolios", tags=["portfolio valuation"],
    responses={
        422: {"model": ValuationErrorRead, "description": "Configuração de avaliação inválida."},
        503: {"model": ValuationErrorRead, "description": "Cotação indisponível; avaliação completa não realizada."},
    },
)


@router.get("/positions", response_model=list[PositionValuationRead])
async def list_market_positions(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
    quotes: QuoteService = Depends(get_quote_service),
):
    """Posições abertas por moeda, com preço cadastrado e cotação separados."""
    return await service.market_positions(current_user.user_id, quotes)


@router.get("/summary", response_model=PortfolioValuationRead)
async def get_market_summary(
    current_user: UserModel = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
    quotes: QuoteService = Depends(get_quote_service),
):
    """Totais por moeda e cotações da mesma avaliação, sem conversão cambial.

    P&L das posições abertas, sem dividendos ou ganhos realizados.
    Requisições independentes podem utilizar cotações de horários distintos.
    """
    return await service.market_summary(current_user.user_id, quotes)
