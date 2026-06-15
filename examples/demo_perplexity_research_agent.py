import asyncio
import os
import sys

from cortex.engine.swarm import SwarmOrchestrator
from cortex.agents.perplexity import PerplexityResearchAgent

async def main():
    print("🚀 Initializing Cortex Swarm Orchestrator...")
    orchestrator = SwarmOrchestrator()
    
    print("🧠 Bootstrapping PerplexityResearchAgent...")
    research_agent = PerplexityResearchAgent(
        model="sonar-pro",
        temperature=0.1
    )
    
    orchestrator.register_agent("researcher", research_agent)
    
    query = "State of the art in Vector Symbolic Architectures for LLMs 2026"
    print(f"\n📡 Dispatching Query: '{query}'")
    
    response = await orchestrator.dispatch(
        target="researcher",
        instruction=query
    )
    
    print("\n✅ Research Synthesis:")
    print("="*40)
    print(response.content)
    print("="*40)

if __name__ == "__main__":
    if not os.environ.get("PERPLEXITY_API_KEY"):
        print("❌ Error: PERPLEXITY_API_KEY environment variable is required.")
        sys.exit(1)
    asyncio.run(main())
