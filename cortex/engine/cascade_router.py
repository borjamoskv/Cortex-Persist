#!/usr/bin/env python3
"""
Cascade Router
Tactical routing logic to delegate heavy LLM tasks to local CLI engines:
Gemini (Antigravity), Claude Code, and Codex.
"""

import hashlib
import logging
import os
import sqlite3
import subprocess
from pathlib import Path

logger = logging.getLogger("cortex_cascade.router")


class CascadeRouter:
    """Tactical router to delegate heavy LLM tasks to CLI engines."""

    def __init__(self):
        pass

    def route_task(
        self,
        prompt: str,
        task_type: str = "general",
        files: list[str] | None = None,
        task_id: str | None = None,
    ) -> str:
        """
        Routes the task based on heuristics.
        task_type hints: 'architecture', 'refactor', 'snippet', 'test', 'audit'
        """
        engine = self._select_engine(task_type, files)
        logger.info(f"🧠 [ROUTER] Selected engine: {engine} for task: {task_type}")
        return self._execute(engine, prompt, files, task_id)

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

    def _execute(
        self, engine: str, prompt: str, files: list[str] | None, task_id: str | None
    ) -> str:
        try:
            if engine == "gemini":
                cmd = ["npx", "-y", "@google/gemini-cli"]
                if files:
                    for f in files:
                        cmd.extend(["--file", f])
                cmd.append(prompt)

            elif engine == "claude":
                cmd = ["npx", "-y", "@anthropic-ai/claude-code", "--print", "-q", prompt]

            elif engine == "codex":
                cmd = ["codex", prompt]

            else:
                raise ValueError(f"Unknown engine: {engine}")

            logger.info(f"🚀 [ROUTER] Dispatching to {engine}...")

            # Selectively pass API keys from parent environment
            child_env = {**os.environ}

            result = subprocess.run(cmd, env=child_env, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"❌ [ROUTER] {engine} failed. STDERR: {result.stderr.strip()}")
                return f"Error ({engine}): {result.stderr.strip()}"

            stdout = result.stdout.strip()

            # Log to DB for BM25 indexing
            if task_id:
                try:
                    db_path = Path("~/.cortex/cortex.db").expanduser()
                    if db_path.exists():
                        conn = sqlite3.connect(db_path)
                        digest = hashlib.sha256(stdout.encode("utf-8")).hexdigest()[:16]
                        # Escribir en la tabla de episodios/BM25
                        conn.execute(
                            "INSERT INTO episodes (event_type, project, content) VALUES (?, ?, ?)",
                            (
                                "llm_task_result",
                                "cortex-engine",
                                f"task_id:{task_id} engine:{engine} digest:{digest}\n{stdout[:500]}",
                            ),
                        )
                        # Opcional: Actualizar la tarea original
                        try:
                            conn.execute(
                                "UPDATE tasks SET status='completed' WHERE id=?", (task_id,)
                            )
                        except sqlite3.OperationalError:
                            pass  # Ignorar si la tabla tasks no tiene esa estructura
                        conn.commit()
                        conn.close()
                except Exception as db_e:
                    logger.error(f"⚠️ [ROUTER] Falló la persistencia en BD para indexación: {db_e}")

            return stdout

        except FileNotFoundError:
            logger.error(
                f"🔌 [ROUTER] CLI no encontrado en PATH: {cmd[0]}. Activando circuit breaker..."
            )
            try:
                from cortex.engine.circuit_breaker import CircuitBreaker

                cb = CircuitBreaker()
                return cb.fallback_response(engine, prompt)
            except ImportError:
                return f"Error: {cmd[0]} not found and circuit breaker unavailable."
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
