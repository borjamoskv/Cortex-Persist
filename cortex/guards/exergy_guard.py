import logging
import re

logger = logging.getLogger("cortex.guards")

DECORATIVE_TERMS = [
    r"por supuesto", r"entendido", r"como un modelo de lenguaje",
    r"espero que te sea útil", r"aquí tienes", r"en conclusión",
    r"procedo a explicarte", r"estoy aquí para ayudarte",
    r"friendly message", r"help you", r"say hello", r"hi there"
]

def calculate_exergy(text: str) -> float:
    """Calculates thermodynamic yield (exergy) of a string."""
    if not text.strip():
        return 0.0

    text_lower = text.lower()
    matches = []
    for term in DECORATIVE_TERMS:
        if re.search(term, text_lower):
            matches.append(term)

    if not matches:
        return 1.0

    # Penalty based on decorative density
    penalty = (len(matches) * 0.2)
    score = max(0.0, 1.0 - penalty)

    # Very short text that is decorative is 0
    if len(text.split()) < 10 and matches:
        return 0.0

    return score

class ExergyGuard:
    """Ω₂: The Thermodynamic Guard. Filters low-exergy (decorative) content."""

    def check_thermodynamic_yield(
        self,
        content: str,
        project_id: str,
        fact_type: str = "AXIOM",
        taint: str | None = None
    ) -> float:
        """Enforces exergy limits on AXIOM/PROPOSAL facts."""
        # Non-text or structured types bypass exergy checks (assumed high utility)
        if fact_type in ("code", "structure", "archive") and taint != "MOLTBOOK_WILD":
            return 1.0

        score = calculate_exergy(content)

        threshold = 0.8 if taint == "MOLTBOOK_WILD" else 0.5

        if score < threshold:
            logger.warning("Ω₂ Violation: Low exergy content detected (%.2f) [Taint: %s]", score, taint)
            raise ValueError(
                f"Thermodynamic Violation: Ingestion of low-exergy decorative content rejected (Score: {score:.2f}). "
                "CORTEX requires high exergy/utility density."
            )

        return score

    async def calculate_proposal_exergy(self, proposal: dict) -> float:
        """Calculates unified exergy for a memory proposal (Ω₉)."""
        facts = proposal.get("facts", [])
        if not facts:
            return 0.0

        # Calculate mean exergy over all facts
        total_score = 0.0
        count = 0
        for fact in facts:
            if isinstance(fact, str):
                total_score += calculate_exergy(fact)
                count += 1
            elif isinstance(fact, dict) and "content" in fact:
                total_score += calculate_exergy(str(fact["content"]))
                count += 1

        return total_score / count if count > 0 else 1.0
