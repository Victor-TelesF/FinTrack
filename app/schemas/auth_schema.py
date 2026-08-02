from pydantic import BaseModel, ConfigDict

class UserLogin(BaseModel):
    user_name: str
    password: str


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"