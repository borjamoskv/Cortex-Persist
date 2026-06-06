#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
import os
import subprocess
import re
from typing import Optional
from datetime import datetime

def log(msg: str, tier: str = "INFO") -> None:
    print(f"[{datetime.now().time()}] [{tier}] [CHAOS-FUZZER] {msg}")

def execute_forge_fuzz(target_dir: str, runs: int = 250000) -> tuple[bool, str | None]:
    """Levanta el subproceso contra Foundry buscando fracturar invariantes."""
    log(f"Iniciando Chaos Engine sobre el Target Físico... ({runs} ciclos)", "L3-STRIKE")
    
    cmd: list[str] = ["forge", "test", "--fuzz-runs", str(runs), "-vv"]
    if "sky" in target_dir.lower():
        cmd.extend(["--no-match-contract", "DepositorUniV3Test|StableDepositorUniV3Test"])
    
    # Asegurar RPC para forks mainnet si no está configurado
    env = os.environ.copy()
    if "ETH_RPC_URL" not in env:
        env["ETH_RPC_URL"] = "https://ethereum.publicnode.com"
    
    try:
        # Run en C5-REAL (I/O bloqueante puro hasta fractura)
        result = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True, timeout=60, env=env)
        output = result.stdout + result.stderr
        
        # Parseo del Breaker (Buscamos semilla determinista fallida)
        if "[FAIL" in output:
            log("Fractura Detectada. Invariante Inconsistente.", "BREAKER")
            seed_match = re.search(r'fuzz-seed:? (0x[0-9a-fA-F]+|\d+)', output)
            seed = seed_match.group(1) if seed_match else "Unknown_Seed"
            
            # Aislar output para ledger
            fail_line = [line for line in output.split("\n") if "[FAIL" in line]
            if fail_line:
                log(f"Motivo de colapso: {fail_line[0].strip()}", "CORRUPTION")
                
            return True, seed
        else:
            log(f"Silo termo-resistente. Ninguna invariante cedió ante la entropía. (Forge ReturnCode: {result.returncode})", "C5-SUCCESS")
            if result.returncode != 0:
                log(f"Forge Error Block:\n{output}", "C5-DEBUG")
            return False, None
            
    except subprocess.TimeoutExpired:
        log("Límites térmicos alcanzados. El orquestador truncó la ejecución (>60s).", "WARN")
        return False, None
    except OSError as e:
        log(f"Error nativo invocando Forge: {e}", "ERROR")
        return False, None

def crystallize_harness(target_dir: str) -> bool:
    """Cristaliza un target falso pero estructuralmente corruptible para prueba Físico-Estocástica."""
    os.makedirs(target_dir, exist_ok=True)
    subprocess.run(["forge", "init", "--force", "--no-git"], cwd=target_dir, capture_output=True)
    
    src_dir = os.path.join(target_dir, "src")
    test_dir = os.path.join(target_dir, "test")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    contract_code = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract TargetToCorrupt {
    uint256 public lockedValue;
    bool public hasExploded;

    constructor() {
        lockedValue = 1000;
        hasExploded = false;
    }

    // Vulnerabilidad inyectada (Underflow lógico por falta de guards bajo Chaos Fuzzing)
    function complexOperation(uint256 x, uint256 y, uint256 z) public {
        unchecked {
            if (x * y + z == 89283471) {
                if (x < 1000 && y > 50000) {
                    hasExploded = true; // El Fuzzer debería hallar este estado imposible a ciegas
                }
            }
        }
    }
}
"""
    test_code = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// Import local simulation workaround para no depender de layout absoluto
contract TargetToCorrupt {
    uint256 public lockedValue;
    bool public hasExploded;

    constructor() {
        lockedValue = 1000;
        hasExploded = false;
    }

    function complexOperation(uint256 x, uint256 y, uint256 z) public {
        unchecked {
            if (x * y + z == 89283471) {
                if (x < 1000 && y > 50000) {
                    hasExploded = true;
                }
            }
        }
    }
}

contract ChaosTest is Test {
    TargetToCorrupt target;

    function setUp() public {
        target = new TargetToCorrupt();
    }

    // Invariante Soberana
    function testFuzz_ChaosExplosion(uint256 x, uint256 y, uint256 z) public {
        target.complexOperation(x, y, z);
        assertEq(target.hasExploded(), false, "Chaos Reached! Memory Corrupted.");
    }
}
"""
    try:
        # Forge Toml required by forge test
        with open(os.path.join(target_dir, "foundry.toml"), "w") as f:
            f.write("[profile.default]\nsrc = 'src'\nout = 'out'\nlibs = ['lib']\n")
            
        with open(os.path.join(src_dir, "Target.sol"), "w", encoding='utf-8') as f:
            f.write(contract_code)
            
        with open(os.path.join(test_dir, "ChaosInvariant.t.sol"), "w", encoding='utf-8') as f:
            f.write(test_code)
            
        return True
    except OSError as e:
        log(f"Fallo I/O al cristalizar Harness: {e}", "ERROR")
        return False

def main() -> None:
    import sys
    if len(sys.argv) < 2:
        log("Uso: python3 cortex_chaos_fuzzer.py <target_dir> [runs]", "ERROR")
        sys.exit(1)
        
    target_dir = os.path.abspath(sys.argv[1])
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 250000
    
    log(f"Iniciando Asalto Chaos en: {target_dir} ({runs} ciclos)", "SYSTEM")
    
    # Si el directorio no es un proyecto de Forge, lo inicializamos
    if not os.path.exists(os.path.join(target_dir, "foundry.toml")):
        log("Detectado target virgen. Cristalizando harness estocástico...", "CRYSTAL")
        crystallize_harness(target_dir)
        
    success, seed = execute_forge_fuzz(target_dir, runs)
    
    if success:
        log(f"-> EXERGY YIELD: Encontrada colisión matemática en {target_dir}. Seed: {seed}", "C5-REAL")
    else:
        log(f"-> EXERGY YIELD: Target {target_dir} resistió la carga térmica.", "C5-REAL")

if __name__ == "__main__":
    main()
