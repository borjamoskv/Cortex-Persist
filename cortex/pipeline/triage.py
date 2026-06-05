from dataclasses import dataclass, field
from typing import List, Any
from cortex.worker.issue_reader import IssueReader, IssueContext
from cortex.interfaces.memory_provider import MemoryProvider, MemoryResult, MemoryRef
from cortex.worker.issue_reader import IssueReader, IssueContext

@dataclass
class TriageContext:
    issue: IssueContext
    related_memories: List[MemoryResult] = field(default_factory=list)
    architecture_context: List[Any] = field(default_factory=list)

class IssueMemoryStrategy:
    ALLOWED_FACT_TYPES = {"issue", "decision", "knowledge", "architecture", "postmortem", "code_pattern"}
    
    @classmethod
    def is_valid(cls, ref: MemoryRef) -> bool:
        if ref.fact_type not in cls.ALLOWED_FACT_TYPES:
            return False
        # Phase 2 filtering is purely structural. No decryption here.
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
        
        # PHASE 1: Semantic retrieval (NO DECRYPT)
        candidate_refs = self.memory.search(query=query, limit=50)
        
        # PHASE 2: Structural filtering
        filtered_refs = []
        for ref in candidate_refs:
            if IssueMemoryStrategy.is_valid(ref):
                filtered_refs.append(ref)
            if len(filtered_refs) == 5:
                break
                
        # PHASE 3 & 4: Rank and Hydrate
        hydrated_memories = self.memory.hydrate(filtered_refs)
        
        return TriageContext(
            issue=issue,
            related_memories=hydrated_memories,
        )
