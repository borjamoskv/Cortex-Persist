import asyncio
import threading
from cortex.swarm.autopulse import process_queue
from cortex.swarm.tensor_glial import TensorGlialLegion

def start_swarm_daemon():
    """Start the Swarm Autopoiesis engine in a background thread."""
    def run():
        asyncio.run(process_queue())
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
