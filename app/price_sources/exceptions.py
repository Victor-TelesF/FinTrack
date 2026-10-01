from uuid import UUID

from .types import QuoteFailure


class QuoteUnavailableError(Exception):
    def __init__(self, failures: dict[UUID, QuoteFailure]):
        self.failures = failures
        super().__init__("Cotação indisponível para um ou mais ativos.")


class QuoteConfigurationError(Exception):
    def __init__(self, asset_ids: list[UUID]):
        self.asset_ids = asset_ids
        super().__init__("Configuração de cotação inválida para um ou mais ativos.")
