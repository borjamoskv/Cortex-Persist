import re

with open("cortex/engine/causality_pkg/original.py", "r") as f:
    lines = f.readlines()

def get_block(start, end):
    return "".join(lines[start:end])

# Imports: lines 0 to 57 (approximately before CausalGraph)
imports_block = get_block(0, 58)

# graph.py (sync graph): CausalGraph
graph_block = get_block(58, 106)

# async_graph.py: AsyncCausalGraph
async_graph_block = get_block(106, 659)

# oracle.py: AsyncCausalOracle, CausalOracle
oracle_block = get_block(659, len(lines))

print("Creating graph.py")
with open("cortex/engine/causality_pkg/graph.py", "w") as f:
    f.write(imports_block)
    f.write(graph_block)

print("Creating async_graph.py")
with open("cortex/engine/causality_pkg/async_graph.py", "w") as f:
    f.write(imports_block)
    f.write(async_graph_block)

print("Creating oracle.py")
with open("cortex/engine/causality_pkg/oracle.py", "w") as f:
    f.write(imports_block)
    f.write(oracle_block)

print("Creating __init__.py")
with open("cortex/engine/causality_pkg/__init__.py", "w") as f:
    f.write('from .graph import CausalGraph\n')
    f.write('from .async_graph import AsyncCausalGraph\n')
    f.write('from .oracle import CausalOracle, AsyncCausalOracle\n')
    f.write('__all__ = ["CausalGraph", "AsyncCausalGraph", "CausalOracle", "AsyncCausalOracle"]\n')
