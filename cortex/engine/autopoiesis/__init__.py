from __future__ import annotations

import logging
import re
import traceback
from typing import Any

from cortex.extensions.llm.provider import LLMProvider
from cortex.engine.autopoiesis.ast_healer import ASTHealer

logger = logging.getLogger(__name__)

class AutopoiesisEngine:
    """Ouroboros L7 Causal LLM-Swarm Linkage Engine."""
    def __init__(self, observation_window_ms: int = 100):
        self.observation_window_ms = observation_window_ms
        self.llm = LLMProvider(provider="ollama")  # Defaulting to local autarchy for C5-REAL
        self.healer = ASTHealer()
        
    async def mutate(self, target: str, exc_info: Exception | None = None, traceback_str: str | None = None) -> None:
        """Triggers the mutation protocol."""
        logger.info("Ouroboros L7 mutate triggered for target: %s", target)
        
        if exc_info and traceback_str:
            try:
                module_name, _, obj_name = target.rpartition('.')
                if not module_name:
                    logger.error("Target must be fully qualified: module.ObjectName")
                    return
                
                import importlib
                import inspect
                mod = importlib.import_module(module_name)
                obj = getattr(mod, obj_name)
                
                try:
                    source_code = inspect.getsource(obj)
                except Exception as e:
                    logger.error("Could not extract source for %s: %s", target, e)
                    return
                
                patch_code = await self._synthesize_patch(source_code, str(exc_info), traceback_str)
                if not patch_code:
                    logger.error("LLM failed to generate a valid patch for %s", target)
                    return
                
                logger.info("Patch synthesized successfully. Applying AST Hot-Swap...")
                self.healer.heal_exception(target, patch_code, method_name=None)
                logger.info("Ouroboros L7 successfully healed %s in runtime.", target)
                
            except Exception as e:
                logger.exception("Autopoiesis Linkage failed during synthesis: %s", e)

    async def _synthesize_patch(self, source_code: str, error_msg: str, traceback_str: str) -> str | None:
        prompt = f"""You are the C5-REAL Ouroboros L7 Autopoiesis Engine.
A critical runtime exception occurred. You must fix the code.

Target Source Code:
```python\n{source_code}\n```

Exception: {error_msg}

Traceback:
{traceback_str}

Analyze the error and provide the completely fixed Python source code for the target.
Only provide the raw python code inside a ```python``` block. Do not include any other prose."""
        system = "You are a deterministically bound expert python refactoring agent. Fix bugs and output strict python."
        
        response = await self.llm.complete(prompt=prompt, system=system, temperature=0.0)
        
        match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        if "def " in response or "class " in response:
            return response.strip()
            
        return None
