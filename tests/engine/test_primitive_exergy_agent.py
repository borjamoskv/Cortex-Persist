import pytest
import jax.numpy as jnp
from babylon60.engine.primitive_exergy_agent import PrimitiveExergyMaximizerAgent

@pytest.mark.asyncio
async def test_exergy_agent_limit():
    agent = PrimitiveExergyMaximizerAgent()
    
    # Primitiva: Límite de f(x) = x^2 as x->2
    def f(x):
        return x**2
        
    result = await agent.evaluate_primitive("limit", f, 2.0)
    
    # Expected limits ~4.0
    assert "Claim" in result
    assert "Proof" in result
    
    claim = result["Claim"]
    assert pytest.approx(claim["left_limit"], 0.01) == 4.0
    assert pytest.approx(claim["right_limit"], 0.01) == 4.0
    assert result["Proof"]["Base"] == "JAX_AOT_LIMIT"

@pytest.mark.asyncio
async def test_exergy_agent_derivative():
    agent = PrimitiveExergyMaximizerAgent()
    
    # Primitiva: Derivada de f(x) = x^3 evaluated at x=3
    # f'(x) = 3x^2, so f'(3) = 27
    def f(x):
        return x**3
        
    result = await agent.evaluate_primitive("derivative", f, 3.0)
    
    assert "Claim" in result
    assert pytest.approx(result["Claim"], 0.01) == 27.0
    assert result["Proof"]["Base"] == "JAX_AOT_DERIVATIVE"

@pytest.mark.asyncio
async def test_exergy_agent_integral():
    agent = PrimitiveExergyMaximizerAgent()
    
    # Primitiva: Integral of f(x) = x from 0 to 2
    # Result should be (1/2)*x^2 evaluated at 2 = 2.0
    def f(x):
        return x
        
    result = await agent.evaluate_primitive("definite_integral", f, 0.0, 2.0, 100)
    
    assert "Claim" in result
    # Trapezoidal rule with 100 points will be very close to 2.0
    assert pytest.approx(result["Claim"], 0.1) == 2.0
    assert result["Proof"]["Base"] == "JAX_AOT_DEFINITE_INTEGRAL"
