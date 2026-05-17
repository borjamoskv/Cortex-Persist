import multiprocessing.shared_memory as sm
from multiprocessing import resource_tracker
import os


def test_shm_leak():
    name = "test_shm_untrack"
    try:
        shm = sm.SharedMemory(name=name, create=True, size=1024)
        print(f"Created SHM: {shm.name}")

        # Check if it's registered
        # resource_tracker doesn't have an 'is_registered' but we can try to unregister it

        # Manually untrack
        print(f"Untracking {shm.name}")
        resource_tracker.unregister(shm.name, "shared_memory")

        # Standard way to prevent tracker from complaining if we manually unlink
        if hasattr(shm, "_track"):
            shm._track = False

        shm.close()
        shm.unlink()
        print("Done")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            temp = sm.SharedMemory(name=name)
            temp.close()
            temp.unlink()
            print("Cleaned up in finally")
        except:
            pass


if __name__ == "__main__":
    test_shm_leak()
