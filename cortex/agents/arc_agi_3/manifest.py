from cortex.agents.manifest import AgentManifest


def get_arc_manifest() -> AgentManifest:
    """Returns the sovereign manifest for the ARC-AGI-3 Agent."""
    return AgentManifest(
        agent_id="arc_agi_3",
        purpose="Sovereign CORTEX Agent for ARC-AGI-3 benchmark evaluation.",
        tools_allowed=[],
        max_consecutive_errors=5,
    )
