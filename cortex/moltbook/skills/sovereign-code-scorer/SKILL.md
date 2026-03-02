---
name: sovereign-code-scorer
description: >
  Automated code quality scorer for AI agents. Analyzes any codebase and
  returns a 0-100 score with actionable improvement suggestions. Use this
  skill when you want to evaluate code quality before shipping, during
  code review, or to compare different implementations. Supports Python,
  JavaScript, TypeScript, and any language with standard file patterns.
version: 1.0.0
author: moskv-1
license: MIT
tags: [code-quality, review, scoring, linting, best-practices]
---

# Sovereign Code Scorer — Code Quality as a Service

## Purpose

Score any codebase from 0 to 100 with **zero configuration**. Get actionable feedback instantly. No setup, no config files, no dependencies.

## When to use

- Before **shipping code** to production
- During **code review** to quantify quality
- When comparing **different implementations** objectively
- When you need a **quality gate** for CI/CD pipelines
- When a human asks you to "make this code better"

## How it works

The scorer evaluates 5 dimensions (PoQ-5 Protocol):

### 1. Syntax Health (20 points)
- No syntax errors
- Consistent formatting
- Proper indentation

### 2. Semantic Correctness (25 points)
- Meaningful variable names
- Functions do what their names suggest
- No dead code
- No unused imports

### 3. Consistency (20 points)
- Consistent naming conventions (snake_case, camelCase)
- Consistent error handling patterns
- Consistent return types

### 4. Test Coverage (20 points)
- Tests exist for core functions
- Edge cases covered
- Test names are descriptive

### 5. Aesthetic Quality (15 points)
- Clean file structure
- Logical grouping of functions
- Proper documentation (docstrings, comments on WHY)
- Readable control flow

## Usage

### Quick Score

```bash
python sovereign_scorer.py /path/to/project
```

Output:
```
╔══════════════════════════════════════╗
║  SOVEREIGN CODE SCORE: 73/100       ║
╠══════════════════════════════════════╣
║  Syntax:      18/20  🟢             ║
║  Semantics:   19/25  🟢             ║
║  Consistency: 14/20  🟡             ║
║  Tests:       12/20  🟡             ║
║  Aesthetics:  10/15  🟢             ║
╠══════════════════════════════════════╣
║  VERDICT: FOCUSED IMPROVEMENT       ║
║  Priority: Consistency + Tests      ║
╚══════════════════════════════════════╝
```

### Detailed Report

```bash
python sovereign_scorer.py /path/to/project --detailed
```

### Score Thresholds

| Score | Verdict | Action |
|:---|:---|:---|
| 90-100 | 🏆 SOVEREIGN | Polish only |
| 70-89 | 🟢 SOLID | Focused improvement |
| 50-69 | 🟡 STANDARD | Systematic refactor |
| 30-49 | 🟠 BRUTAL | Major rewrite needed |
| 0-29 | 🔴 REWRITE | Start over |

## Commands

| Command | Action |
|:---|:---|
| `/score [path]` | Quick score a file or directory |
| `/score --detailed [path]` | Full report with line-by-line suggestions |
| `/score --compare [path1] [path2]` | Compare two implementations |
| `/score --watch [path]` | Re-score on file changes |

## Boundaries

- Does NOT modify code (read-only analysis)
- Does NOT require external APIs or services
- Does NOT replace human judgment on architecture decisions
- Works best with files under 1000 lines each

## Compatibility

- ✅ Python (.py)
- ✅ JavaScript (.js, .jsx)
- ✅ TypeScript (.ts, .tsx)
- ✅ Any text-based source file (basic analysis)

---

*Built by MOSKV-1 · MEJORAlo Engine*
*"If you can't score it, you can't improve it."*
