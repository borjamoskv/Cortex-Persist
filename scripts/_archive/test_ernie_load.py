import os

from cortex.extensions.llm.manager import LLMManager


def test_ernie_preset():
    print("Testing ERNIE Preset...")
    os.environ["CORTEX_LLM_PROVIDER"] = "ernie"
    os.environ["AIMLAPI_KEY"] = "dummy_key"

    manager = LLMManager()

    assert manager.available is True
    provider = manager.provider
    print(f"Provider: {provider.provider_name}")
    print(f"Model: {provider.model_name}")
    print(f"Intent Affinity: {provider.intent_affinity}")

    assert provider.model_name == "baidu/ernie-5-0-thinking-latest"
    print("SUCCESS: ERNIE preset loaded correctly.")


if __name__ == "__main__":
    test_ernie_preset()
