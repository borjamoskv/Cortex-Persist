# Repository Boundary Reconciliation Matrix

This snapshot records how the `codex/repo-boundary-cleanup` branch reconciled the tracked CORTEX repository with the boundary rules defined in [`../WORKSPACE_POLICY.md`](../WORKSPACE_POLICY.md).

It is not a product architecture document. It is a repository-boundary ledger: what used to be mixed into the core, where that surface belongs now, and which operating rule should prevent the contamination from returning.

## Baseline

- Canonical core repository: `/Users/borjafernandezangulo/30_CORTEX`
- Cleanup commits:
  - `9c34bbab` — `chore(workspace): extract non-core projects from cortex repo`
  - `e1aa858d` — `chore(repo): extract docs and marketing surfaces from core`
- Primary policy anchors:
  - `30_CORTEX` is the only core source of truth.
  - Long-form docs do not belong in the tracked core repo.
  - Marketing, landing, and web-shell assets do not belong in the tracked core repo.
  - Research, bounties, nested repos, backups, and worktrees do not belong in the tracked core repo.

## Reconciliation Matrix

| Surface | Before Cleanup | Current Status In `30_CORTEX` | Canonical Home / Owner | Enforcement Rule |
| :--- | :--- | :--- | :--- | :--- |
| Core runtime and product code | Mixed together with docs-site, marketing, bounty, and nested subproject material | Retained as the canonical tracked surface | `30_CORTEX` | Core work starts here by default. |
| Repo-root governance and buyer-facing entrypoints | Present, but diluted by duplicate doc trees and web-build surfaces | Retained as thin repo-root entrypoints | `30_CORTEX` | Keep repo-root docs concise, stable, and link out when depth is needed. |
| `docs/*.md` compatibility shims | Coexisted with a full in-repo docs site and backups | Retained as compatibility shims only | Dedicated docs surface at `https://cortexpersist.com/docs` and `/Users/borjafernandezangulo/30_CORTEX_DOCS` | Do not restart long-form docs work inside `docs/`. |
| Full docs-site content and historical backups | `src/content/docs/**`, `mkdocs.yml`, and `docs_backup/**` lived inside the core repo | Removed from tracked core | Dedicated docs repo or published docs surface | Historical material is archive content, not core product state. |
| Marketing and landing assets | Astro/Vercel app, web pages, media, site build scripts, and deploy configs lived in the core repo | Removed from tracked core | `/Users/borjafernandezangulo/cortexpersist-landing` | Web and landing work must happen in the landing repo, not in core. |
| Security research and bug-bounty artifacts | `bounty/` and `bounty_hunt/` lived beside product code | Removed from tracked core | Dedicated sibling repo under `10_PROJECTS` or quarantine under `90_REPO_RESCUE` | Research outside the shipped core cannot live in the canonical repo. |
| Parallel SDK package | `cortex-sdk/` duplicated SDK intent already covered by `sdks/` | Removed from tracked core | `sdks/` only, unless a sibling repo is explicitly created | Do not maintain parallel SDK trees inside core. |
| Nested Rust / Foundry / external subprojects | `cortex_mev_base/` lived inside the repo boundary | Removed from tracked core | Dedicated sibling repo under `10_PROJECTS` | No nested repos or non-core subprojects inside the canonical repo. |
| Local runtime residue and generated surfaces | `node_modules/`, `site/`, `src/`, `tmp*/`, `worktrees/`, `*.db`, caches, and scratch outputs still exist locally when needed | Ignored and non-canonical | Local workspace only | Ignored presence is acceptable; tracked re-entry is not. |

## Operating Rules After Cleanup

1. If the task changes core runtime, trust surfaces, tests, packaging, or governance entrypoints, work in `30_CORTEX`.
2. If the task needs a docs-site generator, marketing copy system, landing pages, or Vercel/Astro build assets, stop and switch to the dedicated sibling repo first.
3. If the task produces research, exploit, rescue, or archival material, route it to a dedicated sibling repo or quarantine path instead of the canonical core.
4. If ownership is unclear, classify the surface before coding. Do not let the core repo become the default dumping ground again.

## Residual Risk To Watch

The tracked Git boundary is now cleaner than the working directory boundary.

That means local ignored folders can still exist for tooling or operator convenience, but they must remain:

- untracked
- non-canonical
- easy to delete or relocate

The failure mode to avoid is not local residue by itself. The failure mode is silently promoting local residue back into the tracked product surface.
