import subprocess
import time

from web3 import Web3

# WATCHER config
FUNDER_ADDR = "0x2340E6826B572522E0a59Ad25f27b600C69820dd"
THRESHOLD_WEI = 500000000000000  # 0.0005 ETH
RPC_URL = "https://mainnet.base.org"
TSUNAMI_SCRIPT = "/Users/borjafernandezangulo/cortex/scripts/dust_tsunami_v2.py"
PYTHON_PATH = "/Users/borjafernandezangulo/cortex/.venv/bin/python"


def watch_and_fire():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    print(f"📡 [CORTEX WATCHER] Monitoring funder {FUNDER_ADDR}...")

    while True:
        try:
            bal = w3.eth.get_balance(FUNDER_ADDR)
            if bal >= THRESHOLD_WEI:
                print(
                    f"🔥 [SIGNAL DETECTED] Balance: {w3.from_wei(bal, 'ether')} ETH. Firing Tsunami..."
                )
                # Run the script
                result = subprocess.run(
                    [PYTHON_PATH, TSUNAMI_SCRIPT], capture_output=True, text=True
                )
                print(result.stdout)
                if "✅" in result.stdout:
                    print("🎯 [MISSION ACCOMPLISHED] Watcher standing down.")
                    break
            else:
                # Still waiting
                pass
        except Exception as e:
            print(f"⚠️ [WATCHER ERROR] {e}")

        time.sleep(30)  # Poll every 30s for responsiveness


if __name__ == "__main__":
    watch_and_fire()
