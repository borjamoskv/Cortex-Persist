import time
from cortex.engine.pearl import PearlEngine

def benchmark():
    engine = PearlEngine()
    
    # 30x30 grid with some objects
    grid = [[0] * 30 for _ in range(30)]
    for i in range(5, 15):
        for j in range(5, 15):
            grid[i][j] = 1
    for i in range(20, 25):
        for j in range(20, 25):
            grid[i][j] = 2
            
    print(f"Engine Primitives: {list(engine.primitives.keys())}")
    
    # Warmup
    engine.primitives["get_objects"](grid)
    
    start = time.perf_counter()
    iterations = 1000
    for _ in range(iterations):
        engine.primitives["get_objects"](grid)
    end = time.perf_counter()
    
    avg_ms = (end - start) / iterations * 1000
    print(f"Average 'get_objects' (30x30): {avg_ms:.4f} ms")
    
    # Check if we are using Rust
    import sys
    if "cortex_rust" in sys.modules:
        print("STATUS: RUST CORE ACTIVE (AX-051)")
    else:
        print("STATUS: PYTHON FALLBACK (ENTROPIC)")

if __name__ == "__main__":
    benchmark()
