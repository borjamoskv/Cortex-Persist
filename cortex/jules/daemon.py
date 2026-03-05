"""MOSKV-Jules — Background daemon and MoskvDaemon monitor."""

from __future__ import annotations

import logging
import threading

from cortex.jules.models import AgentTask, JulesAlert, TaskStatus
from cortex.jules.queue import TaskQueue
from cortex.jules.runner import JulesAgent

__all__ = ["JulesDaemon", "JulesMonitor"]

logger = logging.getLogger("cortex.jules.daemon")

_DEFAULT_POLL = 60      # seconds between queue polls
_DEFAULT_MAX_CONCURRENT = 2


class JulesDaemon:
    """Background daemon that polls the TaskQueue and runs JulesAgent tasks.

    Designed to run as daemon threads inside MoskvDaemon.
    """

    def __init__(
        self,
        queue: TaskQueue | None = None,
        poll_interval: int = _DEFAULT_POLL,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
        llm_provider: str = "qwen",
        github_token: str | None = None,
        github_repos: list[str] | None = None,
    ) -> None:
        self._queue = queue or TaskQueue()
        self._poll_interval = poll_interval
        self._max_concurrent = max_concurrent
        self._llm_provider = llm_provider
        self._github_token = github_token
        self._github_repos = github_repos or []
        self._stop_event = threading.Event()
        self._active: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._completed: list[JulesAlert] = []

    # ── Control ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the polling loop (blocking). Run in a daemon thread."""
        logger.info("🤖 Jules daemon started (poll=%ds, max=%d)", self._poll_interval, self._max_concurrent)

        # Start GitHub ingestor if configured
        if self._github_token and self._github_repos:
            gh_thread = threading.Thread(
                target=self._github_poll_loop,
                name="JulesGitHub",
                daemon=True,
            )
            gh_thread.start()

        while not self._stop_event.is_set():
            self._tick()
            self._stop_event.wait(timeout=self._poll_interval)

        logger.info("🤖 Jules daemon stopped")

    def stop(self) -> None:
        self._stop_event.set()

    # ── Internal loop ──────────────────────────────────────────────────

    def _tick(self) -> None:
        """Single poll cycle — spawn worker threads up to max_concurrent."""
        with self._lock:
            # Clean up finished threads
            done = [tid for tid, t in self._active.items() if not t.is_alive()]
            for tid in done:
                del self._active[tid]

            slots = self._max_concurrent - len(self._active)

        for _ in range(slots):
            task = self._queue.pop_next()
            if task is None:
                break
            t = threading.Thread(
                target=self._run_task_thread,
                args=(task,),
                name=f"Jules-{task.id}",
                daemon=True,
            )
            with self._lock:
                self._active[task.id] = t
            t.start()
            logger.info("🚀 Spawned worker thread for task [%s]", task.id)

    def _run_task_thread(self, task: AgentTask) -> None:
        """Run a single task in its own thread."""
        agent = JulesAgent(llm_provider=self._llm_provider)
        result = agent.run_task_sync(task, self._queue)

        alert = JulesAlert(
            task_id=result.id,
            title=result.title,
            status=result.status,
            message=result.result[:200] if result.status == TaskStatus.DONE else result.error[:200],
        )
        with self._lock:
            self._completed.append(alert)

    def _github_poll_loop(self) -> None:
        """Polls GitHub for issues labeled 'jules' and enqueues them."""
        from cortex.jules.github_ingestor import GitHubIngestor

        ingestor = GitHubIngestor(
            token=self._github_token,
            repos=self._github_repos,
            queue=self._queue,
        )
        while not self._stop_event.is_set():
            try:
                ingestor.poll()
            except Exception as e:
                logger.warning("GitHub ingestor error: %s", e)
            self._stop_event.wait(timeout=300)  # poll every 5 minutes

    # ── Status for MoskvDaemon ─────────────────────────────────────────

    def pop_completed_alerts(self) -> list[JulesAlert]:
        """Return and clear the list of recently completed task alerts."""
        with self._lock:
            alerts = list(self._completed)
            self._completed.clear()
        return alerts

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)


class JulesMonitor:
    """Monitor adapter for MoskvDaemon integration."""

    def __init__(self, daemon: JulesDaemon) -> None:
        self._daemon = daemon

    def check(self) -> list[JulesAlert]:
        """Called by MoskvDaemon.check() — returns completed task alerts."""
        return self._daemon.pop_completed_alerts()
