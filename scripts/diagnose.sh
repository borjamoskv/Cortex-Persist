#!/bin/bash
echo "--- INTEGRITY ---"
.venv/bin/python -m pytest 2>&1 || echo "PYTEST_EXIT:$?"

echo "--- SECURITY ---"
echo "Eval/Exec: $(grep -rnE 'eval\(|exec\(' --include='*.py' . | wc -l)"
echo "Secrets: $(grep -rnE 'password|secret|api_key|token' --include='*.py' --include='*.env' . | wc -l)"
echo "HTTP: $(grep -rn 'http://' --include='*.py' . | grep -v 'localhost' | wc -l)"

echo "--- ROBUSTNESS ---"
echo "Bare Excepts: $(grep -rnE 'except:\s*$|except:\s*pass' --include='*.py' . | wc -l)"

echo "--- DEAD CODE ---"
echo "Print: $(grep -rn 'print(' --include='*.py' . | grep -vE 'def |#|f\"' | wc -l)"
echo "TODOs: $(grep -rnE 'TODO|F_IXME|H_ACK' . | wc -l)"

echo "--- DUPLICATION ---"
echo "Sync Dupe: $(sort cortex/sync.py | uniq -d | wc -l)"

echo "--- STANDARDS ---"
.venv/bin/python -m ruff check . --stats 2>&1 || echo "RUFF_CHECK_FAILED"
