"""
Cortex-Persist :: Adaptive FPU PID Controller (Cerebellum Node)
C5-REAL Execution Kernel.
"""

import asyncio
import logging
import math
import time
from typing import TypedDict

logger = logging.getLogger(__name__)

class ErrorSignal(TypedDict):
    target: float
    actual: float
    timestamp: float

class PIDState(TypedDict):
    integral: float
    previous_error: float
    kp: float
    ki: float
    kd: float

class AdaptiveFPUPID:
    """
    Cerebellum C5-REAL implementation.
    Isomorphism mapping from Neo4j node 'cerebelo':
    - function: motor_prediction_and_error_correction
    - compute: adaptive_fpu_pid
    - latency_ms: 5
    """
    def __init__(self, base_kp: float = 1.0, base_ki: float = 0.1, base_kd: float = 0.05) -> None:
        self.state: PIDState = {
            "integral": 0.0,
            "previous_error": 0.0,
            "kp": base_kp,
            "ki": base_ki,
            "kd": base_kd
        }
        self.target_latency_ms: float = 5.0
        logger.info("[C5-REAL] Cerebellum Adaptive FPU PID initialized.")

    def compute_motor_plan(self, signal: ErrorSignal) -> tuple[float, float]:
        """
        Executes Error Correction and Timing Signal.
        Must resolve in under target_latency_ms to comply with L1 Layer constraints.
        Returns: (correction_value, timing_gate_ms)
        """
        dt = max(time.time() - signal["timestamp"], 0.001)
        
        error = signal["target"] - signal["actual"]
        self.state["integral"] += error * dt
        derivative = (error - self.state["previous_error"]) / dt

        # Adaptive tuning based on error magnitude (Thermodynamic adjustment)
        if abs(error) > 10.0:
            self.state["kp"] *= 1.05  # Escalate response
        else:
            self.state["kp"] *= 0.99  # Relax response

        correction = (self.state["kp"] * error) + \
                     (self.state["ki"] * self.state["integral"]) + \
                     (self.state["kd"] * derivative)

        self.state["previous_error"] = error
        
        # Timing signal for Basal Ganglia gating
        timing_gate_ms = math.exp(-abs(error)) * self.target_latency_ms

        return float(correction), float(timing_gate_ms)

    def predict_forward_state(self, current_state: float, motor_command: float) -> float:
        """
        Forward Model (Smith Predictor Isomorphism).
        Predicts sensory consequence of a motor command before physical execution.
        Prevents L1 oscillation.
        """
        predicted_delta = motor_command * 0.85  # Damping factor
        return float(current_state + predicted_delta)

    async def run_autonomous_daemon(self, inbox: asyncio.Queue, outbox: asyncio.Queue) -> None:
        """
        Closed-loop autonomous execution (C5-REAL Daemon).
        Pulls sensory predictions and pushes motor corrections strictly independent 
        from the main event loop, acting as a sovereign physical actor.
        Complies with Rule Ω9 (Deterministic Ignition).
        """
        logger.info("[C5-REAL] Cerebellum Daemon ignited. Awaiting synchronization.")
        while True:
            try:
                signal: ErrorSignal = await inbox.get()
                correction, gate_ms = self.compute_motor_plan(signal)
                
                # Emit correction downstream autonomously
                await outbox.put({"correction": correction, "gate_ms": gate_ms})
                inbox.task_done()
                
            except asyncio.CancelledError:
                logger.info("[C5-REAL] Cerebellum Daemon terminated via apoptosis.")
                break
            except Exception as e: # noqa: BLE001
                # Constraint LL-AC-03: Fault containment inside background worker.
                logger.error(f"[C5-REAL] L1 Oscillation collapse in cerebellum daemon: {e}")
                await asyncio.sleep(0.001)  # Thermodynamic debounce
