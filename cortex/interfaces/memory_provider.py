from typing import Protocol, List
from dataclasses import dataclass

@dataclass
class MemoryResult:
    id: str
    score: float
    summary: str
    content: str = ""
    fact_type: str = "knowledge"

class MemoryProvider(Protocol):
    def search(self, query: str, limit: int = 10) -> List[MemoryResult]:
        """
        Searches the memory backend for facts/memories related to the query.
        Returns a list of structured MemoryResult objects.
        """
        ...
