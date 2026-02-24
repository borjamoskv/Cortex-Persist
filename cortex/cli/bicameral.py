"""
CORTEX V4 Bicameral Console (Subconscious Interface)

This module provides the visual separation of the Sovereign Agent's internal monologue into three distinct streams:
1. Limbic (Subconscious/Emotional): Magenta, for lore and nemesis evaluations.
2. Motor (Execution): Cyan/Green, for fast, direct actions.
3. Autonomic (Tether/Safety): Red, for hard limits and dead-man switches.
"""

from rich.console import Console
from rich.theme import Theme

# Industrial Noir 2026 Theme
bicameral_theme = Theme({
    "limbic": "dim magenta",     # Reflejando memoria, intuición, cicatrices
    "motor": "bold cyan",        # Ejecución pura, frío, metálico
    "autonomic": "bold red",     # Peligro, límites, tether
    "limbic_prefix": "magenta",
    "motor_prefix": "cyan",
    "autonomic_prefix": "red",
})

console = Console(theme=bicameral_theme)

class BicameralConsole:
    """The Subconscious Interface separating agent internal monologue."""
    
    @staticmethod
    def log_limbic(message: str, source: str = "LORE") -> None:
        """Logs emotional, historical, or allergy-driven reasoning."""
        prefix = f"[limbic_prefix][▶ CORTEX Límbico | {source.upper():<7}][/limbic_prefix]"
        console.print(f"{prefix} [limbic]{message}[/limbic]")
        
    @staticmethod
    def log_motor(message: str, action: str = "EXEC") -> None:
        """Logs fast execution and physical interaction."""
        prefix = f"[motor_prefix][▶ CORTEX Motor   | {action.upper():<7}][/motor_prefix]"
        console.print(f"{prefix} [motor]{message}[/motor]")
        
    @staticmethod
    def log_autonomic(message: str, check: str = "TETHER") -> None:
        """Logs hard boundaries, resource checks, and autolysis."""
        prefix = f"[autonomic_prefix][⚠ CORTEX T.C.A   | {check.upper():<7}][/autonomic_prefix]"
        console.print(f"{prefix} [autonomic]{message}[/autonomic]")

bicameral = BicameralConsole()
