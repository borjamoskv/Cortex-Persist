# Cortex Improvement Plan (MEJORAlo v9.0) & Stitch Analysis

## 1. ULTRATHINK Analysis (The 4 Lenses)

### Psychological
The user is juggling two distinct contexts: the backend infrastructure of **CORTEX** (refactoring async engine, stability) and the frontend/product vision of **Naroa 2026** ("Stitch cards", "Google Stitch idea"). The command "CORTEX mejoralo ultrathink" signals a desire to stabilize the core while keeping the creative momentum alive. The prompt "idea con google STICH mcp" suggests leveraging the **Stitch** brand/concept (via Google?) as a new MCP capability or integration.

### Technical
*   **CORTEX State**: Currently in a "half-migrated" state. `AsyncCortexEngine` has recent fixes but `engine_async.py` has leftovers from a failed refactor (lint errors, partial edits).
*   **Stitch Context**: `stitch-cards.css` defines a premium UI system ("Google Stitch-Quality"). This suggests "Stitch" is a *design language* or *quality standard* in Naroa, possibly inspired by Google's design or tools. The "Google Stitch MCP" idea might be about creating an MCP server that serves these UI components or integrates with a Google service to populate them.
*   **Actionable Gap**: We need to finish the `AsyncCortexEngine` cleanup to ensure the backend is robust enough to support whatever "Stitch MCP" becomes.

### Accessibility
*   **Cortex**: Backend improvement affects reliability.
*   **Stitch**: The CSS already includes `focus-visible` (WCAG), which is good. Any new MCP or integration must preserve these standards.

### Scalability
*   **Cortex**: The async refactor is key for scale (massive concurrency).
*   **Stitch**: If "Stitch" becomes a reusable MCP tool, it scales the design system across projects.

## 2. Immediate Objectives (MEJORAlo)

### Phase 1: Stabilize Cortex (Priority #1)
1.  **Fix `cortex/engine_async.py`**:
    *   Define `TX_BEGIN_IMMEDIATE` constant (already improved, verify usage).
    *   Fix the `vote` method signature (remove `agent_id` param if unused or fix usage).
    *   Simplift nested conditionals.
2.  **Verify Sync/Async Compat**:
    *   Ensure `SyncCompatMixin` works with `AsyncCortexEngine` logic.
    *   Run tests.

### Phase 2: Analyze & Propose "Google Stitch MCP" warning
*   **Hypothesis**: The user wants an MCP server that acts as a bridge to "Google Stitch" (concept) or creates "Stitch-quality" cards from Google data (e.g. Sheets/Docs/Photos).
*   **Verification**: Ask user for specific "Google Stitch" tool reference if not found.
*   **Proposal**: If "Stitch" = "Naroa Design System", then a "Stitch MCP" could generating these HTML/CSS components dynamically for the Agent to use in `generate_image` or UI building.

## 3. Execution Steps

1.  **Refactor `cortex/engine_async.py`**: Complete the lint fixes.
2.  **Run Tests**: Verify `cortex` integrity.
3.  **Stitch Integration**: acknowledge the CSS and propose an MCP connection.

