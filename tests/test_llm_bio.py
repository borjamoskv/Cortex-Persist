import asyncio
from cortex.llm.router import CortexPrompt
from cortex.llm.provider import LLMProvider
from cortex.sovereign.endocrine import DigitalEndocrine

async def test_llm_modulation():
    # Setup
    provider = LLMProvider(provider="custom", base_url="http://localhost:8080/v1", api_key="test")
    endocrine = DigitalEndocrine()
    
    # 1. Stress Mode (Cortisol High)
    endocrine.cortisol = 0.9
    prompt_stress = CortexPrompt(
        system_instruction="You are a system monitor.",
        working_memory=[{"role": "user", "content": "Status?"}],
        biological_context=endocrine.snapshot()
    )
    
    # Mocking _sanitize_messages to see what would be sent
    messages_stress = prompt_stress.to_openai_messages()
    temp_stress = endocrine.temperature
    style_stress = endocrine.response_style
    
    print(f"Stress Temperature: {temp_stress}")
    print(f"Stress Style: {style_stress}")
    
    # Verify manual injection logic (which match Provider.invoke)
    for msg in messages_stress:
        if msg["role"] == "system":
            msg["content"] += f"\n\n[STYLISTIC HINT: {style_stress}]"
            break
            
    assert temp_stress < 0.3
    assert "telegraphic" in messages_stress[0]["content"]
    
    # 2. Creative Mode (Dopamine High)
    endocrine.cortisol = 0.0
    endocrine.dopamine = 0.9
    prompt_creative = CortexPrompt(
        system_instruction="You are a system monitor.",
        biological_context=endocrine.snapshot()
    )
    
    temp_creative = endocrine.temperature
    style_creative = endocrine.response_style
    
    print(f"Creative Temperature: {temp_creative}")
    print(f"Creative Style: {style_creative}")
    
    assert temp_creative > 0.7
    assert "expansive" in style_creative

    print("✅ LLM Provider modulation logic verified.")

if __name__ == "__main__":
    asyncio.run(test_llm_modulation())
