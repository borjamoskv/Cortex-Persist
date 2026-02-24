"""CORTEX Config — Backward-compatible shim.

Real implementation lives in cortex.core.config.
This module re-exports everything so existing `from cortex.config import X` works.
"""

import sys

from cortex.core.config import *  # noqa: F401,F403
from cortex.core.config import CortexConfig  # explicit for type-checkers
from cortex.core.config import reload as _core_reload


def reload() -> None:
    """Reload and sync module-level attrs in *this* shim module."""
    _core_reload()
    # Propagate updated attrs to the shim (cortex.config) namespace
    import cortex.core.config as _core

    _self = sys.modules[__name__]
    for attr in CortexConfig.__dataclass_fields__:
        setattr(_self, attr, getattr(_core, attr))
    _self.PROD = _core.PROD
    _self.IS_PROD = _core.IS_PROD


# Re-trigger module-level attribute population (backwards compat)
reload()
