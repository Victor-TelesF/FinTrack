"""Define the strategy registry for return calculations."""

from ..enums import IndexType, BondIndexType
from ..protocols import ReturnStrategy
from .cdi import CDIStrategy
from .ipca import IPCAStrategy
from .selic import SelicStrategy
from .prefixada import FixedRateStrategy
from ..exceptions import InvalidIndexTypeError


def get_strategy_for(index_type: IndexType | BondIndexType) -> ReturnStrategy:
    """Return the appropriate strategy for the provided index type.

    Args:
        index_type (IndexType | BondIndexType): The index type for strategy selection.

    Returns:
        ReturnStrategy: The strategy instance for the given index type.

    Raises:
        InvalidIndexTypeError: If the index_type is not supported.
    """
    _STRATEGY_REGISTRY = {
        IndexType.CDI: CDIStrategy(),
        IndexType.IPCA: IPCAStrategy(),
        IndexType.PREFIXADO: FixedRateStrategy(),
        BondIndexType.SELIC: SelicStrategy(),
        BondIndexType.IPCA: IPCAStrategy(),
        BondIndexType.PREFIXADO: FixedRateStrategy()
    }
    if not index_type in _STRATEGY_REGISTRY:
        raise InvalidIndexTypeError("Valor de estratégia inválido")
    
    return _STRATEGY_REGISTRY[index_type]
