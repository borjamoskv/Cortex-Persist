import asyncio
import os
from dotenv import load_dotenv

from cortex.agents.arc_agi_agent import CortexArcAgent
from arc_agi import Arcade

def run_arc_agent():
    # Make sure we load the arc api key from the `.env` if we have it
    load_dotenv(dotenv_path=".env")

    # The actual implementation sets arc_env via Swarm, but we can do a minimal test
    arc_api_key = os.getenv("ARC_API_KEY", "")
    if not arc_api_key:
        print("Warning: ARC_API_KEY not found in environment.")
    
    # 1. Init environment wrapper
    arc = Arcade()
    scorecard_id = arc.open_scorecard(tags=["test"])
    
    # Just picking a fast test task from ARC if env allows it 
    # Or rely on swarm main loop
    env = arc.make(game_id="ls20", scorecard_id=scorecard_id)


    # 2. Init Sovereign Agent
    agent = CortexArcAgent(
        card_id="test_card_123",
        game_id="ls20", # common task id ? We'll leave it as a placeholder
        agent_name="cortex_arc_test",
        ROOT_URL="https://arcprize.org",
        record=True,
        arc_env=env,
        tags=["cortex-integration-test"]
    )
    
    print(f"CORTEX Agent initialized: {agent.name}")
    print(f"Agent state: {agent.state}")
    
    # Normally we do `agent.main()` here 
    # but we might need a specific game_id to work correctly with their API.
    # Let's just run agent.main()
    print("Running main loop...")
    try:
        agent.main()
        print("Agent loop finished.")
    except Exception as e:
        print(f"Agent threw an exception: {e}")
        
    print(f"Scorecard: levels_completed={agent.levels_completed}")
    print("Done")

if __name__ == "__main__":
    run_arc_agent()
