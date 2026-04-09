# Canonical Demo

This is the shortest reproducible proof of product value in CORTEX Persist:

1. Store a decision.
2. Verify it while clean.
3. Simulate external tampering.
4. Re-verify the fact and the ledger.
5. Export evidence.

The demo is intentionally CLI-first because the current supported core is local-first and source-installed.

## Prerequisites

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install .
```

## Run The Demo

```bash
export DB=/tmp/cortex-demo.db
export OUT=/tmp/cortex-demo.json
rm -f "$DB" "$OUT"

cortex init --db "$DB"

cortex store risk-bot \
  "Transaction flagged: IP mismatch on payout" \
  --type decision \
  --source agent:risk-bot \
  --tags fraud,payout \
  --db "$DB"

export FACT_ID=$(python - <<'PY'
import os
import sqlite3

db = os.environ["DB"]
with sqlite3.connect(db) as conn:
    print(conn.execute("SELECT id FROM facts ORDER BY id DESC LIMIT 1").fetchone()[0])
PY
)

cortex recall risk-bot --db "$DB"
cortex verify "$FACT_ID" --db "$DB"
cortex trust-ledger verify --full --db "$DB"
```

What this should prove:

- `recall` shows the stored decision in the project context.
- `verify` reports the fact as verified while it is still clean.
- `trust-ledger verify --full` reports the ledger and fact set as valid.

## Tamper Drill

Now simulate an out-of-band mutation that bypasses the write path.

```bash
python - <<'PY'
import os
import sqlite3

db = os.environ["DB"]
fact_id = int(os.environ["FACT_ID"])

with sqlite3.connect(db) as conn:
    conn.execute(
        "UPDATE facts SET content = ? WHERE id = ?",
        ("Tampered payout decision", fact_id),
    )
    conn.commit()
PY

cortex verify "$FACT_ID" --db "$DB"
cortex trust-ledger verify --full --db "$DB"
cortex export --project risk-bot --format json --out "$OUT" --db "$DB"
```

What should change:

- `cortex verify` should now report `INTEGRITY VIOLATION`.
- `Content Integrity` should show `HASH_MISMATCH`.
- `cortex trust-ledger verify --full` should report `Ledger is COMPROMISED`.
- `export` should leave a JSON artifact that captures the compromised state for review outside the runtime.

This is the core product claim: silent database mutation stops looking silent.

## Notes

- `init` seeds the database, so the first user fact is not guaranteed to be `#1`.
- `FACT_ID` is resolved from SQLite so the demo stays deterministic.
- The tamper drill is for demonstration only. It intentionally bypasses normal guard and write-path rules.

## Related References

- [Supported Core](supported-core.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
- [API Reference](api.md)
- [Operations](OPERATIONS.md)
