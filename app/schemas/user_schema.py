from pydantic import BaseModel, ConfigDict
from uuid import UUID

class UserCreate(BaseModel):
    user_name: str
    password: str

class UserRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    user_name: str