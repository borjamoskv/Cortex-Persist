#!/usr/bin/env python3
"""
Cascade Router
Tactical routing logic to delegate heavy LLM tasks to local CLI engines:
Gemini (Antigravity), Claude Code, and Codex.
"""

import logging
import subprocess

logger = logging.getLogger("cortex_cascade.router")


class CascadeRouter:
    """Tactical router to delegate heavy LLM tasks to CLI engines."""

    def __init__(self):
        pass

    def route_task(
        self, prompt: str, task_type: str = "general", files: list[str] | None = None
    ) -> str:
        """
        Routes the task based on heuristics.
        task_type hints: 'architecture', 'refactor', 'snippet', 'test', 'audit'
        """
        engine = self._select_engine(task_type, files)
        logger.info(f"🧠 [ROUTER] Selected engine: {engine} for task: {task_type}")
        return self._execute(engine, prompt, files)

    def _select_engine(self, task_type: str, files: list[str] | None) -> str:
        num_files = len(files) if files else 0

        # Heuristics based on engine strengths and context windows
        if task_type in ("architecture", "audit", "deep_analysis") or num_files > 5:
            return "gemini"
        elif task_type in ("refactor", "bugfix", "strict_typing", "general"):
            return "claude"
        elif task_type in ("snippet", "test", "quick"):
            return "codex"
        else:
            return "claude"  # default fallback

    def _execute(self, engine: str, prompt: str, files: list[str] | None) -> str:
        try:
            if engine == "gemini":
                # gemini-cli supports context loading via flags
                cmd = ["npx", "-y", "@google/gemini-cli"]
                if files:
                    for f in files:
                        cmd.extend(["--file", f])
                cmd.append(prompt)

            elif engine == "claude":
                # claude-code run non-interactively to stdout
                cmd = ["npx", "-y", "@anthropic-ai/claude-code", "--print", "-q", prompt]

            elif engine == "codex":
                # codex binary in path
                cmd = ["codex", prompt]

            else:
                raise ValueError(f"Unknown engine: {engine}")

            logger.info(f"🚀 [ROUTER] Dispatching to {engine}...")
            # 5 minute timeout for complex generation
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"❌ [ROUTER] {engine} failed. STDERR: {result.stderr.strip()}")
                return f"Error ({engine}): {result.stderr.strip()}"

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ [ROUTER] {engine} execution timed out (300s).")
            return f"Error: {engine} timed out."
        except Exception as e:
            logger.error(f"🔥 [ROUTER] Subprocess execution exception: {e}")
            return f"Error: {e}"


if __name__ == "__main__":
    # Test stub
    logging.basicConfig(level=logging.INFO)
    router = CascadeRouter()
    logger.info(
        "Test Routing (Architecture): %s",
        router._select_engine("architecture", ["f1", "f2", "f3", "f4", "f5", "f6"]),
    )
    logger.info("Test Routing (Refactor): %s", router._select_engine("refactor", ["f1"]))
    logger.info("Test Routing (Snippet): %s", router._select_engine("snippet", []))
