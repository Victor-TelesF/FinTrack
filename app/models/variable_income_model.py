from .asset_model import AssetModel


class NationalStockModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "national_stock"}


class InternationalStockModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "international_stock"}


class RealEstateFundModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "real_estate_fund"}

class CryptocurrencyModel(AssetModel):
    __mapper_args__ = {"polymorphic_identity": "cryptocurrency"}