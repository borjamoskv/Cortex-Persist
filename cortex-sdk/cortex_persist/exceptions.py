"""cortex-persist — Exceptions."""

__all__ = ["CortexError"]


class CortexError(Exception):
    """Base error for CORTEX Persistence API operations."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"CORTEX API error {status_code}: {detail}")
