import re
import sys

def classify_error(message):
    message_lower = message.lower()
    if "no module named 'hypothesis'" in message_lower:
        return "Infraestructura (Falta Hypothesis)"
    elif "redis" in message_lower and "connection" in message_lower:
        return "Infraestructura (Redis no disponible)"
    elif "fixture 'db_path' not found" in message_lower:
        return "Obsoleto (Missing db_path fixture)"
    elif "ledger" in message_lower or "taint_engine" in message_lower:
        return "Regresión P0 (Core Crypto/Audit)"
    elif "cortex_test_env" in message_lower:
        return "Entorno Local"
    elif "importerror" in message_lower or "modulenotfounderror" in message_lower:
        return "Infraestructura (Imports rotos)"
    else:
        return "Regresión (Otros)"

def main():
    log_file = sys.argv[1] if len(sys.argv) > 1 else "tests_output.log"
    
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {log_file}: {e}")
        sys.exit(1)
        
    failures = []
    current_fail = None
    
    for line in lines:
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            if current_fail:
                failures.append(current_fail)
            current_fail = {"nodeid": line.split()[1], "message": ""}
        elif current_fail and line.strip() and not line.startswith("=") and not line.startswith("-"):
            current_fail["message"] += line

    if current_fail:
        failures.append(current_fail)
        
    categories = {}
    for t in failures:
        cat = classify_error(t["message"])
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
        
    print(f"# Pytest Triage Report")
    print(f"Total Failures Found in Log: {len(failures)}")
    print("\n## Clasificación de Fallos\n")
    
    for cat, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"### {cat}: {len(items)} fallos")
        for i, item in enumerate(items[:5]): # show top 5
            msg = item["message"].splitlines()
            err_line = msg[-1].strip() if msg else ""
            print(f"- `{item['nodeid']}`: {err_line}")
        if len(items) > 5:
            print(f"- ... y {len(items) - 5} más.")
        print("")

if __name__ == "__main__":
    main()
