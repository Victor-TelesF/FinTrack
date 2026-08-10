from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from ..database import Base
from uuid import UUID, uuid4


class AssetModel(Base):

    __tablename__ = "asset"

    id: Mapped[UUID] = mapped_column(primary_key=True, index=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50))
    ticker: Mapped[str] = mapped_column(String(50))
    current_price: Mapped[Decimal] = mapped_column(Numeric(precision=18,scale=8))
    type_column: Mapped[str] = mapped_column(String(50))

    @property
    def asset_type(self) -> str:
        return self.type_column

    __mapper_args__ = {
        "polymorphic_on": type_column,
        "polymorphic_identity": "asset"
    }