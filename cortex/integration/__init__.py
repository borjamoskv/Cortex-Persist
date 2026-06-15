from .telemetry import AgentTelemetryEmitter, compute_agent_fingerprint
from .morph_registry import MorphRegistry, MorphSnapshot
from .divergence_audit import DivergenceAuditor, DivergenceReport
from .jit_bridge import JITBridgeCompiler, BridgeArtifact
from .verifier import IntegrationVerifier

__version__ = "0.1.0-c5-real"
