
class AppError(Exception):
    ...


class InvalidTokenError(AppError):
    
    def __init__(self, message: str = "Token inválido ou expirado"):
        super().__init__(message)