import sys
import os
import json
import logging

# Ensure imports
cortex_core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cortex-core"))
sys.path.append(cortex_core_path)
from persistence import VSAMemory

# Import history
sys.path.append(os.path.expanduser("~/.gemini/antigravity/skills/Autodidact-History-OMEGA/scripts"))
try:
    import retrieve_history
except ImportError as e:
    print(f"Failed to import retrieve_history: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SAGE_COUNCIL_INGEST")


def main():
    vsa = VSAMemory()
    milestones = retrieve_history.MILESTONES

    logger.info(f"Initiating SAGE_COUNCIL ingestion: {len(milestones)} milestones to VSA Memory.")

    count = 0
    for key, data in milestones.items():
        summary = f"HISTORY_MILESTONE_{key.upper()}: {data['title']}"
        content = json.dumps(
            {
                "year": data["year"],
                "description": data["description"],
                "thermodynamics": data["thermodynamics"],
            }
        )
        vsa.record(summary, content)
        logger.info(f"Ingested -> {summary}")
        count += 1

    logger.info(f"C5-REAL Ledger updated. Total milestones crystallized in VSA: {count}")


if __name__ == "__main__":
    main()
