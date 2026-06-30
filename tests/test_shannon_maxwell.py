# [C5-REAL] Exergy-Maximized
"""Tests for Maxwell's Token Demon (L1 Router / Cognitive Heat Sink).
Validates structural bypass, filler annihilation, and entropy filtering.
"""

from __future__ import annotations

import pytest

from babylon60.shannon.maxwell import filter_context


def test_empty_content() -> None:
    """Empty content should return default values."""
    res = filter_context("")
    assert res.original_length == 0
    assert res.filtered_length == 0
    assert res.exergy_density == 0.0
    assert res.filtered_content == ""
    assert res.tokens_discarded == 0


def test_structural_bypass() -> None:
    """Lines with exergy markers (e.g. 'def', 'class', code blocks) must bypass filtering."""
    content = (
        "I think we should define a class.\n"
        "class Model:\n"
        "    def run(self):\n"
        "        pass\n"
        "To summarize, this object is important."
    )
    # Even if entropy is low, 'class Model:' and 'def run' should be preserved.
    # Conversational filler 'I think...' and 'To summarize...' should be filtered.
    res = filter_context(content, entropy_threshold=2.0)
    assert "class Model:" in res.filtered_content
    assert "def run(self):" in res.filtered_content
    assert "I think" not in res.filtered_content
    assert "To summarize" not in res.filtered_content


def test_code_block_bypass() -> None:
    """All lines inside a markdown code block must be preserved."""
    content = (
        "As an AI, I suggest this code:\n"
        "```python\n"
        "I think this line inside code block is safe\n"
        "print('hello')\n"
        "```\n"
        "In conclusion, that is it."
    )
    res = filter_context(content, entropy_threshold=3.0)
    # The code block markers and content inside should be preserved completely
    assert "```python" in res.filtered_content
    assert "I think this line inside code block is safe" in res.filtered_content
    assert "print('hello')" in res.filtered_content
    assert "```" in res.filtered_content
    # Filler outside code blocks should be removed
    assert "As an AI" not in res.filtered_content
    assert "In conclusion" not in res.filtered_content


def test_filler_annihilation() -> None:
    """Common filler phrases should be dropped."""
    content = (
        "Perhaps we can look at the data.\n"
        "Here is the key fact: the system has low latency.\n"
        "I understand your request."
    )
    # 'Perhaps...' and 'I understand...' start with filler patterns, so they should be annihilated.
    # 'Here is...' also starts with filler patterns but wait, _LOW_EXERGY_FILLER has 'Here is'.
    res = filter_context(content, entropy_threshold=0.5)
    assert "Perhaps" not in res.filtered_content
    assert "I understand" not in res.filtered_content
    assert "Here is" not in res.filtered_content


def test_entropy_filtering() -> None:
    """Lines with sufficient entropy are kept, while low-entropy ones are filtered."""
    content = (
        "random random random random\n"  # Very low entropy (highly repetitive/stop-words)
        "The cognitive topology map exhibits high structural variance and exergy density.\n"  # High entropy
    )
    res = filter_context(content, entropy_threshold=1.5)
    assert "exhibits high structural variance" in res.filtered_content
    assert "random random" not in res.filtered_content
