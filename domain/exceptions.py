"""Define domain-specific exceptions used across the application.

This module defines the base error types and specialized exception classes for
validation, business logic, and market data issues.
"""


class FinTrackError(Exception):
    """Base exception for FinTrack domain errors."""
    ...


class InvalidValueError(FinTrackError):
    """Raised when a provided value does not meet validation requirements."""

    def __init__(self, message: str = "Valor inválido"):
        super().__init__(message)


class InvalidPriceError(InvalidValueError):
    """Raised when a price value is invalid."""

    def __init__(self, message: str = "Preço inválido"):
        super().__init__(message)


class InvalidPurchasePriceError(InvalidPriceError):
    """Raised when a purchase price value is invalid."""

    def __init__(self, message: str = "Preço de compra inválido"):
        super().__init__(message)


class InvalidRateError(InvalidValueError):
    """Raised when a rate value is invalid."""

    def __init__(self, message: str = "Taxa Inválida"):
        super().__init__(message)


class InvalidMaturityError(InvalidValueError):
    """Raised when a maturity date value is invalid."""

    def __init__(self, message: str = "Data de vencimento inválida"):
        super().__init__(message)


class InvalidTransactionDateError(InvalidValueError):
    """Raised when a transaction date value is invalid."""

    def __init__(self, message: str = "Data de transação invalida"):
        super().__init__(message)


class ProtocolError(InvalidValueError):
    """Raised when an object does not follow the expected protocol."""

    def __init__(self, message: str = "Objeto não segue o protocolo esperado"):
        super().__init__(message)


class InvalidLiquidityError(InvalidValueError):
    """Raised when a liquidity value is invalid."""
    ...


class InvalidIndexTypeError(InvalidValueError):
    """Raised when an index type value is invalid."""
    ...


class InvalidQuantityError(InvalidValueError):
    """Raised when a quantity value is invalid."""

    def __init__(self, message: str = "Valor de Quantidade inválida"):
        super().__init__(message)


class InvalidTransactionTypeError(InvalidValueError):
    """Raised when a transaction type value is invalid."""
    ...


class BusinessError(FinTrackError):
    """Raised for business rule violations."""
    ...


class AssetNotFoundError(BusinessError):
    """Raised when an asset is not found in the portfolio."""
    ...


class InsufficientBalanceError(BusinessError):
    """Raised when attempting to sell more assets than available."""
    ...


class MarketDataError(FinTrackError):
    """Raised when market data is missing or invalid."""
    ...


class CdiRateError(MarketDataError):
    """Raised when CDI rate data is unavailable."""

    def __init__(self, message: str = "Taxa CDI não foi fornecida"):
        super().__init__(message)


class IpcaRateError(MarketDataError):
    """Raised when IPCA rate data is unavailable."""

    def __init__(self, message: str = "Taxa IPCA não fornecida"):
        super().__init__(message)


class SelicRateError(MarketDataError):
    """Raised when Selic rate data is unavailable."""

    def __init__(self, message: str = "Taxa Selic não fornecida"):
        super().__init__(message)
