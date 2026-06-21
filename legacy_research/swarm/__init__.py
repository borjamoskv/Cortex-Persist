"""Cortex swarm — SubagentRunner, AgentRegistry and built-in handlers."""
import asyncio
import threading

from cortex.swarm.autopulse import process_queue


def start_swarm_daemon():
    """Start the Swarm Autopoiesis engine in a background thread."""
    def run():
        asyncio.run(process_queue())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
