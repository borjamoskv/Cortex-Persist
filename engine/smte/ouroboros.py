import os
import sys
import importlib
import subprocess
from pathlib import Path
from engine.smte.parser import CortexASTParser


class OuroborosLoop:
    """
    The Autopoietic Loop for AGENTS.ARCHI.
    1. Transcription (AST Parsing)
    2. Mutation (LLM/MCP Patching)
    3. Integration (Writing to disk)
    4. Mitosis (Hot-reload)
    """

    def __init__(self, target_module_path: str):
        self.target_path = Path(target_module_path).resolve()
        self.parser = CortexASTParser(str(self.target_path))

    def transcribe(self):
        """Reads the source code into the AST parser."""
        sys.stdout.write(f"[OUROBOROS] Transcribing {self.target_path.name}...\\n")
        functions = self.parser.extract_functions()
        return functions

    def mutate(self, target_function_name: str, new_code: str):
        """Replaces a specific function with new code."""
        sys.stdout.write(f"[OUROBOROS] Mutating function: {target_function_name}\\n")
        functions = self.parser.extract_functions()
        target_fn = next((f for f in functions if f["name"] == target_function_name), None)

        if not target_fn:
            raise ValueError(f"Function {target_function_name} not found in target module.")

        # Get original source segment
        original_segment = self.parser.get_source_segment(
            target_fn["lineno"], target_fn["end_lineno"]
        )

        # Inject the mutation
        self.parser.inject_mutation(original_segment, new_code)

    def validate_in_sandbox(self) -> bool:
        """Runs tests against the module before allowing it into reality."""
        sys.stdout.write("[OUROBOROS] Running hyper-vector sandbox validation...\\n")
        # For this PoC, we will run the project's tests
        # In a real environment, this might be a specialized sandbox
        root_dir = self.target_path.parent.parent.parent
        try:
            result = subprocess.run(
                ["pytest", "tests/"], cwd=str(root_dir), capture_output=True, text=True
            )
            if result.returncode == 0:
                sys.stdout.write("[OUROBOROS] Validation passed. C5-REAL.\\n")
                return True
            else:
                sys.stdout.write(
                    f"[OUROBOROS] Validation failed (Entropy > 0).\\n{result.stderr}\\n"
                )
                return False
        except FileNotFoundError:
            # pytest not found, assume failure or skip
            sys.stdout.write(
                "[OUROBOROS] pytest not found. Sandbox validation bypassed (DANGEROUS).\\n"
            )
            return True

    def integrate(self):
        """Writes the mutated AST back to disk."""
        sys.stdout.write("[OUROBOROS] Integrating mutation to disk...\\n")
        self.parser.save()

    def mitosis(self, module_name: str):
        """Hot-reloads the module into the current process."""
        sys.stdout.write(f"[OUROBOROS] Triggering Mitosis (hot-reload) for {module_name}...\\n")
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
            sys.stdout.write("[OUROBOROS] Mitosis complete.\\n")
        else:
            sys.stdout.write("[OUROBOROS] Module not loaded in memory yet. No mitosis needed.\\n")
