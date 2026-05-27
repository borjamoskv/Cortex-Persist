"""
CORTEX JIT Compiled Skill: API-Provider-OMEGA
Description: C5-REAL LLM API Fallback and Routing Skill. Provides deterministic fallback to external APIs when local inference (like qwen3.6-coder) fails or is unavailable.
"""
import json
import logging

class ApiProviderOmegaSkill:
    def __init__(self):
        self.name = "API-Provider-OMEGA"
        self.description = "C5-REAL LLM API Fallback and Routing Skill. Provides deterministic fallback to external APIs when local inference (like qwen3.6-coder) fails or is unavailable."
        self.instructions = "# API-Provider-OMEGA (LLM API Fallback)\n\nThis skill handles the dynamic fallback and bridging for the `CortexLLMRouter` when local models (like Ollama's `qwen3.6-coder:7b`) are not found or fail to load.\n\n## 1. Directives\n- **Zero-Friction Fallback**: If a local model fails to load, immediately reroute to an equivalent API provider.\n- **Provider Parity**: Prioritize frontier models like `qwen3.6-27b` (via DashScope) when local dense models fail.\n- **Ledger Audit**: Record all fallback events in the ledger to track exergy loss due to external API usage.\n- **Thinking Traces**: Enforce `enable_thinking: True` and `preserve_thinking: True` when routing to models that support it (e.g. Qwen3.6-27B) to maintain C5-REAL agentic transparency.\n\n## 2. Supported Providers & Configurations\n\n### Alibaba Cloud Model Studio (DashScope)\n- **Model ID**: `qwen3.6-27b`\n- **Base URL (OpenAI Spec)**: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`\n- **Base URL (Anthropic Spec)**: `https://dashscope-intl.aliyuncs.com/apps/anthropic`\n- **Auth Environment Variable**: `DASHSCOPE_API_KEY`\n- **Specifics**: Requires `extra_body: { \"enable_thinking\": True, \"preserve_thinking\": True }` in OpenAI-compatible payloads for full reasoning trace preservation. Can be seamlessly integrated into `OpenClaw`, `Qwen Code`, and `Claude Code`.\n\n## 3. Usage\nUse this skill when modifying router configurations to ensure robust fallback logic, preventing agent stall when the environment lacks the requested local binary, while adhering to the C5-REAL zero-plaintext hygiene standards for the `DASHSCOPE_API_KEY`.\n"

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        """
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        """
        logging.info(f"[{self.name}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload
        }
