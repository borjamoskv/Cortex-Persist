class MacMaestroError(Exception):
    """Base exception for mac_maestro."""


class ElementNotFoundError(MacMaestroError):
    """Raised when no matching accessibility element is found."""


class ElementAmbiguousError(MacMaestroError):
    """Raised when more than one candidate matches with similar confidence."""


class ActionExecutionError(MacMaestroError):
    """Raised when an action cannot be executed on a matched element."""


class SafetyViolationError(MacMaestroError):
    """Raised when an action is blocked by safety policy."""
