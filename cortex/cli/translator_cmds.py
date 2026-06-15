# [C5-REAL] Exergy-Maximized
"""
CORTEX CLI - Distributed Translation Daemon Commands.
Provides start and request entrypoints for sharded translation operations.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import cli, console
from cortex.extensions.daemon.translator import ShardedTranslationDaemon
from cortex.extensions.signals.sharded_bus import ShardedAsyncSignalBus


@cli.group("translator")
def translator_group():
    """SOVEREIGN TRANSLATOR - Distributed translation daemon & request client."""
    pass


@translator_group.command("start")
@click.option(
    "--shards-dir",
    default="~/.cortex/10k_shards",
    help="Directory containing SQLite database shards.",
)
@click.option(
    "--worker-id",
    default="translation_worker_0",
    help="Unique worker identifier for this daemon instance.",
)
@click.option(
    "--shard-indices",
    default=None,
    help="Comma-separated list of shard indices (e.g. 0,1,2,3) to poll. Defaults to all.",
)
@click.option(
    "--poll-interval",
    default=3.0,
    type=float,
    help="Polling interval in seconds.",
)
@click.option(
    "--model",
    default="gemini-2.0-flash",
    help="Gemini LLM model version to use.",
)
def start_translator(
    shards_dir: str, worker_id: str, shard_indices: str | None, poll_interval: float, model: str
):
    """Start the distributed translation daemon worker."""
    shards_path = Path(shards_dir).expanduser()
    shards_path.mkdir(parents=True, exist_ok=True)

    parsed_indices: list[int] | None = None
    if shard_indices:
        try:
            parsed_indices = [int(i.strip()) for i in shard_indices.split(",")]
        except ValueError:
            raise click.BadParameter("shard-indices must be a comma-separated list of integers.")

    console.print(
        Panel(
            f"⚡ [bold]CORTEX SHARDED TRANSLATOR DAEMON[/]\n"
            f"Worker ID: [cyan]{worker_id}[/]\n"
            f"Shards Location: [cyan]{shards_path}[/]\n"
            f"Partition Shard Indices: [bold green]{parsed_indices or 'All'}[/]\n"
            f"Model: [yellow]{model}[/]\n"
            f"Poll Interval: [cyan]{poll_interval}s[/]",
            border_style="magenta",
        )
    )

    daemon = ShardedTranslationDaemon(
        shards_dir=shards_path,
        worker_id=worker_id,
        shard_indices=parsed_indices,
        poll_interval_s=poll_interval,
        model=model,
    )

    try:
        asyncio.run(daemon.run_loop())
    except KeyboardInterrupt:
        console.print("\n[bold red]🛑 Worker shutting down...[/]")
        daemon.stop()


@translator_group.command("request")
@click.option(
    "--shards-dir",
    default="~/.cortex/10k_shards",
    help="Directory containing SQLite database shards.",
)
@click.option(
    "--text",
    required=True,
    help="Text content to translate.",
)
@click.option(
    "--target-lang",
    default="en",
    help="Target language code (e.g. en, es, fr).",
)
@click.option(
    "--source-lang",
    default=None,
    help="Optional source language code. Autodetected if omitted.",
)
@click.option(
    "--routing-key",
    default="translation_requests",
    help="Routing key for sharding request placement.",
)
@click.option(
    "--timeout",
    default=15.0,
    type=float,
    help="Time in seconds to wait for translation response.",
)
@click.option(
    "--direct",
    is_flag=True,
    help="Perform translation synchronously in-process, bypassing the sharded bus entirely.",
)
def request_translation(
    shards_dir: str,
    text: str,
    target_lang: str,
    source_lang: str | None,
    routing_key: str,
    timeout: float,
    direct: bool,
):
    """Submit a translation task to the sharded bus and wait for result."""
    shards_path = Path(shards_dir).expanduser()

    if direct:

        async def _direct_run():
            daemon = ShardedTranslationDaemon(
                shards_dir=shards_path,
                worker_id="direct_translator",
                model="gemini-2.0-flash",
            )
            console.print(
                "⚡ [bold green]Bypassing Bus: Performing in-process direct sync translation[/]..."
            )
            start_t = time.perf_counter()
            try:
                # Detect source lang if not provided
                resolved_src = source_lang
                if not resolved_src:
                    from cortex.compaction.lang_compress import detect_language

                    try:
                        resolved_src = detect_language(text)
                    except Exception:
                        resolved_src = "unknown"

                translated = await daemon.translate_text(text, target_lang, resolved_src)
                duration_ms = (time.perf_counter() - start_t) * 1000
                is_fallback = "[OFFLINE FALLBACK]:" in translated

                res_table = Table(
                    title="📊 Translation Stats (Direct Sync)",
                    show_header=False,
                    border_style="cyan",
                )
                res_table.add_row("Source Lang", resolved_src)
                res_table.add_row("Target Lang", target_lang)
                res_table.add_row("Execution Time", f"{duration_ms:.1f} ms")
                res_table.add_row("Offline Fallback", str(is_fallback))
                console.print(res_table)
                console.print(
                    Panel(
                        f"[bold white]{translated}[/bold white]",
                        title="✨ Translation Result",
                        border_style="green",
                    )
                )
            except Exception as e:
                console.print(
                    Panel(f"[red]Error: {e}[/]", title="❌ Translation Failed", border_style="red")
                )

        asyncio.run(_direct_run())
        return

    correlation_id = f"tr-req-{uuid.uuid4().hex[:12]}"

    async def _run():
        bus = ShardedAsyncSignalBus(base_dir=shards_path)
        await bus.initialize()

        console.print(f"📤 [bold green]Emitting translation request[/] ({correlation_id})...")
        await bus.emit(
            event_type="translation:request",
            payload={
                "text": text,
                "target_lang": target_lang,
                "source_lang": source_lang,
                "correlation_id": correlation_id,
            },
            source="translator_cli",
            routing_key=routing_key,
        )

        console.print(f"⏳ Waiting for worker to process request (timeout {timeout}s)...")
        start = time.monotonic()
        response_sig = None
        poll_delay = 0.02  # Start polling at 20ms for ultra-low latency

        while time.monotonic() - start < timeout:
            signals = await bus.history(routing_key=correlation_id)
            for sig in signals:
                if (
                    sig.event_type in ("translation:completed", "translation:failed")
                    and sig.payload.get("correlation_id") == correlation_id
                ):
                    response_sig = sig
                    break
            if response_sig:
                break
            await asyncio.sleep(poll_delay)
            poll_delay = min(0.5, poll_delay * 1.5)  # Adaptive backoff to max 500ms

        await bus.close()

        if not response_sig:
            console.print(
                "[bold red]❌ TIMEOUT: No translation worker responded within the specified time limit.[/]"
            )
            return

        payload = response_sig.payload
        if response_sig.event_type == "translation:failed":
            console.print(
                Panel(
                    f"[red]Error: {payload.get('error')}[/]",
                    title="❌ Translation Failed",
                    border_style="red",
                )
            )
            return

        # Success - Display stats and result
        res_table = Table(title="📊 Translation Stats", show_header=False, border_style="cyan")
        res_table.add_row("Correlation ID", correlation_id)
        res_table.add_row("Source Lang", payload.get("source_lang"))
        res_table.add_row("Target Lang", payload.get("target_lang"))
        res_table.add_row("Execution Time", f"{payload.get('duration_ms', 0):.1f} ms")
        res_table.add_row("Worker ID", payload.get("worker_id"))
        res_table.add_row("Offline Fallback", str(payload.get("offline_fallback", False)))
        if payload.get("tokens_saved", 0) > 0:
            res_table.add_row(
                "Token Savings (Est)",
                f"{payload.get('tokens_saved')} tokens ({payload.get('savings_pct'):.1f}%)",
            )

        console.print(res_table)
        console.print(
            Panel(
                f"[bold white]{payload.get('translated_text')}[/bold white]",
                title="✨ Translation Result",
                border_style="green",
            )
        )

    asyncio.run(_run())
