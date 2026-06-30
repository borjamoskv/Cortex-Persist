# ⚙️ CORTEX Backend Workspace

Sovereign persistence, validation, and forensic ledger backend workspace for the BABYLON-60 database.

> **SYS_ID:** borjamoskv  
> **Environment:** Python 3.10 - 3.13 / SQLite / SQLite-Vec  

## 🛠️ Architecture
This folder contains the core logic engines, sovereign guards, cryptographic ledger implementations, and database connection pools.

## 🚦 Model Assignments (Cognitive Layer)
By default, the following agent configuration is active for this repository:
- **Planning Agent:** `Gemini 3 Pro` — Handles schema design proposals, SAGA sequence planning, and safety boundary definition.
- **Code Execution Agent:** `Claude 4.6 / Claude 3.5 Sonnet` — Modifies the Python code, implements cryptographic ledger chains, and configures WAL database operations.
- **Test Writer Agent:** `Gemini 3.5 Flash` — Writes pytest unit/integration tests and validates invariants before commits.
