import logging
import os
import sys

logger = logging.getLogger(__name__)

# Append paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sdk/babylon60-mtk/src')))

from babylon60_mtk import install_bootstrap_watchdog
from babylon60_mtk.watchdog import _is_mitosis_branch


def run_tests():
    logger.info("[TEST] Instalando MTK Bootstrap Watchdog...")
    install_bootstrap_watchdog()
    
    # 1. Test read operation (should always pass)
    try:
        with open("cortex/nodes/causal_framework_nodes.py") as f:
            pass
        logger.info("[OK] Leer archivos del core está permitido.")
    except PermissionError:
        logger.info("[FAIL] Lectura bloqueada incorrectamente.")
        sys.exit(1)
        
    # 2. Check current branch state (Should be True in this environment)
    is_mitosis = _is_mitosis_branch()
    logger.info(f"[TEST] Estamos en rama de mitosis nativamente? {is_mitosis}")
    
    # 3. Test write operation - ALLOWED (Mitosis branch)
    test_file = "cortex/test_watchdog_file.txt"
    if is_mitosis:
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info("[OK] Escritura permitida porque estamos en una rama de mitosis.")
        except PermissionError as e:
            logger.info(f"[FAIL] Escritura bloqueada incorrectamente estando en mitosis. Error: {e}")
            sys.exit(1)
            
    # 4. Test write operation - BLOCKED (Mock non-mitosis branch)
    logger.info("[TEST] Simulando rama externa (main)...")
    os.environ["MOCK_NON_MITOSIS"] = "1"
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        logger.info("[FAIL] Escritura permitida sin estar en mitosis. Watchdog falló.")
        sys.exit(1)
    except PermissionError as e:
        logger.info(f"[OK] Escritura bloqueada correctamente bajo entorno hostil: {e}")
    finally:
        os.environ.pop("MOCK_NON_MITOSIS", None)
            
    logger.info("[SUCCESS] Bootstrap Watchdog funcionando de acuerdo a LEY 10 (Autopoiesis).")

if __name__ == "__main__":
    run_tests()
