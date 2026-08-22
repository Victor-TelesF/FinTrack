from .asset_model import AssetModel
from domain.enums import Currency


class NationalStockModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "national_stock"}

    @property
    def currency(self) -> Currency:
        return Currency.BRL


class InternationalStockModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "international_stock"}

    @property
    def currency(self) -> Currency:
        return Currency.USD


class RealEstateFundModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "real_estate_fund"}

class CryptocurrencyModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "cryptocurrency"}