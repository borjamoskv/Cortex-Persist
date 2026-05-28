#!/usr/bin/env python3
"""
∴ CORTEX-FOUNDRY-STRIKE-GENERATOR v1.0
Generates executable Foundry test contracts from Hound findings.
Closes the loop: Hypothesis → STRIKE → C5-REAL Verification.

Pipeline:
  1. Receive HoundFinding (vuln_type, target_code, hypothesis)
  2. Select template + inject context via LocalLLMAdapter
  3. Write .t.sol to ouroboros-sniper/test/generated/
  4. Compile with `forge build`
  5. Execute with `forge test`
  6. Parse result → C5-REAL or iterate

∴ Axioms: Ω₂ (Thermodynamic), Ω₉ (Truth)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Resolve project paths
SCRIPTS_DIR = Path(__file__).resolve().parent
CORTEX_PERSIST = SCRIPTS_DIR.parent
OUROBOROS_DIR = Path(os.environ.get(
    "CORTEX_OUROBOROS_DIR",
    str(CORTEX_PERSIST.parent.parent / "30_CORTEX" / "ouroboros-sniper")
))
TEMPLATES_DIR = SCRIPTS_DIR / "templates"
GENERATED_DIR = OUROBOROS_DIR / "test" / "generated"

# Add autodidact-private to path for LLM adapter
AUTODIDACT_PRIVATE = Path(os.environ.get(
    "AUTODIDACT_PRIVATE_ROOT",
    str(CORTEX_PERSIST.parent.parent / "Downloads" / "WIKIPEDIA BORJA MOSKV" / "CODEX H" / "autodidact-private")
))
if str(AUTODIDACT_PRIVATE) not in sys.path:
    sys.path.insert(0, str(AUTODIDACT_PRIVATE))


C = {
    "B": "\033[38;2;43;59;229m",
    "G": "\033[38;2;0;255;136m",
    "R": "\033[38;2;255;59;48m",
    "D": "\033[38;2;90;90;90m",
    "V": "\033[38;2;102;0;255m",
    "W": "\033[97m",
    "X": "\033[0m",
}

VULN_TEMPLATES = {
    "reentrancy": "reentrancy.t.sol.j2",
    "flashloan": "flashloan.t.sol.j2",
    "flash_loan": "flashloan.t.sol.j2",
    "access_control": "access_control.t.sol.j2",
    "oracle": "oracle_manipulation.t.sol.j2",
    "price_manipulation": "oracle_manipulation.t.sol.j2",
}


@dataclass
class HoundFinding:
    """Structured output from agent_hound_omega or manual input."""
    target_name: str
    vuln_type: str
    hypothesis: str
    target_code: str
    exploit_plan: str = ""
    target_url: str = ""
    severity: str = "critical"


@dataclass
class STRIKEResult:
    """Result of a STRIKE generation + execution cycle."""
    test_file: Path | None = None
    compiled: bool = False
    executed: bool = False
    passed: bool = False
    verdict: str = "UNKNOWN"
    forge_output: str = ""
    iterations: int = 0
    error: str = ""


def select_template(vuln_type: str) -> Path | None:
    """Select the best matching Jinja2 template for the vulnerability type."""
    vuln_lower = vuln_type.lower().replace("-", "_").replace(" ", "_")
    for keyword, template_name in VULN_TEMPLATES.items():
        if keyword in vuln_lower:
            path = TEMPLATES_DIR / template_name
            if path.exists():
                return path
    return None


def load_heuristics_context(vuln_type: str) -> str:
    """Load relevant heuristics from autodidact-private as LLM context."""
    heuristics_dir = AUTODIDACT_PRIVATE / "heuristics"
    context_parts = []

    if heuristics_dir.exists():
        for heuristic_file in heuristics_dir.glob("*.md"):
            content = heuristic_file.read_text(encoding="utf-8")
            context_parts.append(f"--- {heuristic_file.name} ---\n{content}")

    return "\n\n".join(context_parts) if context_parts else ""


def generate_STRIKE_via_llm(finding: HoundFinding, template_content: str) -> str | None:
    """Use LocalLLMAdapter to generate a complete .t.sol from template + finding."""
    try:
        from adapters.local_llm_adapter import LocalLLMAdapterConfig
    except ImportError:
        print(f"  {C['R']}[STRIKE-GEN] LocalLLMAdapter not available. Using template-only mode.{C['X']}")
        return None

    config = LocalLLMAdapterConfig.from_env()
    if not config.model:
        print(f"  {C['R']}[STRIKE-GEN] No LM Studio model configured. Set AUTODIDACT_LM_STUDIO_MODEL.{C['X']}")
        return None

    heuristics = load_heuristics_context(finding.vuln_type)

    prompt_payload = {
        "kind": "foundry_STRIKE_request",
        "finding": {
            "target_name": finding.target_name,
            "vuln_type": finding.vuln_type,
            "hypothesis": finding.hypothesis,
            "exploit_plan": finding.exploit_plan,
            "severity": finding.severity,
        },
        "target_code": finding.target_code[:12000],
        "template": template_content,
        "heuristics_context": heuristics[:4000],
        "response_contract": {
            "format": "Complete Solidity test file (.t.sol)",
            "requirements": [
                "Must compile with `forge build`",
                "Must contain function testExploit_*",
                "Must use forge-std/Test.sol assertions",
                "Must demonstrate actual impact (fund loss, state corruption)",
                "No genesis comments — all code must be executable",
            ]
        },
        "constraints": [
            "Return ONLY the Solidity code. No markdown fences. No prose.",
            "The test MUST be self-contained (deploy target + exploit in setUp/test).",
            "Use vm.deal, vm.prank, vm.expectRevert when appropriate.",
            "THINK SURGICAL [Φ_Surgical]: Minimal code, maximum impact.",
            "THINK LOGIC [Φ_Logic]: State your attack vector in a NatSpec comment.",
        ],
    }

    prompt = json.dumps(prompt_payload, indent=2)

    # Direct LLM call (bypass bridge for speed)
    from urllib import request
    body = {
        "model": config.model,
        "temperature": 0.15,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Foundry security test generator for the CORTEX Autodidact system. "
                    "You generate complete, compilable Solidity test files that prove vulnerabilities. "
                    "Output ONLY valid Solidity code. No markdown. No explanations."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }

    payload = json.dumps(body).encode("utf-8")
    endpoint = f"{config.base_url}/chat/completions"
    http_request = request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=60) as response:
            raw_body = response.read().decode("utf-8")
        data = json.loads(raw_body)
        content = data["choices"][0]["message"]["content"]

        # Strip markdown fences if present
        import re
        fenced = re.search(r"```(?:solidity)?\s*(.*?)\s*```", content, re.DOTALL)
        if fenced:
            content = fenced.group(1)

        return content.strip()
    except Exception as exc:
        print(f"  {C['R']}[STRIKE-GEN] LLM request failed: {exc}{C['X']}")
        return None


def compile_STRIKE(test_file: Path) -> tuple[bool, str]:
    """Compile the generated test with forge build."""
    try:
        result = subprocess.run(
            ["forge", "build"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(OUROBOROS_DIR),
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: forge build exceeded 30s"
    except FileNotFoundError:
        return False, "forge binary not found"


def execute_STRIKE(test_file: Path) -> tuple[bool, str]:
    """Execute the STRIKE test with forge test."""
    test_file.stem.replace(".t", "")
    try:
        result = subprocess.run(
            [
                "forge", "test",
                "--match-path", f"test/generated/{test_file.name}",
                "-vvv",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(OUROBOROS_DIR),
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0 and "FAIL" not in output
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: forge test exceeded 60s"
    except FileNotFoundError:
        return False, "forge binary not found"


def generate_and_verify(finding: HoundFinding, max_iterations: int = 3) -> STRIKEResult:
    """
    Full pipeline: Generate STRIKE → Compile → Execute → Verify.
    Iterates up to max_iterations on failure.
    """
    result = STRIKEResult()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{C['B']}╔══════════════════════════════════════════════════╗{C['X']}")
    print(f"{C['B']}║{C['W']}  ∴ CORTEX-FOUNDRY-STRIKE v1.0 — EXPLOIT FORGE       {C['B']}║{C['X']}")
    print(f"{C['B']}╚══════════════════════════════════════════════════╝{C['X']}")
    print(f"  {C['D']}Target:{C['X']} {finding.target_name}")
    print(f"  {C['D']}Vuln:{C['X']}   {finding.vuln_type}")
    print(f"  {C['D']}Hypo:{C['X']}   {finding.hypothesis}")

    # Select template
    template_path = select_template(finding.vuln_type)
    template_content = ""
    if template_path:
        template_content = template_path.read_text(encoding="utf-8")
        print(f"  {C['G']}[✓] Template:{C['X']} {template_path.name}")
    else:
        print(f"  {C['D']}[○] No template match. LLM will generate from scratch.{C['X']}")

    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        print(f"\n  {C['V']}[ITER {iteration}/{max_iterations}]{C['X']}")

        # Generate
        print(f"  {C['D']}[○] Generating STRIKE via LLM...{C['X']}")
        sol_code = generate_STRIKE_via_llm(finding, template_content)
        if not sol_code:
            result.error = "LLM generation failed"
            print(f"  {C['R']}[✗] LLM generation failed{C['X']}")
            continue

        # Write to file
        safe_name = finding.target_name.replace(" ", "_").replace("/", "_")[:40]
        test_filename = f"AutodidactSTRIKE_{safe_name}_{finding.vuln_type}.t.sol"
        test_file = GENERATED_DIR / test_filename
        test_file.write_text(sol_code, encoding="utf-8")
        result.test_file = test_file
        print(f"  {C['G']}[✓] Written:{C['X']} {test_file}")

        # Compile
        print(f"  {C['D']}[○] Compiling...{C['X']}")
        compiled, compile_output = compile_STRIKE(test_file)
        result.compiled = compiled
        if not compiled:
            result.error = f"Compilation failed: {compile_output[:200]}"
            print(f"  {C['R']}[✗] Compile failed{C['X']}")
            # Feed error back to LLM on next iteration
            template_content += f"\n\n// PREVIOUS COMPILE ERROR:\n// {compile_output[:500]}"
            continue

        print(f"  {C['G']}[✓] Compiled successfully{C['X']}")

        # Execute
        print(f"  {C['D']}[○] Executing forge test...{C['X']}")
        passed, test_output = execute_STRIKE(test_file)
        result.executed = True
        result.passed = passed
        result.forge_output = test_output

        if passed:
            result.verdict = "C5-REAL"
            print(f"  {C['G']}[✓✓✓] EXPLOIT CONFIRMED — C5-REAL{C['X']}")
            break
        else:
            result.verdict = "C5-PENDING"
            result.error = f"Test failed: {test_output[:200]}"
            print(f"  {C['R']}[✗] Test failed. Iterating...{C['X']}")
            template_content += f"\n\n// PREVIOUS TEST FAILURE:\n// {test_output[:500]}"

    print(f"\n  {C['B']}{'─' * 50}{C['X']}")
    print(f"  {C['W']}Verdict:{C['X']} {result.verdict}")
    print(f"  {C['W']}Iterations:{C['X']} {result.iterations}")
    print(f"  {C['B']}{'─' * 50}{C['X']}\n")

    return result


if __name__ == "__main__":
    # Self-test with the existing HoneypotFuzz scenario
    finding = HoundFinding(
        target_name="MaliciousHoneypotToken",
        vuln_type="access_control",
        hypothesis="Token transfer function restricts selling to non-owner addresses, creating a honeypot",
        target_code="""
contract MaliciousHoneypotToken {
    mapping(address => uint256) public balanceOf;
    address public owner;
    constructor() { owner = msg.sender; }
    function mint(address to, uint256 amount) external { balanceOf[to] += amount; }
    function transfer(address to, uint256 amount) external returns (bool) {
        if (msg.sender != owner && to != owner) {
            revert("HONEYPOT: YOU CANNOT SELL");
        }
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
""",
        exploit_plan="Call transfer as non-owner to non-owner address to prove honeypot behavior",
    )

    result = generate_and_verify(finding)
    print(json.dumps({
        "test_file": str(result.test_file) if result.test_file else None,
        "verdict": result.verdict,
        "compiled": result.compiled,
        "passed": result.passed,
        "iterations": result.iterations,
    }, indent=2))
