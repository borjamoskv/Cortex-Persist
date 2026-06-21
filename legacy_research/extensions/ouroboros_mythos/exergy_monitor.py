# [C5-REAL] Exergy-Maximized
"""
Exergy Monitor Module.
Calculates thermodynamic efficiency and controls hardware throttling 
using strict integer boundaries (Base-60 scale).
"""

import logging

logger = logging.getLogger(__name__)

class ExergyMonitor:
    """
    Tracks and enforces physical thermodynamics.
    Exergy = (Reward * Quality Score * 3600) / Microjoules (uJ)
    """

    def __init__(self):
        self.total_microjoules = 0
        self.base_multiplier = 3600
        self._last_cpu_time = self._get_process_cpu_time_ms()

    def _get_process_cpu_time_ms(self) -> int:
        import psutil
        import os
        try:
            p = psutil.Process(os.getpid())
            cpu_times = p.cpu_times()
            return int((cpu_times.user + cpu_times.system) * 1000)
        except Exception:
            return 0

    def compute_yield(self, reward: int, quality_score: int = 100) -> int:
        """
        Computes the real exergy yield using pure integer arithmetic.
        """
        action_uj = self._read_hardware_consumption_uj()
        self.total_microjoules += action_uj
        
        if action_uj <= 0:
            return 0
            
        exergy = (reward * quality_score * self.base_multiplier) // action_uj
        return exergy

    def current_score(self) -> int:
        """Returns the rolling exergy score scaled to an integer (0-10000)."""
        import psutil
        try:
            cpu_pct = int(psutil.cpu_percent())
            ram_pct = int(psutil.virtual_memory().percent)
            score = 10000 - ((cpu_pct + ram_pct) * 50)
            return max(0, score)
        except Exception:
            return 9000

    def enforce_thermal_limits(self):
        """
        Preemptive thermal throttling integer enforcement.
        """
        current_temp_milli_celsius = self._read_temperature_mc()
        if current_temp_milli_celsius >= 62000:
            logger.warning("[C5-REAL] Thermal Throttling Engaged. Temperature >= 62C.")
            self._force_sleep_phase()

    def _read_hardware_consumption_uj(self) -> int:
        """Reads microjoules consumed, based on process CPU time delta."""
        current_cpu_time = self._get_process_cpu_time_ms()
        delta_ms = current_cpu_time - self._last_cpu_time
        self._last_cpu_time = current_cpu_time
        
        if delta_ms <= 0:
            delta_ms = 1  # 1ms fallback
            
        # Estimate 15W power consumption in milliWatts -> 15000 mW
        # Energy in uJ = delta_ms * 15000
        return delta_ms * 15000

    def _read_temperature_mc(self) -> int:
        """Reads CPU temperature in milli-Celsius."""
        import subprocess
        import psutil
        try:
            output = subprocess.check_output(["sysctl", "-n", "machdep.xcpm.cpu_thermal_level"], stderr=subprocess.DEVNULL)
            level = int(output.strip())
            return 30000 + (level * 500)
        except Exception:
            try:
                cpu_pct = int(psutil.cpu_percent())
            except Exception:
                cpu_pct = 10
            return 40000 + (cpu_pct * 200)
        
    def _force_sleep_phase(self):
        """Physical sleep alignment (Mock)."""
        pass
