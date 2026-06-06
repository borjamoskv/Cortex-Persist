# [C5-REAL] Exergy-Maximized

import logging

logger = logging.getLogger("cortex.extensions.llm._router_shannon")


def compress_working_memory(
    messages: list[dict[str, str]],
    max_words: int,
    tail: int,
) -> list[dict[str, str]]:
    """Truncate working_memory if it exceeds the entropic safety threshold."""
    total_words = sum(len(m.get("content", "").split()) for m in messages)
    if total_words <= max_words or len(messages) <= tail + 1:
        return messages

    head = messages[:1]
    compressed_marker = {
        "role": "system",
        "content": (
            f"[CORTEX Ω₁₃ Shannon Compression] "
            f"{len(messages) - 1 - tail} intermediate messages truncated "
            f"({total_words} words exceeded {max_words} word budget). "
            f"Only seed instruction and last {tail} messages retained."
        ),
    }
    recent = messages[-tail:]
    logger.warning(
        "🗜️ [SHANNON] Compressed working_memory: %d msgs (%d words) → %d msgs",
        len(messages),
        total_words,
        len(head) + 1 + len(recent),
    )
    return head + [compressed_marker] + recent
