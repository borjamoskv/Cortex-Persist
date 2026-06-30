# 💻 CORTEX Frontend Workspace

Sovereign client application workspace for the BABYLON-60 persistence engine.

> **SYS_ID:** borjamoskv  
> **Aesthetic:** Industrial Noir 2026  
> **Environment:** Cloudflare Pages / Vite + React + TypeScript  

## 🛠️ Architecture
This folder contains the client-facing UI components, AST validations, and the Web Diagnostics interface. It communicates with the backend via JSON-RPC / REST APIs.

## 🚦 Model Assignments (Cognitive Layer)
By default, the following agent configuration is active for this repository:
- **Planning Agent:** `Gemini 3 Pro` — Handles user request parsing, component design plans, and dependency maps.
- **Code Execution Agent:** `Claude 4.6 / Claude 3.5 Sonnet` — Modifies the AST, creates UI components, and designs aesthetic features.
- **Test Writer Agent:** `Gemini 3.5 Flash` — Validates components via automated tests and writes visual assertion scripts.
