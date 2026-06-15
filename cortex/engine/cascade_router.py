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

    def fallback_response(self, engine: str, prompt: str) -> str:
        """Fallback response when engine is unavailable."""
        try:
            from cortex.engine.circuit_breaker import CircuitBreaker

            cb = CircuitBreaker(f"cascade_router_{engine}")
            cb._on_failure()
        except Exception as cb_err:
            logger.debug(f"Could not update circuit breaker: {cb_err}")
        return f"Error: CLI tool '{engine}' not found in PATH. Subprocess execution failed."

    async def route_task(
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
        return await self._execute(engine, prompt, files, task_id)

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

    async def _execute(
        self, engine: str, prompt: str, files: list[str] | None, task_id: str | None
    ) -> str:
        import asyncio
        max_retries = 3
        base_delay = 2

        for attempt in range(1, max_retries + 1):
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

                logger.info(f"🚀 [ROUTER] Dispatching to {engine} (Attempt {attempt}/{max_retries})...")

                # Selectively pass API keys from parent environment
                child_env = {
                    **os.environ,
                    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "sk-ant-fallback"),
                    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "gemini-fallback"),
                }

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=child_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=300)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.communicate()
                    logger.error(f"⏱️ [ROUTER] {engine} execution timed out (300s).")
                    if attempt < max_retries:
                        delay = base_delay ** attempt
                        logger.info(f"⏳ [ROUTER] Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        continue
                    return f"Error: {engine} timed out."

                stdout = stdout_bytes.decode('utf-8').strip()
                stderr = stderr_bytes.decode('utf-8').strip()

                output_content = stdout if process.returncode == 0 else f"ERROR:\n{stderr}\n{stdout}"

                if process.returncode != 0:
                    logger.error(f"❌ [ROUTER] {engine} failed. STDERR: {stderr}")
                    if attempt < max_retries:
                        delay = base_delay ** attempt
                        logger.info(f"⏳ [ROUTER] Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        continue

                # Log to DB for BM25 indexing (done only on success or exhaustion of retries)
                if task_id:
                    try:
                        db_path = Path("~/.cortex/cortex.db").expanduser()
                        if db_path.exists():
                            conn = sqlite3.connect(db_path)
                            digest = hashlib.sha256(output_content.encode("utf-8")).hexdigest()[:16]
                            # Escribir en la tabla de episodios/BM25
                            conn.execute(
                                "INSERT INTO episodes (session_id, event_type, project, content) VALUES (?, ?, ?, ?)",
                                (
                                    "cascade-sys",
                                    "llm_task_result",
                                    "cortex-engine",
                                    f"task_id:{task_id} engine:{engine} digest:{digest}\n{output_content[:500]}",
                                ),
                            )
                            # Opcional: Actualizar la tarea original
                            try:
                                status = "completed" if process.returncode == 0 else "failed"
                                conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
                            except sqlite3.OperationalError:
                                pass  # Ignorar si la tabla tasks no tiene esa estructura
                            conn.commit()
                            conn.close()
                    except Exception as db_e:
                        logger.error(f"⚠️ [ROUTER] Falló la persistencia en BD para indexación: {db_e}")

                if process.returncode != 0:
                    return f"Error ({engine}): {stderr}"

                return stdout

            except FileNotFoundError:
                logger.error("🔌 [ROUTER] CLI no encontrado en PATH. Activando fallback...")
                return self.fallback_response(engine, prompt)
            except Exception as e:
                logger.error(f"🔥 [ROUTER] Subprocess execution exception: {e}")
                if attempt < max_retries:
                    delay = base_delay ** attempt
                    logger.info(f"⏳ [ROUTER] Retrying in {delay} seconds due to exception...")
                    await asyncio.sleep(delay)
                    continue
                return f"Error: {e}"


if __name__ == "__main__":
    import asyncio
    # Test stub
    logging.basicConfig(level=logging.INFO)
    router = CascadeRouter()
    
    async def run_tests():
        logger.info(
            "Test Routing (Architecture): %s",
            router._select_engine("architecture", ["f1", "f2", "f3", "f4", "f5", "f6"]),
        )
        logger.info("Test Routing (Refactor): %s", router._select_engine("refactor", ["f1"]))
        logger.info("Test Routing (Snippet): %s", router._select_engine("snippet", []))
        
    asyncio.run(run_tests())
