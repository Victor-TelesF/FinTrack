from pydantic import BaseModel, ConfigDict
from uuid import UUID


class PortfolioRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)
    id_portfolio: UUID