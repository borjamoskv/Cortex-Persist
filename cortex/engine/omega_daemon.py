"""
C5-REAL OmegaDaemon — Macro-organismo que reside en memoria y evalúa termodinámica del sistema.
Claim: Zero-Prompt Operation mediante ExergyGuard + EntropySensor.
"""
import asyncio
import os
import re
import resource
import subprocess
import time
from typing import Optional

# ==================== ExergyGuard ====================
class ExergyGuard:
    """Monitorea exergía del sistema (RAM libre + CPU load)."""
    
    def __init__(self, ram_threshold_mb: float = 200.0):
        self.ram_threshold_mb = ram_threshold_mb
    
    def check_ram_free_mb(self) -> float:
        """RAM libre en MB (macOS vm_stat)."""
        try:
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            pages_free = 0
            for line in result.stdout.splitlines():
                if "Pages free" in line:
                    pages_free = int(line.split(":")[1].strip().rstrip("."))
                    break
            return pages_free * 16384 / (1024 * 1024)  # MB
        except Exception:
            return 0.0
    
    def get_ram_pressure(self) -> str:
        """RAM pressure de macOS (memory_pressure)."""
        try:
            result = subprocess.run(
                ["memory_pressure"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "RAM pressure" in line:
                    return line.split(":")[1].strip()
            return "unknown"
        except Exception:
            return "unknown"
    
    def check(self) -> dict:
        """Ciclo de exergía: RAM libre + presión."""
        ram_free = self.check_ram_free_mb()
        pressure = self.get_ram_pressure()
        
        critical = ram_free < self.ram_threshold_mb
        return {
            "ram_free_mb": ram_free,
            "ram_pressure": pressure,
            "critical": critical,
            "exergy": 1.0 if not critical else 0.0,
        }
    
    def reclaim(self) -> tuple[float, str]:
        """Reclaim RAM con purge (macOS)."""
        try:
            before = self.check_ram_free_mb()
            subprocess.run(["purge"], capture_output=True, timeout=10)
            after = self.check_ram_free_mb()
            reclaimed = after - before
            return reclaimed, "OK"
        except Exception as e:
            return 0.0, f"ERR: {e}"

# ==================== EntropySensor ====================
class EntropySensor:
    """Sensa entropía del sistema (CPU load + swap)."""
    
    def check_cpu_load(self) -> float:
        """CPU load promedio (top -l 1)."""
        try:
            result = subprocess.run(
                ["top", "-l", "1", "-o", "cpu"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "CPU usage" in line:
                    # Extrae % user + sys
                    match = re.search(r"([\d.]+)%\s*user.*([\d.]+)%\s*sys", line)
                    if match:
                        return (float(match.group(1)) + float(match.group(2))) / 100.0
            return 0.0
        except Exception:
            return 0.0
    
    def check_swap_mb(self) -> float:
        """Swap usado en MB (sysctl vm.swapusage)."""
        try:
            result = subprocess.run(
                ["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "used" in line:
                    match = re.search(r"([\d.]+)\s*M", line)
                    if match:
                        return float(match.group(1))
            return 0.0
        except Exception:
            return 0.0
    
    def sense(self) -> dict:
        """Sensado de entropía: CPU + swap."""
        cpu = self.check_cpu_load()
        swap = self.check_swap_mb()
        return {
            "cpu_load": cpu,
            "swap_mb": swap,
            "entropy": cpu * 0.6 + swap / 1000.0 * 0.4,  # Normalizada
        }

# ==================== OmegaDaemon ====================
class OmegaDaemon:
    """OmegaDaemon — Macro-organismo termodinámico en memoria."""
    
    def __init__(self, exergy_threshold: float = 0.5, reclaim_on_critical: bool = True):
        self.exergy = ExergyGuard(ram_threshold_mb=200.0)
        self.entropy = EntropySensor()
        self.running = False
        self.exergy_threshold = exergy_threshold
        self.reclaim_on_critical = reclaim_on_critical
        self.loop_count = 0
    
    async def start(self, interval_s: float = 5.0):
        """OmegaDaemon ciclo continuo."""
        self.running = True
        print("[C5-REAL] OmegaDaemon started — Zero-Prompt Operation active")
        print("  ExergyGuard: RAM threshold 200 MB")
        print("  EntropySensor: CPU + swap monitoring")
        
        while self.running:
            self.loop_count += 1
            ex = self.exergy.check()
            ent = self.entropy.sense()
            
            print(f"\n[OmegaLoop {self.loop_count}]")
            print(f"  Exergy: {ex['exergy']:.2f} (RAM: {ex['ram_free_mb']:.1f} MB, critical: {ex['critical']})")
            print(f"  Entropy: {ent['entropy']:.3f} (CPU: {ent['cpu_load']:.2f}, swap: {ent['swap_mb']:.1f} MB)")
            
            if ex['critical'] and self.reclaim_on_critical:
                reclaimed, status = self.exergy.reclaim()
                print(f"  ⚠️  RAM CRÍTICA — reclaim: {reclaimed:.1f} MB ({status})")
            
            if ex['exergy'] < self.exergy_threshold:
                print(f"  ⚠️  Exergy baja ({ex['exergy']:.2f}) — recomendación: reducir carga agéntica")
            
            await asyncio.sleep(interval_s)
    
    def stop(self):
        """OmegaDaemon stop."""
        self.running = False
        print("\n[C5-REAL] OmegaDaemon stopped")

# ==================== main ====================
if __name__ == "__main__":
    daemon = OmegaDaemon()
    try:
        asyncio.run(daemon.start(interval_s=5.0))
    except KeyboardInterrupt:
        daemon.stop()
