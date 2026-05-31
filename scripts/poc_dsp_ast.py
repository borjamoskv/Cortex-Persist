import math
import hashlib
import json

# 21-EDO constants
ROOT_FREQ = 440.0  # Base frequency (A4)
EDO = 21
STEP_RATIO = 2 ** (1 / EDO)

# Map EDO-21 pitch classes (0-20) to AST components
AST_MAP = {
    0: "Module",
    1: "FunctionDef",
    2: "arguments",
    3: "arg",
    4: "Return",
    5: "Name",
    6: "Load",
    7: "Store",
    8: "Constant",
    9: "BinOp",
    10: "Add",
    11: "Sub",
    12: "Mult",
    13: "Div",
    14: "Assign",
    15: "Compare",
    16: "Gt",
    17: "Lt",
    18: "If",
    19: "Call",
    20: "Param",
}


def freq_to_pitch_class(freq: float) -> int:
    # Calculate steps from base frequency
    steps = round(EDO * math.log2(freq / ROOT_FREQ))
    return steps % EDO


def compile_frequencies_to_syntax_tree(freq_seq: list[float]) -> str:
    # Convert frequency sequence to a string of AST operations
    ops = [AST_MAP[freq_to_pitch_class(f)] for f in freq_seq]
    return " -> ".join(ops)


# Example sequence simulating a 21-EDO melody:
# 440.0 (Root), 454.8 (Step 1), 470.1 (Step 2), 522.2 (Step 5)
melody = [440.0, 454.8, 470.1, 522.2, 591.2]
ast_program = compile_frequencies_to_syntax_tree(melody)
seal = hashlib.sha256(ast_program.encode()).hexdigest()

print(
    json.dumps(
        {
            "status": "C5-REAL",
            "freq_sequence_hz": melody,
            "edo_21_pitch_classes": [freq_to_pitch_class(f) for f in melody],
            "mapped_ast_topology": ast_program,
            "sha256_cryptographic_seal": seal,
        },
        indent=2,
    )
)
