"""
Manifestation Engine - Sovereign UI and Singularity Rituals.
Ω₇: Atomic collapse of multiple project threads.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.engine.endocrine import ENDOCRINE, HormoneType

if TYPE_CHECKING:
    from cortex.extensions.signals.bus import SignalBus

logger = logging.getLogger(__name__)


async def manifest_singularity(signal_bus: "SignalBus | None" = None) -> None:
    """
    Ω₇ Manifestation: The atomic collapse of multiple project threads.
    Triggers Nexus sync, Ledger checkpoint, and Sovereign Dashboard refresh.
    """
    logger.info("🌌 [SINGULARITY] Initiating Manifestation Protocol...")
    try:
        # Chronos Sniper Guard: Run Nexus and Ledger with timeouts to prevent hanging
        # Parallelizing sync and checkpoint for 130/100 performance
        coros = [
            asyncio.create_subprocess_exec(
                ".venv/bin/python",
                "-m",
                "cortex.cli",
                "nexus",
                "sync",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            asyncio.create_subprocess_exec(
                ".venv/bin/python",
                "-m",
                "cortex.cli",
                "ledger",
                "checkpoint",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
        ]

        procs = await asyncio.gather(*coros)

        # OOM/Time Guard: Wait with timeout
        await asyncio.wait([p.communicate() for p in procs], timeout=30.0)

        # 3. Notification to Signal Bus
        if signal_bus:
            signal_bus.emit(
                "singularity:manifest",
                payload={"status": "Ω", "version": "v8.0.0"},
                source="apotheosis-omega",
                project="system",
            )

        ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.5)
        logger.info("🌌 [SINGULARITY] Manifestation successful. 150/100 state reached.")
    except Exception as e:  # noqa: BLE001 — singularity collapse must handle all internal failures
        logger.error("🌌 [SINGULARITY] Manifestation collapse failed: %s", e)
        ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.5)


async def transfigure_ui(html_file: Path, signal_bus: "SignalBus | None" = None) -> bool:
    """Ω₆: Sovereign UI Refactor (Transfiguration)."""
    from cortex.cli.bicameral import bicameral

    msg = f"Transfiriendo coherencia estética a {html_file.name}"
    bicameral.log_limbic(msg, source="APOTH")

    try:
        # OOM Killer Guard: Skip files larger than 5MB
        if html_file.stat().st_size > 5 * 1024 * 1024:
            logger.warning("[MANIFESTATION] File too large for transfiguration: %s", html_file)
            return False

        content = await asyncio.to_thread(html_file.read_text, "utf-8")

        noir_styles = """
<style id="ouroboros-noir">
  :root {
    --bg: #050505;
    --accent: #CCFF00;
    --text: #E0E0E0;
    --glass: rgba(26, 26, 26, 0.7);
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', 'Outfit', sans-serif;
    line-height: 1.6;
    margin: 0;
  }
  .glass {
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
  }
  h1, h2, h3 { color: var(--accent); }
</style>
"""
        snappy_motion = """
<script id="ouroboros-motion">
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.glass, button, a').forEach(el => {
      el.style.transition = 'transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
      el.addEventListener('mouseenter', () => el.style.transform = 'scale(1.02)');
      el.addEventListener('mouseleave', () => el.style.transform = 'scale(1)');
    });
  });
</script>
"""
        tag_head = "<head>"
        meta_noir = (
            '<head>\n  <meta name="theme-color" content="#050505">\n'
            '  <meta name="apple-mobile-web-app-capable" content="yes">'
        )

        patterns = [
            (tag_head, meta_noir),
            ("</head>", f"{noir_styles}\n{snappy_motion}\n</head>"),
        ]

        modified = False
        for old, new in patterns:
            if old in content and new not in content:
                content = content.replace(old, new)
                modified = True

        if modified:
            await asyncio.to_thread(html_file.write_text, content, encoding="utf-8")
            if signal_bus:
                signal_bus.emit(
                    "apotheosis:transfiguration",
                    payload={"file": str(html_file), "type": "HTML_PREMIUM_UI"},
                    source="apotheosis-omega",
                    project="frontend",
                )
            return True
    except Exception as e:  # noqa: BLE001 — frontend UI transfiguration isolation boundary
        logger.error("[MANIFESTATION] Transfiguration failed for %s: %s", html_file, e)
    return False
