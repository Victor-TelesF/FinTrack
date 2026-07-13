from ..enums import IndexType, BondIndexType
from ..protocols import ReturnStrategy
from .cdi import CDIStrategy
from .ipca import IPCAStrategy
from .selic import SelicStrategy
from .prefixada import FixedRateStrategy
from ..exceptions import InvalidIndexTypeError

def get_strategy_for(index_type: IndexType | BondIndexType) -> ReturnStrategy:
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
