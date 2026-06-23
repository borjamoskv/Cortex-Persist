# [C5-REAL] Exergy-Maximized
import logging
import time
from collections.abc import Callable
from typing import Any

import jax
import jax.numpy as jnp

from babylon60.engine.goat_calculus import (
    compute_derivative,
    compute_limit,
    definite_integral,
    rate_of_change,
)
from babylon60.engine.legion import AsyncSignalBus, SwarmAgent, SwarmSignal

logger = logging.getLogger("babylon60.primitive_exergy_agent")


class PrimitiveExergyMaximizerAgent:
    """
    Agente C5-REAL: Maximiza la exergía de los cálculos matemáticos (Primitivas).
    Desvía la evaluación de primitivas algebraicas o de cálculo de la inferencia LLM
    (alta entropía) a implementaciones deterministas JAX/PyTorch (alta exergía).
    """

    name = "primitive_exergy_omega"

    async def evaluate_primitive(self, primitive_type: str, f: Callable[[Any], Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Evaluates a mathematical primitive using deterministic JAX compute.
        Returns the C5-REAL structural output including exergy metrics.
        """
        logger.info("⚡ [PRIMITIVE-EXERGY] Forzando colapso determinista para: %s", primitive_type)
        
        start_time = time.perf_counter()
        result: Any = None
        
        try:
            if primitive_type == "limit":
                left_lim, right_lim = compute_limit(f, *args, **kwargs)
                result = {"left_limit": float(left_lim), "right_limit": float(right_lim)}
            elif primitive_type == "derivative":
                # Devuelve un callable derivado, lo evaluamos si se pasan args
                df = compute_derivative(f)
                if args:
                    result = float(df(args[0]))
                else:
                    result = "[Compiled Derivative Function]"
            elif primitive_type == "rate_of_change":
                result = rate_of_change(f, *args, **kwargs)
            elif primitive_type == "definite_integral":
                result = float(definite_integral(f, *args, **kwargs))
            else:
                raise ValueError(f"Primitiva no soportada: {primitive_type}")

            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Cálculo de Exergía: Estimación del costo LLM vs costo de ejecución determinista
            llm_estimated_latency_ms = 1200.0
            exergy_saved_ms = llm_estimated_latency_ms - execution_time_ms
            
            return {
                "Claim": result,
                "Proof": {
                    "Base": f"JAX_AOT_{primitive_type.upper()}",
                    "ExecutionTimeMs": round(execution_time_ms, 4),
                    "ExergySavedMs": round(exergy_saved_ms, 4),
                    "Confidence": "C5-REAL"
                }
            }

        except Exception as e:
            logger.error("[PRIMITIVE-EXERGY] Fallo en la evaluación JAX: %s", str(e))
            return {
                "Claim": "APOPTOSIS",
                "Proof": {
                    "Base": "EXECUTION_FAILURE",
                    "Error": str(e),
                    "Confidence": "C4-SIM"
                }
            }


class PrimitiveExergyAgentAdapter(SwarmAgent):
    """
    Wraps the PrimitiveExergyMaximizerAgent for the Swarm ecosystem.
    """

    def __init__(self, agent_id: str, bus: AsyncSignalBus, engine: Any = None):
        super().__init__(agent_id, bus)
        self.engine = engine
        self.maximizer = PrimitiveExergyMaximizerAgent()

    async def on_signal(self, signal: SwarmSignal) -> None:
        if signal.type == "EVALUATE_PRIMITIVE":
            primitive_type = signal.payload.get("primitive_type")
            # f should be passed in payload or registered
            f_expr = signal.payload.get("function_expression") 
            args = signal.payload.get("args", [])
            
            if not f_expr or not primitive_type:
                logger.warning("[%s] Señal inválida. Falta primitive_type o function_expression.", self.agent_id)
                return
                
            # Por simplicidad en el adapter, simulamos la construcción de la función JAX.
            # En un entorno de producción, la función `f` debería estar pre-compilada o validada.
            def _compile_jax_func(expr: str) -> Callable[[Any], Any]:
                # Nota: eval() es inseguro en red pública. Se asume entorno C5-REAL seguro o AST parsing.
                # Aquí inyectamos jnp en los globals de eval.
                def f(x: Any) -> Any:
                    return eval(expr, {"jnp": jnp, "jax": jax}, {"x": x})
                return f
                
            try:
                f_compiled = _compile_jax_func(f_expr)
                result = await self.maximizer.evaluate_primitive(primitive_type, f_compiled, *args)
                
                # Emitir resultado de vuelta al enjambre
                await self.emit("PRIMITIVE_EVALUATED", {
                    "target": signal.source,
                    "result": result
                })
            except Exception as e:
                logger.error("[%s] Error compilando o evaluando primitiva: %s", self.agent_id, str(e))
