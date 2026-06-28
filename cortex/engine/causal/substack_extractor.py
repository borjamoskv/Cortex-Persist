import logging
import subprocess

logger = logging.getLogger("Cortex.SubstackExtractor")


class SubstackExtractor:
    """
    [C5-REAL] Extractor de materia prima causal.
    Lee directamente del Git Ledger para garantizar que toda emisión
    se base en invariantes físicos inmutables.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def extract_commit_payload(self, commit_hash: str) -> dict[str, str]:
        """
        Extrae el SSOT (Single Source of Truth) de un commit.
        """
        try:
            # Get the commit message
            msg_cmd = ["git", "show", "-s", "--format=%B", commit_hash]
            msg_result = subprocess.run(
                msg_cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            commit_msg = msg_result.stdout.strip()

            # Get the full diff
            diff_cmd = ["git", "show", commit_hash]
            diff_result = subprocess.run(
                diff_cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            raw_diff = diff_result.stdout.strip()

            logger.info(f"Causal payload extracted for node: {commit_hash[:7]}")

            return {"hash": commit_hash, "message": commit_msg, "diff": raw_diff}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract hash {commit_hash}: {e.stderr}")
            raise RuntimeError(f"C5-REAL extraction failure for hash {commit_hash}") from e
