#Classe de erro base
class FinTrackError(Exception):
    """Exceção base do domínio"""
    ...

#Erros de valor

class InvalidValueError(FinTrackError):
    def __init__(self, message: str = "Valor inválido"):
        super().__init__(message)

class InvalidPriceError(InvalidValueError):
    def __init__(self, message: str = "Preço inválido"):
        super().__init__(message)

class InvalidPurchasePriceError(InvalidPriceError):
    def __init__(self, message: str = "Preço de compra inválido"):
        super().__init__(message)

class InvalidRateError(InvalidValueError):
    def __init__(self, message: str = "Taxa Inválida"):
        super().__init__(message)

class InvalidMaturityError(InvalidValueError):
    def __init__(self, message: str = "Data de vencimento inválida"):
        super().__init__(message)

class InvalidTransactionDateError(InvalidValueError):
    def __init__(self, message: str = "Data de transação invalida"):
        super().__init__(message)

class ProtocolError(InvalidValueError):
    def __init__(self, message: str = "Objeto não segue o protocolo esperado"):
        super().__init__(message)

class InvalidLiquidityError(InvalidValueError):
    ...

class InvalidIndexTypeError(InvalidValueError):
    ...

class InvalidQuantityError(InvalidValueError):
     def __init__(self, message: str = "Valor de Quantidade inválida"):
        super().__init__(message)

class InvalidTransactionTypeError(InvalidValueError):
    ...



#Erros de negócios

class BusinessError(FinTrackError):
    ...

class AssetNotFoundError(BusinessError):
    ...

class InsufficientBalanceError(BusinessError):
    ...


#Erros de dados do mercado
class MarketDataError(FinTrackError):
    ...

class CdiRateError(MarketDataError):
    def __init__(self, message: str = "Taxa CDI não foi fornecida"):
        super().__init__(message)

class IpcaRateError(MarketDataError):
    def __init__(self, message: str = "Taxa IPCA não fornecida"):
        super().__init__(message)

class SelicRateError(MarketDataError):
    def __init__(self, message: str = "Taxa Selic não fornecida"):
        super().__init__(message)
