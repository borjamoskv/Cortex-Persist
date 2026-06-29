# [C5-REAL] Exergy-Maximized
"""
CORTEX Extensions Package.
Contains all extension modules, governed by the Tier Registry system.
"""

import importlib.abc
import sys

from cortex.extensions.registry import verify_extension_import


class ExtensionTierImportEnforcer(importlib.abc.MetaPathFinder):
    """Interceptors all imports under cortex.extensions to enforce safety and validation boundaries."""
    
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("cortex.extensions."):
            verify_extension_import(fullname)
        return None  # Let standard importers load it after verification


# Register the enforcer at the head of the meta path
sys.meta_path.insert(0, ExtensionTierImportEnforcer())
