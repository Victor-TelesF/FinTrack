from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from uuid import UUID

class AssetBaseCreate(BaseModel):

    name: str
    ticker: str
    

class AssetBaseRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    ticker: str
    current_price: Decimal