# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""AlphaCode — Solution Sampler.

Generates diverse candidate solutions via LLM at varying temperatures.
Uses CORTEX's LLMProvider for OpenAI-compatible inference.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING

from cortex.alphacode._models import (
    AlphaCodeConfig,
    Language,
    Problem,
    SampledSolution,
)

if TYPE_CHECKING:
    from cortex.llm.provider import LLMProvider

logger = logging.getLogger("cortex.alphacode.sampler")


_SYSTEM_PROMPT_PYTHON = """\
You are an expert competitive programmer. Solve the given problem in Python 3.
- Read input from stdin using input()
- Print output to stdout using print()
- Handle edge cases and constraints carefully
- Optimize for correctness first, performance second
- Output ONLY the Python code, no explanations
- Do NOT include markdown code fences"""

_SYSTEM_PROMPT_CPP = """\
You are an expert competitive programmer. Solve the given problem in C++17.
- Read from cin, write to cout
- Use #include <bits/stdc++.h> if convenient
- Handle edge cases and constraints carefully
- Output ONLY the C++ code, no explanations
- Do NOT include markdown code fences"""

_SYSTEM_PROMPT_JS = """\
You are an expert competitive programmer. Solve the given problem in JavaScript (Node.js).
- Read input from process.stdin
- Write output to process.stdout
- Handle edge cases carefully
- Output ONLY the JavaScript code, no explanations
- Do NOT include markdown code fences"""

_SYSTEM_PROMPTS: dict[Language, str] = {
    Language.PYTHON: _SYSTEM_PROMPT_PYTHON,
    Language.CPP: _SYSTEM_PROMPT_CPP,
    Language.JAVASCRIPT: _SYSTEM_PROMPT_JS,
}

_CODE_FENCE_RE = re.compile(
    r"```(?:python|cpp|c\+\+|javascript|js)?\s*\n(.*?)```",
    re.DOTALL,
)


def _extract_code(raw: str) -> str:
    """Extract clean code from LLM output, stripping markdown fences if present."""
    match = _CODE_FENCE_RE.search(raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _build_user_prompt(problem: Problem) -> str:
    """Build the user prompt from a Problem specification."""
    parts = [
        f"# {problem.title}\n",
        problem.statement,
        "\n## Example Test Cases\n",
    ]
    for i, test in enumerate(problem.example_tests, 1):
        parts.append(f"### Example {i}")
        parts.append(f"**Input:**\n```\n{test.input}\n```")
        parts.append(f"**Output:**\n```\n{test.expected_output}\n```\n")

    if problem.time_limit_seconds:
        parts.append(f"Time limit: {problem.time_limit_seconds}s")
    if problem.memory_limit_mb:
        parts.append(f"Memory limit: {problem.memory_limit_mb}MB")

    return "\n".join(parts)


class Sampler:
    """Generate diverse candidate solutions for a competitive programming problem."""

    def __init__(
        self,
        llm: LLMProvider,
        config: AlphaCodeConfig,
    ) -> None:
        self._llm = llm
        self._config = config

    async def sample_all(self, problem: Problem) -> list[SampledSolution]:
        """Generate all candidate solutions with bounded concurrency."""
        semaphore = asyncio.Semaphore(self._config.max_concurrent_samples)
        user_prompt = _build_user_prompt(problem)
        system_prompt = _SYSTEM_PROMPTS.get(problem.language, _SYSTEM_PROMPT_PYTHON)

        async def _sample_one(index: int) -> SampledSolution | None:
            async with semaphore:
                return await self._generate_single(
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                    index=index,
                )

        tasks = [_sample_one(i) for i in range(self._config.num_samples)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        solutions: list[SampledSolution] = []
        for r in results:
            if isinstance(r, SampledSolution):
                solutions.append(r)
            elif isinstance(r, Exception):
                logger.warning("Sample generation failed: %s", r)

        # Deduplicate by code hash
        seen: set[str] = set()
        unique: list[SampledSolution] = []
        for sol in solutions:
            if sol.code_hash not in seen:
                seen.add(sol.code_hash)
                unique.append(sol)

        logger.info(
            "Sampled %d solutions (%d unique) for '%s'",
            len(solutions),
            len(unique),
            problem.title,
        )
        return unique

    async def _generate_single(
        self,
        user_prompt: str,
        system_prompt: str,
        index: int,
    ) -> SampledSolution:
        """Generate a single candidate solution."""
        temperature = self._config.temperature_for_sample(index)

        start = time.monotonic()
        raw_response = await self._llm.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=temperature,
            max_tokens=self._config.max_tokens_per_sample,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        code = _extract_code(raw_response)

        return SampledSolution(
            code=code,
            sample_index=index,
            temperature=temperature,
            model_name=self._llm.model_name,
            generation_time_ms=elapsed_ms,
        )
