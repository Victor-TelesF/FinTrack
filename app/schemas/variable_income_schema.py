from .asset_schema import AssetBaseRead, AssetBaseCreate
from domain.enums import Currency


class RealEstateFundCreate(AssetBaseCreate):
    pass


class RealEstateFundRead(AssetBaseRead):
    pass


class NationalStockCreate(AssetBaseCreate):
    pass


class NationalStockRead(AssetBaseRead):
    currency: Currency


class InternationalStockCreate(AssetBaseCreate):
    pass


class InternationalStockRead(AssetBaseRead):
    currency: Currency


class CryptocurrencyCreate(AssetBaseCreate):
    pass


class CryptocurrencyRead(AssetBaseRead):
    pass

