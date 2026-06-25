import asyncio
import sys
import traceback
from unittest.mock import AsyncMock, patch

import pytest

from cortex.engine.autopoiesis import AutopoiesisEngine

class CrashingComponent:
    def buggy_method(self):
        return 1 / 0  # ZeroDivisionError

@pytest.mark.asyncio
async def test_ouroboros_llm_linkage():
    engine = AutopoiesisEngine(observation_window_ms=10)
    
    # Mock the LLMProvider to return a deterministic patch
    mock_patch_code = '''
class CrashingComponent:
    def buggy_method(self):
        return 42
'''
    engine.llm.complete = AsyncMock(return_value=f"```python\n{mock_patch_code}\n```")
    
    # Mock ASTHealer to avoid actual sandbox execution side-effects during this unit test
    # (Though C5 Sandbox isolates it, we just want to test the LLM extraction pipeline here)
    from unittest.mock import MagicMock
    engine.healer.heal_exception = MagicMock()
    
    # Trigger exception manually
    try:
        obj = CrashingComponent()
        obj.buggy_method()
    except ZeroDivisionError as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        target_str = "tests.engine.autopoiesis.test_ouroboros_l7.CrashingComponent"
        
        await engine.mutate(target=target_str, exc_info=exc_value, traceback_str=tb_str)
        
    # Verify the LLM was called with the source code and the traceback
    engine.llm.complete.assert_called_once()
    call_kwargs = engine.llm.complete.call_args.kwargs
    assert "return 1 / 0" in call_kwargs["prompt"], "Source code should be in prompt"
    assert "ZeroDivisionError" in call_kwargs["prompt"], "Exception should be in prompt"
    
    # Verify ASTHealer was called with the extracted patch code
    engine.healer.heal_exception.assert_called_once()
    heal_args = engine.healer.heal_exception.call_args[0]
    assert heal_args[0] == target_str
    assert "return 42" in heal_args[1]
