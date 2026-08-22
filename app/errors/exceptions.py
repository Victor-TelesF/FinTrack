
class AppError(Exception):
    ...


class InvalidTokenError(AppError):
    
    def __init__(self, message: str = "Token inválido ou expirado"):
        super().__init__(message)


class InvalidCredentialsError(AppError):

    def __init__(self, message: str = "Usuário ou senha incorretos"):
        super().__init__(message)

class UserAlreadyExistsError(AppError):

    def __init__(self, message: str = "Nome de usuário já está em uso"):
        super().__init__(message)


class AssetNotFoundError(AppError):

    def __init__(self, message: str = "Ativo não encontrado"):
        super().__init__(message)


class AssetAlreadyExistsError(AppError):

    def __init__(self, message: str = "Ticker já está cadastrado"):
        super().__init__(message)


class PortfolioNotFoundError(AppError):

    def __init__(self, message: str = "Carteira não encontrada"):
        super().__init__(message)


class InvalidPortfolioTransactionError(AppError):

    def __init__(self, message: str = "Operação inválida para a carteira"):
        super().__init__(message)


class InvalidAdminKeyError(AppError):

    def __init__(self, message: str = "Chave administrativa inválida"):
        super().__init__(message)