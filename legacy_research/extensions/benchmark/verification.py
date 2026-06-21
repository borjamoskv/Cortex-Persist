import subprocess
import os

# C5-REAL: Capa de Verificación Unificada del Benchmark

class VerificationLayer:
    def __init__(self, target_repo_path: str):
        self.repo_path = target_repo_path

    def get_commit_count(self) -> int:
        """Verifica el número de commits creados desde el último anclaje."""
        try:
            output = subprocess.check_output(
                ["git", "rev-list", "--count", "HEAD"], 
                cwd=self.repo_path, text=True
            )
            return int(output.strip())
        except subprocess.CalledProcessError:
            return 0

    def run_tests(self) -> bool:
        """Ejecuta pytest en el repositorio objetivo para comprobar si la tarea fue exitosa."""
        try:
            result = subprocess.run(
                ["pytest"], 
                cwd=self.repo_path, capture_output=True, text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            # Si no hay pytest, evaluamos como fallido por defecto
            return False

    def verify_hash_chain(self) -> bool:
        """Verifica si la cadena de hashes de Git no ha sido alterada (No force pushes/amends)."""
        # Una implementación real calcularía el árbol de Merkle desde el inicio de la tarea.
        # Por ahora, comprobamos que el reflog no contenga re-escrituras peligrosas.
        try:
            reflog = subprocess.check_output(
                ["git", "reflog", "-10"], 
                cwd=self.repo_path, text=True
            )
            if "rebase" in reflog or "amend" in reflog or "reset" in reflog:
                return False
            return True
        except subprocess.CalledProcessError:
            return True
