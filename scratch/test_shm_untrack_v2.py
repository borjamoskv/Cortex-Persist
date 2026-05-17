import multiprocessing.shared_memory as sm
from multiprocessing import resource_tracker
import os
import time


def test_shm_leak_v2():
    name = "test_shm_v2"
    try:
        shm = sm.SharedMemory(name=name, create=True, size=1024)
        print(f"Created SHM. shm.name='{shm.name}'")

        # On macOS/Python 3.14, let's see what the tracker thinks
        # We can't easily peek into the tracker, but we can try to be exhaustive

        target_name = shm.name
        if not target_name.startswith("/"):
            target_name = "/" + target_name

        print(f"Attempting to unregister '{target_name}'")
        try:
            resource_tracker.unregister(target_name, "shared_memory")
            print("Unregistered with slash")
        except Exception as e:
            print(f"Unregister with slash failed: {e}")

        # Also try without slash just in case
        if target_name.startswith("/"):
            no_slash = target_name[1:]
            print(f"Attempting to unregister '{no_slash}'")
            try:
                resource_tracker.unregister(no_slash, "shared_memory")
                print("Unregistered without slash")
            except Exception as e:
                print(f"Unregister without slash failed: {e}")

        if hasattr(shm, "_track"):
            shm._track = False

        shm.close()
        shm.unlink()
        print("Done. Waiting a bit for tracker to process...")
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_shm_leak_v2()
