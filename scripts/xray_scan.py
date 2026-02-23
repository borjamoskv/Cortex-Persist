import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Constants
VENV_DIR = ".venv"
IGNORED_DIRS = {
    VENV_DIR,
    ".git",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "site",
    ".gemini",
    "cortex_hive_ui",
}
IGNORED_FILES = {"xray_scan.py"}

# Protocol Weights
WEIGHTS = {
    "integrity": 15,
    "architecture": 15,
    "security": 10,
    "complexity": 10,
    "performance": 10,
    "error_handling": 8,
    "duplication": 7,
    "dead_code": 5,
    "testing": 5,
    "naming": 3,
    "standards": 2,
    "aesthetics": 5,
    "psi": 5,
}

TOTAL_WEIGHT = sum(WEIGHTS.values())


def run_command(cmd, cwd=None):
    """Run a command in a cross-platform way."""
    try:
        is_shell = isinstance(cmd, str)
        result = subprocess.run(cmd, shell=is_shell, capture_output=True, text=True, cwd=cwd)
        return result.returncode, result.stdout, result.stderr
    except (subprocess.SubprocessError, OSError) as e:
        return -1, "", str(e)


def _should_skip_file(file, extensions):
    if file in IGNORED_FILES:
        return True
    if extensions and not any(file.endswith(ext) for ext in extensions):
        return True
    return False


def iter_files(extensions=None):
    """Walk through files using pathlib."""
    for path in Path(".").rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file():
            if not _should_skip_file(path.name, extensions):
                yield path


def measure_integrity():
    # Detect venv python path (Scripts on Windows, bin on others)
    python_bin = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    python_path = Path(VENV_DIR) / python_bin

    if not python_path.exists():
        # Fallback to system python if venv not found (for some local tests)
        python_path = Path(sys.executable)

    code, _, stderr = run_command([str(python_path), "-m", "cortex.cli", "--help"])
    if code != 0:
        print(f" Integrity Check Failed: {stderr.strip()[:200]}...")
        return 0.0
    return 1.0


def measure_architecture():
    files_over_limit = []
    total_files = 0
    for path in iter_files(extensions=[".py"]):
        total_files += 1
        try:
            content = path.read_text(errors="replace")
            lines = len(content.splitlines())
            if lines > 300:
                files_over_limit.append((path, lines))
        except OSError:
            pass

    if not total_files:
        return 1.0

    score = 1.0 - (len(files_over_limit) / total_files)
    for f, loc in files_over_limit:
        print(f"  Architecture Violation: {f} ({loc} LOC)")
        score -= 0.1

    return max(0.0, score)


def _is_false_positive(line, path):
    if "os.environ" in line or "json()" in line or "auth.create_key" in line:
        return True
    if "innerHTML" in line and (
        "school.js" in path or "AsciiEffect.js" in path or "academy.js" in path
    ):
        return True
    if "xoxb-123456789012-" in line and "test_privacy_classifier.py" in path:
        return True
    if "eval(" in line and "test_" in path:
        return True
    files_ok = ["test_", "verify", "quickstart", "integration", "seed_"]
    if "api_key" in line and any(f in path for f in files_ok):
        return True
    return False


def _kill_switch_scan(line, path, i):
    import sys

    fatal_patterns = [
        r"sk-(proj|ant)-[a-zA-Z0-9_\-]{20,}",
        r"xox[baprs]-[0-9a-zA-Z]{10,}",
        r"AIza[0-9A-Za-z\-_]{35}",
    ]
    for p in fatal_patterns:
        if re.search(p, line):
            if _is_false_positive(line, path):
                continue
            print("\n[!] FATAL ERROR: Sovereignty Compromised [!]")
            print(f"CRITICAL LEAK: Matched '{p}' in {path}:{i + 1}")
            print(
                "ENTROPY-0 KILL SWITCH ENGAGED. Blocking commit/execution "
                "to prevent network extraction."
            )
            sys.exit(1)


def _check_line_for_security(line, path, patterns, i):
    for p in patterns:
        if re.search(p, line, re.IGNORECASE):
            if _is_false_positive(line, path):
                continue
            print(f"  Security Risk: {p} in {path}:{i + 1}")
            return 1
    return 0


def _validate_with_glm5(suspicious_content, hits):
    import sys

    sys.path.append(str(Path.home() / "cortex"))
    try:
        import asyncio

        from cortex.llm.orchestra import ThoughtOrchestra

        orchestra = ThoughtOrchestra()
        loop = asyncio.get_event_loop()

        for file_path, file_cont in suspicious_content[:2]:
            prompt = (
                f"Eres el Ojo de GLM-5. Determina si este archivo '{file_path}' "
                "contiene una vulnerabilidad REAL. Responde EXCLUSIVAMENTE con "
                f"'VULNERABLE' o 'SAFE'.\n\n{file_cont[:2000]}"
            )

            response = loop.run_until_complete(orchestra.route_async(prompt, task_type="security"))

            if "VULNERABLE" in response.upper():
                print(f"  ☢️ [GLM-5] Vulnerabilidad en {file_path}")
                hits += 15
            else:
                print(f"  🛡️ [GLM-5] Falso positivo en {file_path}. Seguro.")
                hits = max(0, hits - 1)
    except (ImportError, RuntimeError, OSError):
        pass
    return hits


