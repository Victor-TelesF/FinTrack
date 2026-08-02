from fastapi import APIRouter, Depends
from ..dependencies import get_auth_service
from ..service.auth_service import AuthService
from ..schemas.user_schema import UserCreate, UserRead
from ..schemas.auth_schema import UserLogin, TokenRead

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
def register(user_data: UserCreate, service: AuthService = Depends(get_auth_service)):
    return service.register(user_data)

@router.post("/login", response_model=TokenRead)
def login(credentials: UserLogin, service: AuthService = Depends(get_auth_service)):
    return service.login(credentials)