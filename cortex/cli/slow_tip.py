"""
CORTEX v5.2 — Slow-Op Tip Emitter.

Automatically surfaces contextual tips whenever a CLI operation exceeds
a configurable latency threshold. Zero overhead on fast paths.

Architecture:
  - SlowOpTipEmitter: daemon thread + threading.Event for clean shutdown
  - with_slow_tips(): context manager for any blocking operation
  - slow_tips_spinner(): Rich-integrated spinner that emits tips inline
  - @tip_on_slow: decorator for Click commands

Usage::

    # Context manager
    with with_slow_tips("Searching CORTEX memory…"):
        results = engine.search(project, limit=500)

    # Decorator
    @tip_on_slow(threshold=2.0)
    def my_command(): ...

    # Rich spinner with live tips
    with slow_tips_spinner("Running swarm…") as spinner:
        run_swarm()
"""

from __future__ import annotations

import functools
import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Generator

__all__ = [
    "SlowOpTipEmitter",
    "tip_on_slow",
    "slow_tips_spinner",
    "with_slow_tips",
]

if TYPE_CHECKING:
    pass

# Default thresholds
_DEFAULT_THRESHOLD = 2.0   # seconds before first tip fires
_DEFAULT_INTERVAL = 8.0    # seconds between subsequent tips
_DEFAULT_LANG = "es"


# ─── Core Emitter ────────────────────────────────────────────────────


class SlowOpTipEmitter:
    """Daemon thread that emits tips while a slow operation runs.

    Thread starts immediately; tips only surface after ``threshold`` seconds.
    Call ``stop()`` (or use as context manager) to cleanly terminate.

    Thread is daemonized — it will not prevent process exit.
    """

    __slots__ = (
        "_stop_event",
        "_thread",
        "_threshold",
        "_interval",
        "_lang",
        "_engine",
        "_label",
    )

    def __init__(
        self,
        label: str = "Thinking…",
        *,
        threshold: float = _DEFAULT_THRESHOLD,
        interval: float = _DEFAULT_INTERVAL,
        lang: str = _DEFAULT_LANG,
        engine=None,
    ) -> None:
        self._label = label
        self._threshold = threshold
        self._interval = interval
        self._lang = lang
        self._engine = engine
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="cortex-tip-emitter",
        )

    # ─── Lifecycle ───────────────────────────────────────────────

    def start(self) -> "SlowOpTipEmitter":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=1.0)

    def __enter__(self) -> "SlowOpTipEmitter":
        return self.start()

    def __exit__(self, *_) -> None:
        self.stop()

    # ─── Tip loop ────────────────────────────────────────────────

    def _run(self) -> None:
        """Wait for threshold, then emit tips at interval until stopped."""
        # Wait for threshold before emitting first tip
        if self._stop_event.wait(timeout=self._threshold):
            return  # Operation finished before threshold — no tip needed

        self._emit_tip()

        # Subsequent tips at interval
        while not self._stop_event.wait(timeout=self._interval):
            self._emit_tip()

    def _emit_tip(self) -> None:
        """Emit a single tip to Rich console. Fully isolated — never crashes."""
        try:
            from rich.panel import Panel

            from cortex.cli import console
            from cortex.cli.tips import TipsEngine

            tips_engine = TipsEngine(
                self._engine,
                lang=self._lang,
                include_dynamic=self._engine is not None,
            )
            tip = tips_engine.random()
            console.print()
            console.print(
                Panel(
                    f"[white]{tip.content}[/white]",
                    title=f"[bold cyan]💡 {tip.category.value.upper()}[/bold cyan]",
                    subtitle=f"[dim]mientras esperas · {tip.source}[/dim]",
                    border_style="bright_green",
                    padding=(0, 2),
                )
            )
        except Exception:  # noqa: BLE001
            pass  # Tips are non-critical; never break the CLI


# ─── Context Manager ─────────────────────────────────────────────────


@contextmanager
def with_slow_tips(
    label: str = "Procesando…",
    *,
    threshold: float = _DEFAULT_THRESHOLD,
    interval: float = _DEFAULT_INTERVAL,
    lang: str = _DEFAULT_LANG,
    engine=None,
) -> Generator[SlowOpTipEmitter, None, None]:
    """Context manager that emits tips if the block takes longer than threshold.

    Example::

        with with_slow_tips("Searching CORTEX…", threshold=2.0):
            results = engine.search(project, limit=10_000)
    """
    emitter = SlowOpTipEmitter(
        label,
        threshold=threshold,
        interval=interval,
        lang=lang,
        engine=engine,
    )
    emitter.start()
    try:
        yield emitter
    finally:
        emitter.stop()


# ─── Rich Spinner Integration ─────────────────────────────────────────


@contextmanager
def slow_tips_spinner(
    label: str = "Procesando…",
    *,
    threshold: float = _DEFAULT_THRESHOLD,
    interval: float = _DEFAULT_INTERVAL,
    lang: str = _DEFAULT_LANG,
    engine=None,
    spinner: str = "dots",
) -> Generator[None, None, None]:
    """Rich spinner + slow-op tips combined.

    Shows an animated spinner for immediate feedback, and emits contextual
    tips after ``threshold`` seconds if the operation takes long.

    Example::

        with slow_tips_spinner("Running MEJORAlo…"):
            run_mejoralo()
    """
    try:
        from rich.live import Live
        from rich.spinner import Spinner
        from rich.text import Text

        from cortex.cli import console

        spin = Spinner(spinner, text=Text(f" {label}", style="bold cyan"))

        emitter = SlowOpTipEmitter(
            label,
            threshold=threshold,
            interval=interval,
            lang=lang,
            engine=engine,
        )

        with Live(spin, console=console, refresh_per_second=10, transient=True):
            emitter.start()
            try:
                yield
            finally:
                emitter.stop()
    except ImportError:
        # Fallback: plain context manager without spinner
        with with_slow_tips(label, threshold=threshold, interval=interval, lang=lang, engine=engine):
            yield


# ─── Decorator ───────────────────────────────────────────────────────


def tip_on_slow(
    threshold: float = _DEFAULT_THRESHOLD,
    interval: float = _DEFAULT_INTERVAL,
    lang: str = _DEFAULT_LANG,
    label: str | None = None,
    use_spinner: bool = False,
) -> Callable:
    """Decorator that emits tips if the decorated function exceeds threshold.

    Works with both regular functions and Click commands.

    Example::

        @cli.command()
        @tip_on_slow(threshold=2.0)
        def export(project: str): ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            op_label = label or f"Ejecutando {fn.__name__}…"
            ctx_mgr = slow_tips_spinner if use_spinner else with_slow_tips
            with ctx_mgr(
                op_label,
                threshold=threshold,
                interval=interval,
                lang=lang,
            ):
                return fn(*args, **kwargs)
        return wrapper
    return decorator


# ─── Async variant ───────────────────────────────────────────────────


@contextmanager
def with_slow_tips_sync(
    label: str = "Procesando…",
    threshold: float = _DEFAULT_THRESHOLD,
    interval: float = _DEFAULT_INTERVAL,
    lang: str = _DEFAULT_LANG,
    engine=None,
) -> Generator[SlowOpTipEmitter, None, None]:
    """Alias for with_slow_tips (sync-friendly name for clarity in CLI code)."""
    with with_slow_tips(label, threshold=threshold, interval=interval, lang=lang, engine=engine) as e:
        yield e
