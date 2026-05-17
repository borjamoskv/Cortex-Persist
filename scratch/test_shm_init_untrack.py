import multiprocessing.shared_memory as sm
from multiprocessing import resource_tracker
import time


def test_untrack_at_creation():
    name = "test_untrack_init"
    try:
        shm = sm.SharedMemory(name=name, create=True, size=1024)
        print(f"Created SHM: {shm.name}")

        # Untrack immediately
        print("Untracking immediately...")
        # We need to be careful with the name
        shm_name = shm._name
        resource_tracker.unregister(shm_name, "shared_memory")
        shm._track = False

        print("Using SHM...")
        # ... do something ...

        print("Cleaning up...")
        shm.close()
        shm.unlink()
        print("Done")
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_untrack_at_creation()
