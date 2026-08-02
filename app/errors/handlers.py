from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .exceptions import InvalidCredentialsError, InvalidTokenError, UserAlreadyExistsError


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(InvalidCredentialsError)
    def handle_invalid_credentials(request: Request, exc: InvalidCredentialsError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(InvalidTokenError)
    def handle_invalid_token(request: Request, exc: InvalidTokenError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(UserAlreadyExistsError)
    def handle_user_already_exists(request: Request, exc: UserAlreadyExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})