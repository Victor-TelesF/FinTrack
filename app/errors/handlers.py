from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.price_sources.exceptions import QuoteConfigurationError, QuoteUnavailableError
from .exceptions import (
    AssetAlreadyExistsError,
    AssetCurrencyLockedError,
    InvalidAssetQuoteMetadataError,
    AssetNotFoundError,
    InvalidAdminKeyError,
    InvalidCredentialsError,
    InvalidPortfolioTransactionError,
    InvalidTokenError,
    PortfolioNotFoundError,
    UserAlreadyExistsError,
)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(QuoteConfigurationError)
    async def handle_quote_configuration(request: Request, exc: QuoteConfigurationError):
        return JSONResponse(status_code=422, content={
            "detail": str(exc), "asset_ids": [str(asset_id) for asset_id in exc.asset_ids],
        })

    @app.exception_handler(QuoteUnavailableError)
    async def handle_quote_unavailable(request: Request, exc: QuoteUnavailableError):
        return JSONResponse(status_code=503, content={
            "detail": str(exc), "asset_ids": [str(asset_id) for asset_id in exc.failures],
        })

    @app.exception_handler(InvalidAssetQuoteMetadataError)
    def handle_invalid_asset_metadata(request: Request, exc: InvalidAssetQuoteMetadataError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AssetCurrencyLockedError)
    def handle_asset_currency_locked(request: Request, exc: AssetCurrencyLockedError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(InvalidCredentialsError)
    def handle_invalid_credentials(request: Request, exc: InvalidCredentialsError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(InvalidAdminKeyError)
    def handle_invalid_admin_key(request: Request, exc: InvalidAdminKeyError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(InvalidTokenError)
    def handle_invalid_token(request: Request, exc: InvalidTokenError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(UserAlreadyExistsError)
    def handle_user_already_exists(request: Request, exc: UserAlreadyExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(AssetNotFoundError)
    def handle_asset_not_found(request: Request, exc: AssetNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(AssetAlreadyExistsError)
    def handle_asset_already_exists(request: Request, exc: AssetAlreadyExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(PortfolioNotFoundError)
    def handle_portfolio_not_found(request: Request, exc: PortfolioNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidPortfolioTransactionError)
    def handle_invalid_portfolio_transaction(
        request: Request, exc: InvalidPortfolioTransactionError
    ):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
