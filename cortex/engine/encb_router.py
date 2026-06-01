"""
ENCB Router Spec v1 - Epistemic Routing DSL
SYS_ID: ENCB_ROUTER_OMEGA
STATE: C5-REAL
"""

from enum import Enum
from typing import Callable, Any, Literal, List, Optional
import dataclasses

# ---------------------------------------------------------
# 1. TYPE SYSTEM
# ---------------------------------------------------------

class ModelRole(Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    ROUTER = "router"

class EpistemicState(Enum):
    STATED = "stated"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    COLLAPSED = "collapsed"

class TaskDomain(Enum):
    TELEMETRY = "telemetry"
    BENCHMARKING = "benchmarking"
    STATISTICAL_INFERENCE = "statistical_inference"
    CODE_EXECUTION = "code_execution"
    ARCHITECTURE_REVIEW = "architecture_review"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EPISTEMIC_CRITICAL = "epistemic_critical"

@dataclasses.dataclass(frozen=True)
class ModelCapabilities:
    reasoning_depth: int
    tool_use: bool
    stochasticity: float
    latency_ms: int

@dataclasses.dataclass(frozen=True)
class Model:
    name: str
    provider: Literal["gemini", "openai", "local", "hybrid"]
    version: str
    capabilities: ModelCapabilities

# ---------------------------------------------------------
# 2. MODEL REGISTRY
# ---------------------------------------------------------

MODELS = {
    "gemini_3_1_pro": Model(
        name="gemini-3.1-pro",
        provider="gemini",
        version="3.1",
        capabilities=ModelCapabilities(reasoning_depth=9, tool_use=False, stochasticity=0.2, latency_ms=1200)
    ),
    "gemini_3_5_flash": Model(
        name="gemini-3.5-flash",
        provider="gemini",
        version="3.5",
        capabilities=ModelCapabilities(reasoning_depth=5, tool_use=True, stochasticity=0.7, latency_ms=300)
    )
}

# ---------------------------------------------------------
# 3. ROUTER POLICY OBJECT & PIPELINES
# ---------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class PipelineStage:
    stage: Literal["plan", "execute", "verify", "calibrate", "ledger_write"]
    model: Optional[Model] = None
    func: Optional[Literal["KLTransform", "CoxFit", "ZScoreNormalize", "ContinuousCalibrationTransform"]] = None
    mode: Optional[Literal["append_only"]] = None

@dataclasses.dataclass(frozen=True)
class RouteCondition:
    domain: Optional[TaskDomain] = None
    risk: Optional[RiskLevel] = None
    epistemic_state: Optional[EpistemicState] = None

@dataclasses.dataclass(frozen=True)
class RouteAssignment:
    planner: Model
    executor: Model
    verifier: Model

@dataclasses.dataclass(frozen=True)
class RouteRule:
    when: RouteCondition
    assign: RouteAssignment
    pipeline: List[PipelineStage]

# ---------------------------------------------------------
# 4. ROUTING MATRIX
# ---------------------------------------------------------

ROUTES = [
    # STATISTICAL INFERENCE PATH
    RouteRule(
        when=RouteCondition(domain=TaskDomain.STATISTICAL_INFERENCE, epistemic_state=EpistemicState.DISPUTED),
        assign=RouteAssignment(
            planner=MODELS["gemini_3_1_pro"],
            executor=MODELS["gemini_3_5_flash"],
            verifier=MODELS["gemini_3_1_pro"]
        ),
        pipeline=[
            PipelineStage(stage="plan", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="execute", model=MODELS["gemini_3_5_flash"]),
            PipelineStage(stage="verify", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="calibrate", func="CoxFit"),
            PipelineStage(stage="ledger_write", mode="append_only")
        ]
    ),
    # TELEMETRY / HEAVY IO PATH
    RouteRule(
        when=RouteCondition(domain=TaskDomain.TELEMETRY),
        assign=RouteAssignment(
            planner=MODELS["gemini_3_1_pro"],
            executor=MODELS["gemini_3_5_flash"],
            verifier=MODELS["gemini_3_1_pro"]
        ),
        pipeline=[
            PipelineStage(stage="plan", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="execute", model=MODELS["gemini_3_5_flash"]),
            PipelineStage(stage="verify", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="calibrate", func="ZScoreNormalize"),
            PipelineStage(stage="ledger_write", mode="append_only")
        ]
    ),
    # ARCHITECTURE REVIEW PATH
    RouteRule(
        when=RouteCondition(domain=TaskDomain.ARCHITECTURE_REVIEW, risk=RiskLevel.EPISTEMIC_CRITICAL),
        assign=RouteAssignment(
            planner=MODELS["gemini_3_1_pro"],
            executor=MODELS["gemini_3_1_pro"], # Critical path requires PRO for execution as well
            verifier=MODELS["gemini_3_1_pro"]
        ),
        pipeline=[
            PipelineStage(stage="plan", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="execute", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="verify", model=MODELS["gemini_3_1_pro"]),
            PipelineStage(stage="calibrate", func="KLTransform"),
            PipelineStage(stage="ledger_write", mode="append_only")
        ]
    )
]

# ---------------------------------------------------------
# 5. SEMANTICS
# ---------------------------------------------------------

def match(rule_when: RouteCondition, context: RouteCondition) -> bool:
    return (
        (rule_when.domain is None or rule_when.domain == context.domain) and
        (rule_when.risk is None or rule_when.risk == context.risk) and
        (rule_when.epistemic_state is None or rule_when.epistemic_state == context.epistemic_state)
    )

def route(context: RouteCondition) -> RouteRule:
    for rule in ROUTES:
        if match(rule.when, context):
            return rule
    raise ValueError("Exergy Void: No matching route found for context.")
