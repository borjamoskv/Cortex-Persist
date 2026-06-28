"""
[C5-REAL] Byzantine Consensus Judge (Empirical Oracle)
Uses the SandboxJIT and Exergy economics to reach consensus on proposed code mutations.
"""

import hashlib
import logging
from typing import Any

from cortex.crypto.keys import KeyManager, Signer, Verifier
from cortex.engine.core.sandbox_jit import JITSandboxViolation, SandboxJIT
from cortex.swarm.exergy import ExergyBank

logger = logging.getLogger(__name__)


class ByzantineJudge:
    """
    Evaluates AST mutations empirically without trusting the agents' claims (Proof of Quality),
    and enforces strictly cryptographic Byzantine Consensus over proposed mutations.
    """

    def __init__(self, km=None):
        self.sandbox = SandboxJIT()
        self.bank = ExergyBank()
        self.km = km or KeyManager(service_name="cortex_swarm_judge")

        # The Judge needs its own key to sign consensus proofs
        self.judge_id = "byzantine_judge_root"
        if not self.km.get_private_key_b64(self.judge_id) or not self.km.get_public_key_b64(
            self.judge_id
        ):
            self.km.generate_and_store_key(self.judge_id)

    def evaluate_proposals(
        self, original_state: dict[str, Any], proposals: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """
        Receives a list of signed proposals from different agents:
        [{"agent_id": "alpha", "ast_code": "def func()...", "signature_b64": "...", "timestamp": "..."}, ...]

        Returns a ConsensusProof dictionary, or None if all failed.
        """
        winning_agent = None
        best_win_rate = -1.0
        winning_ast = None

        for prop in proposals:
            agent_id = prop.get("agent_id")
            code = prop.get("ast_code")
            signature_b64 = prop.get("signature_b64")
            timestamp = prop.get("timestamp")

            if not all([agent_id, code, signature_b64, timestamp]):
                logger.warning(f"Proposal from {agent_id} lacks cryptographic fields. Slashed.")
                if agent_id:
                    wallet = self.bank.register_agent(agent_id)
                    wallet.failed_commits += 1
                    wallet.balance -= self.bank.STAKE_REQUIRED_PER_PROPOSAL
                continue

            # JIT Enrollment: Generate key if agent doesn't have one (Warning)
            pub_key_b64 = self.km.get_public_key_b64(agent_id)  # type: ignore
            if not pub_key_b64:
                logger.warning(f"[AUDIT] JIT Cryptographic Enrollment for Agent: {agent_id}")
                pub_key_b64 = self.km.generate_and_store_key(agent_id)  # type: ignore
                # In a real spoofing test, the signature won't match this newly generated key anyway.

            # Cryptographic Verification (PoQC)
            payload_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()  # type: ignore
            try:
                is_valid = Verifier.verify_signature(
                    pub_key_b64, payload_hash, timestamp, signature_b64
                )  # type: ignore
            except (ValueError, TypeError) as e:
                logger.warning(f"[SECURITY] Signature validation failed structurally: {e}")
                is_valid = False

            if not is_valid:
                logger.error(
                    f"[SECURITY] Cryptographic spoofing or corruption detected for agent {agent_id}. Slashed."
                )
                wallet = self.bank.register_agent(agent_id)  # type: ignore
                wallet.failed_commits += 1
                wallet.balance -= self.bank.STAKE_REQUIRED_PER_PROPOSAL
                continue

            wallet = self.bank.register_agent(agent_id)  # type: ignore
            if not self.bank.stake(agent_id):  # type: ignore
                continue  # Agent bankrupt, ignore proposal

            try:
                # 1. Ejecución Aislada JIT
                logger.info(f"Evaluating verified AST from agent {agent_id}...")
                _new_state = self.sandbox.execute(code, context=dict(original_state))  # type: ignore

                self.bank.reward(agent_id)  # type: ignore

                # Consenso: El agente con mayor histórico (Win Rate) gana en caso de múltiples ASTs válidos
                win_rate = wallet.successful_commits / max(
                    1, wallet.successful_commits + wallet.failed_commits
                )
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    winning_agent = agent_id
                    winning_ast = code

            except JITSandboxViolation as e:
                logger.warning(f"Agent {agent_id} SLASHED due to Sandbox Violation: {e}")
                self.bank.slash(agent_id)  # type: ignore
            except (SyntaxError, TypeError, NameError, ValueError, AttributeError) as e:
                logger.warning(f"Agent {agent_id} SLASHED due to AST execution error: {e}")
                self.bank.slash(agent_id)  # type: ignore
            except (KeyError, OSError, RuntimeError) as e:
                logger.critical(f"Host System Error evaluating agent {agent_id}: {e}")
                raise RuntimeError(f"BFT Consensus halted. Host execution degraded: {e}")

        if winning_agent:
            logger.info(f"🏆 Consensus reached. Winner: {winning_agent}")

            # The Judge signs the final consensus choice
            from datetime import datetime, timezone

            consensus_timestamp = datetime.now(timezone.utc).isoformat()
            consensus_hash = hashlib.sha256(winning_ast.encode("utf-8")).hexdigest()  # type: ignore
            judge_priv = self.km.get_private_key_b64(self.judge_id)
            consensus_sig = Signer.sign_payload(judge_priv, consensus_hash, consensus_timestamp)  # type: ignore

            return {
                "winning_agent": winning_agent,
                "ast_code": winning_ast,
                "consensus_timestamp": consensus_timestamp,
                "consensus_signature_b64": consensus_sig,
                "judge_id": self.judge_id,
            }
        else:
            logger.error("🛑 Consensus failed. All agents slashed or bankrupt.")

        return None
