from dataclasses import dataclass, field
from typing import List, Any
from cortex.worker.issue_reader import IssueReader, IssueContext
from cortex.interfaces.memory_provider import MemoryProvider, MemoryResult

@dataclass
class TriageContext:
    issue: IssueContext
    related_memories: List[MemoryResult] = field(default_factory=list)
    architecture_context: List[Any] = field(default_factory=list)

class IssueMemoryStrategy:
    ALLOWED_FACT_TYPES = {"issue", "decision", "knowledge", "architecture", "postmortem", "code_pattern"}
    
    @classmethod
    def is_valid(cls, memory: MemoryResult) -> bool:
        if memory.fact_type not in cls.ALLOWED_FACT_TYPES:
            return False
        if "v6_aesgcm:" in memory.content:
            return False
        return True

class IssueTriagePipeline:
    """
    Sprint 2: Issue Reader -> CORTEX Search
    Pure pipeline coordinating the components without hard coupling.
    """
    def __init__(self, memory_provider: MemoryProvider):
        self.memory = memory_provider

    def process(self, issue_url: str) -> TriageContext:
        # Step 1: Deterministic Extraction
        issue = IssueReader.read(issue_url)
        
        # Step 2: Retrieve Relevant Context from Memory
        query = f"{issue.title}\n{issue.body}"
        
        # We query the interface with an over-fetch factor (x10) to allow hard-filtering
        raw_memories = self.memory.search(query=query, limit=50)
        
        filtered_memories = []
        for m in raw_memories:
            if IssueMemoryStrategy.is_valid(m):
                filtered_memories.append(m)
            if len(filtered_memories) == 5:
                break
        
        return TriageContext(
            issue=issue,
            related_memories=filtered_memories,
        )
