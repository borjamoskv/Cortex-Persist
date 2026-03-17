import glob
import subprocess


def calculate_complexity(file_path):
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    loc = len(lines)
    functions = sum(1 for line in lines if line.strip().startswith("def "))
    classes = sum(1 for line in lines if line.strip().startswith("class "))

    return loc, functions, classes


def main():
    print("[+] Iniciando Secuencia de Demostración: VECTOR 5 (Aniquilación Entrópica)")
    print("[+] Escaneando topología CORTEX en: cortex/cli/")

    files = glob.glob("cortex/cli/*.py")
    total_loc = 0
    total_funcs = 0

    for f in files:
        loc, funcs, clss = calculate_complexity(f)
        total_loc += loc
        total_funcs += funcs

    evidence = {
        "files_scanned": len(files),
        "total_lines_of_code": total_loc,
        "total_functions": total_funcs,
        "entropy_estimate": round(total_loc / (total_funcs + 1), 2),
    }

    print(
        f"\n[!] Entropía Calculada. {len(files)} archivos, {total_loc} líneas, {total_funcs} funciones."
    )
    print(f"[!] Ratio de Entropía: {evidence['entropy_estimate']}")

    content = f"Demonstration vector executed. Analyzed cortex/cli/. Found {total_loc} LOC. Entropy ratio: {evidence['entropy_estimate']}."

    # Inyectar en CORTEX
    print("\n[+] Forzando colapso de función: Escribiendo en el Master Ledger de CORTEX...")
    cmd = f'.venv/bin/cortex store --type ghost --source agent:antigravity_demo CORTEX_DEMO "{content}"'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        print("[+] SUCCESS: Entropía cristalizada en el Ledger.")
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print("[-] ERROR al inyectar en CORTEX. ¿Está el daemon corriendo o disponible?")
        print(e.stderr)


if __name__ == "__main__":
    main()
