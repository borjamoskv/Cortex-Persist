import multiprocessing.shared_memory as sm
from multiprocessing import resource_tracker
import time


def test_mock_tracker():
    name = "test_mock_init"
    # Backup
    orig_register = resource_tracker.register
    try:
        # Disable tracking
        resource_tracker.register = lambda *args, **kwargs: None
        print("Tracker disabled. Creating SHM...")
        shm = sm.SharedMemory(name=name, create=True, size=1024)
        print(f"Created SHM: {shm.name}")

        # Restore tracker
        resource_tracker.register = orig_register
        print("Tracker restored.")

        # Manually set track flag if needed (usually good practice)
        if hasattr(shm, "_track"):
            shm._track = False

        print("Cleaning up...")
        shm.close()
        shm.unlink()
        print("Done. Waiting for tracker...")
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
        resource_tracker.register = orig_register
    finally:
        resource_tracker.register = orig_register


if __name__ == "__main__":
    test_mock_tracker()
