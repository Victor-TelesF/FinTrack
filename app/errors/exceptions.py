
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