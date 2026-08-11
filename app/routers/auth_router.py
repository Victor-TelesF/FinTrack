from collections import defaultdict
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from ..dependencies import get_auth_service
from ..service.auth_service import AuthService
from ..schemas.user_schema import UserCreate, UserRead
from ..schemas.auth_schema import UserLogin, TokenRead

router = APIRouter(prefix="/auth", tags=["auth"])

_RATE_LIMIT = 5
_RATE_WINDOW_SECONDS = 60.0
_rate_limit_state: dict[tuple[str, str], list[float]] = defaultdict(list)
_rate_limit_lock = Lock()


def _check_rate_limit(request: Request, user_name: str) -> None:
    key = (
        request.url.path,
        request.client.host if request.client else "unknown",
        user_name,
    )
    now = monotonic()
    with _rate_limit_lock:
        recent_requests = [
            timestamp
            for timestamp in _rate_limit_state[key]
            if now - timestamp < _RATE_WINDOW_SECONDS
        ]
        if len(recent_requests) >= _RATE_LIMIT:
            _rate_limit_state[key] = recent_requests
            raise HTTPException(status_code=429, detail="Too many requests")
        recent_requests.append(now)
        _rate_limit_state[key] = recent_requests

def register_rate_limit(request: Request, user_data: UserCreate) -> None:
    _check_rate_limit(request, user_data.user_name)


def login_rate_limit(request: Request, credentials: UserLogin) -> None:
    _check_rate_limit(request, credentials.user_name)


@router.post("/register", response_model=UserRead, dependencies=[Depends(register_rate_limit)])
def register(user_data: UserCreate, service: AuthService = Depends(get_auth_service)):
    return service.register(user_data)

@router.post("/login", response_model=TokenRead, dependencies=[Depends(login_rate_limit)])
def login(credentials: UserLogin, service: AuthService = Depends(get_auth_service)):
    return service.login(credentials)