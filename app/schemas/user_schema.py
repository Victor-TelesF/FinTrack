from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class UserCreate(BaseModel):
    user_name: str = Field(max_length=50)
    password: str = Field(min_length=8)

class UserRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    user_name: str