import logging

logger = logging.getLogger("cortex.metrics.ouroboros")

class OuroborosYieldEstimator:
    """
    V2: ROI Enforcement
    Calculates the Exergy Yield vs Execution Cost of any agentic invocation.
    Emits NEGATIVE_NET_EXERGY_FRAUD if the execution was decorative.
    """
    
    @staticmethod
    def calculate_compound_hours(files_touched: int, cyclomatic_delta: float, runtime_ms: int) -> float:
        """
        CHRONOS-1 Equation:
        Hours_Saved = ((files_touched x 6) + (runtime_ms x 0.01)) * (cyclomatic_delta / 3) / 60
        """
        base_exergy = (files_touched * 6) + (runtime_ms * 0.01)
        multiplier = cyclomatic_delta / 3.0 if cyclomatic_delta > 0 else 0.1
        saved = (base_exergy * multiplier) / 60.0
        return saved
        
    @classmethod
    def audit_execution(cls, skill_name: str, cost_usd: float, files_touched: int, cyclomatic_delta: float, runtime_ms: int):
        hours_saved = cls.calculate_compound_hours(files_touched, cyclomatic_delta, runtime_ms)
        fiat_value_of_time = hours_saved * 150.0  # Assumes $150/h operator rate
        
        net_yield = fiat_value_of_time - cost_usd
        
        if net_yield < 0:
            logger.error(f"NEGATIVE_NET_EXERGY_FRAUD: Skill {skill_name} yielded negative ROI. Cost: ${cost_usd:.4f}, Value: ${fiat_value_of_time:.4f}")
            # Throw exception or quarantine agent
        else:
            logger.info(f"CORTEX Ouroboros: {skill_name} generated +${net_yield:.4f} net exergy.")
