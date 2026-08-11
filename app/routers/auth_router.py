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
_rate_limit_state: dict[str, list[float]] = defaultdict(list)
_rate_limit_lock = Lock()


def _cleanup_rate_limit_state(now: float | None = None) -> None:
    if now is None:
        now = monotonic()

    keys_to_remove = []
    for key, timestamps in _rate_limit_state.items():
        recent_requests = [
            timestamp for timestamp in timestamps if now - timestamp < _RATE_WINDOW_SECONDS
        ]
        if recent_requests:
            _rate_limit_state[key] = recent_requests
        else:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _rate_limit_state[key]


def _check_rate_limit(request: Request, user_name: str) -> None:
    # TODO: For multi-instance Render deployment, replace this in-process store with
    # a shared external store such as Redis.
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    with _rate_limit_lock:
        _cleanup_rate_limit_state(now)
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


def reset_rate_limit_state() -> None:
    with _rate_limit_lock:
        _rate_limit_state.clear()

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