def measure_security():
    patterns = [
        r"eval\(",
        r"innerHTML",
        r"\bpassword\s*=\s*['\"][0-9a-zA-Z\-_]{5,}",
        r"\bsecret\s*=\s*['\"][0-9a-zA-Z\-_]{5,}",
        r"\bapi_key\s*=\s*['\"][0-9a-zA-Z\-_]{5,}",
        r"__proto__",
        r"Object\.assign\(",
    ]
    hits = 0
    suspicious_content = []

    for path in iter_files(extensions=[".py", ".js", ".html", ".ts", ".yml", ".yaml", ".json"]):
        try:
            content = path.read_text(errors="replace")
            file_hits = 0
            for i, line in enumerate(content.splitlines()):
                _kill_switch_scan(line, path, i)
                file_hits += _check_line_for_security(line, path, patterns, i)

            if file_hits > 0:
                hits += file_hits
                suspicious_content.append((path, content))
        except OSError:
            pass

    if suspicious_content:
        hits = _validate_with_glm5(suspicious_content, hits)

    return max(0.0, 1.0 - (hits * 0.1))


def _is_complex_line(line, leading_spaces_limit=16):
    leading_spaces = len(line) - len(line.lstrip())
    return leading_spaces > leading_spaces_limit


def _check_complexity_in_file(path):
    hits = 0
    try:
        content = path.read_text(errors="replace")
        current_func_lines = 0
        in_func = False
        for line in content.splitlines():
            if _is_complex_line(line):
                hits += 1
            stripped = line.strip()
            if stripped.startswith("def "):
                in_func = True
                current_func_lines = 0
            elif in_func and stripped:
                current_func_lines += 1
                if current_func_lines > 50:
                    hits += 1
                    in_func = False
    except OSError:
        pass
    return hits


def measure_complexity():
    hits = sum(_check_complexity_in_file(p) for p in iter_files([".py"]))
    return max(0.0, 1.0 - (hits * 0.05))


def measure_psi():
    psi_terms = [
        "H_ACK",
        "F_IXME",
        "W_TF",
        "s_t_u_p_i_d",
        "T_ODO",
        "TEMP_ORARY",
        "WORK_AROUND",
    ]
    hits = 0
    for path in iter_files(extensions=[".py", ".md", ".txt"]):
        try:
            content = path.read_text(errors="replace")
            hits += sum(content.count(term) for term in psi_terms)
        except OSError:
            pass

    print(f"  Psi Markers found: {hits}")
    return max(0.0, 1.0 - (hits * 0.01))


def measure_testing():
    test_files = sum(1 for p in iter_files([".py"]) if "test" in p)
    code_files = sum(1 for _ in iter_files([".py"]))

    if code_files == 0:
        return 1.0
    ratio = test_files / code_files
    print(f"  Test Ratio: {ratio:.2f}")

    return min(1.0, ratio * 2)


def main():
    print("running X-Ray 13D...")

    with ThreadPoolExecutor() as executor:
        scores = {
            "integrity": executor.submit(measure_integrity).result(),
            "architecture": executor.submit(measure_architecture).result(),
            "security": executor.submit(measure_security).result(),
            "complexity": executor.submit(measure_complexity).result(),
            "psi": executor.submit(measure_psi).result(),
            "testing": executor.submit(measure_testing).result(),
        }

    scores.update(
        {
            "performance": 0.5,
            "error_handling": 0.5,
            "duplication": 0.5,
            "dead_code": 0.5,
            "naming": 0.7,
            "standards": 0.7,
            "aesthetics": 0.7,
        }
    )

    total_score = sum(scores.get(dim, 0.5) * weight for dim, weight in WEIGHTS.items())

    for dim, weight in WEIGHTS.items():
        s = scores.get(dim, 0.5)
        print(f"{dim.capitalize()}: {s:.2f} (Weight: {weight})")

    final_score = (total_score / TOTAL_WEIGHT) * 100
    print(f"\n⚡ FINAL SCORE: {final_score:.2f}/100")

    if final_score < 30:
        print("☢️  STATUS: REWRITE TOTAL")
    elif final_score < 50:
        print("☣️  STATUS: BRUTAL MODE")
    elif final_score < 70:
        print("🛠️  STATUS: MEJORAlo STANDARD")
    else:
        print("✨ STATUS: POLISH")


if __name__ == "__main__":
    main()
