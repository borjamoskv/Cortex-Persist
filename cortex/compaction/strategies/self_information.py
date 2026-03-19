"""
Self-Information pruning strategy for compaction.
Evaluates the information density of facts and compresses verbose ones.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.compaction.compactor import CompactionResult
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compaction.self_info")
_LOG_FMT = "Compactor [%s] %s"


async def execute_self_information(
    engine: "CortexEngine",
    project: str,
    result: "CompactionResult",
    dry_run: bool,
    threshold: float,
) -> None:
    """Execute the SELF_INFORMATION strategy.
    
    Finds the top N longest facts in the workspace and applies the 
    CompressionGuard to reduce their token footprint while retaining semantics.
    """
    from cortex.guards.compression_guard import compress_text
    
    facts = await engine.facts.recall(project=project)
    if not facts:
        return

    # Filter out facts that are already short (<200 chars are probably high density)
    # and facts that are JSON/structured (we don't want to break schema)
    candidates = [f for f in facts if len(f.content) > 200 and not f.content.strip().startswith("{")]
    
    if not candidates:
        return

    result.strategies_applied.append("self_info")
    
    compressed_count = 0
    total_tokens_saved = 0

    for fact in candidates:
        compressed, metrics = compress_text(fact.content, prune_ratio=0.3)
        
        # Only mutate if we save >15% tokens
        if metrics["savings_percent"] > 15.0:
            compressed_count += 1
            total_tokens_saved += (metrics["original_tokens"] - metrics["compressed_tokens"])
            
            if not dry_run:
                # We update the fact directly. If strict immutability is configured, 
                # engine.update handles deprecation automatically.
                try:
                    await engine.update(
                        fact.id,
                        content=compressed
                    )
                except Exception as e:
                    logger.warning("Failed to update fact %d during self_info compaction: %s", fact.id, e)

    detail = f"self_info: {compressed_count} facts compressed, ~{total_tokens_saved} tokens saved"
    result.details.append(detail)
    logger.info(_LOG_FMT, project, detail)

