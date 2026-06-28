import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from cortex.agents.primitives.dispatcher import apex_dispatcher
from cortex.engine.crystallizer import auto_crystallizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("NightShift")


class NightShiftDaemon:
    """
    [C5-REAL] NightShift Thermodynamic Expulsion Daemon (Suntsitu).
    Sweeps episodic memory (transcripts) and compresses it into dense Axioms.
    """

    def __init__(self, transcript_path: str, output_dir: str = ".cortex/axioms") -> None:
        self.transcript_path = Path(transcript_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute_purge(self) -> str:
        """Runs the thermodynamic sweep over the given transcript."""
        if not self.transcript_path.exists():
            logger.error(f"Transcript not found at {self.transcript_path}")
            apex_dispatcher.execute("OP_APOPTOSIS")

        logger.info(f"Initiating NightShift Purge on {self.transcript_path.name}")

        raw_events = []
        with open(self.transcript_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line)
                    # Filter for highly exergic nodes
                    if step.get("type") == "USER_INPUT":
                        raw_events.append(f"[USER] {step.get('content', '')[:200]}")
                    elif step.get("type") == "PLANNER_RESPONSE":
                        # Extract tools used or hashes
                        content = step.get("content", "")
                        if "Git Sentinel Hash:" in content or "C5-REAL" in content:
                            raw_events.append(f"[KERNEL] {content[:300]}")
                except (ValueError, TypeError, OSError, KeyError):
                    pass

        # Collate episodic memory
        episodic_memory = "\n".join(raw_events)
        logger.info(
            f"Extracted {len(raw_events)} exergic events. Total length: {len(episodic_memory)} chars."
        )

        # Pass to AutoCrystallizer
        frozen_fact = auto_crystallizer.crystallize_fact(episodic_memory)

        # Save absolute Axiom
        timestamp = datetime.now().strftime("%Y%md_%H%M%S")
        axiom_file = self.output_dir / f"AXIOM_{timestamp}.json"

        # Unpack MappingProxyType for JSON serialization
        axiom_dict = dict(frozen_fact)

        with open(axiom_file, "w", encoding="utf-8") as out:
            json.dump(axiom_dict, out, indent=2, ensure_ascii=False)

        logger.info(
            f"NightShift complete. Episodic noise purged. Axiom crystallized at {axiom_file}"
        )
        return str(axiom_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NightShift Daemon (Suntsitu)")
    parser.add_argument("transcript", help="Path to transcript.jsonl")
    args = parser.parse_args()

    daemon = NightShiftDaemon(args.transcript)
    axiom_path = daemon.execute_purge()
    print(f"\\n[C5-REAL] NightShift successful. Structural Invariant: {axiom_path}")
