from typing import Protocol, List
from dataclasses import dataclass

@dataclass
class MemoryRef:
    id: str
    score: float
    summary: str
    fact_type: str = "knowledge"

@dataclass
class MemoryResult:
    ref: MemoryRef
    content: str = ""

class MemoryProvider(Protocol):
    def search(self, query: str, limit: int = 10) -> List[MemoryRef]:
        """
        Searches the memory backend for facts/memories related to the query.
        Returns a list of structured MemoryRef objects.
        """
        ...
        
    def hydrate(self, refs: List[MemoryRef]) -> List[MemoryResult]:
        """
        Hydrates a list of MemoryRefs with their full content.
        """
        ...
