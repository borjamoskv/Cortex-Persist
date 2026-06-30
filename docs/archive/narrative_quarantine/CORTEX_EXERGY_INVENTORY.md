# CORTEX Ecosystem Master Exergy Inventory

Consolidated thermodynamic exergy ranking of all SKILLS, SCRIPTS, WORKFLOWS, and PLUGIN SKILLS in the CORTEX ecosystem.

* **Reality Level**: C5-REAL (Dynamic AST + code-block telemetry)
* **Date**: 2026-06-30
* **Compiler**: `scripts/compile_exergy_inventory.py` v2.0

## Summary

```yaml
total_components: 211
exergy_mean: 65.9
exergy_median: 59.3
exergy_min: 50.0
exergy_max: 94.0
type_distribution:
  Plugin Skill: 4
  Script: 74
  Skill: 56
  Workflow: 77
status_distribution:
  Active: 155
  Active (Plugin): 4
  Archived: 14
  Cold Storage: 30
  Tombstoned: 8
```

---

## Justification Logic

```yaml
Python_scoring:
  method: AST analysis via ast.parse()
  formula: 100.0 - (weighted_entropy * 100.0)
  weights:
    mccabe_density: 0.35
    nesting_depth: 0.25
    import_density: 0.20
    size_penalty: 0.20
  confidence: C5

Markdown_scoring:
  method: Code block ratio + YAML structure bonus
  formula: 50.0 + (code_ratio * 45.0) + min(yaml_blocks * 2, 10)
  confidence: C4

Shell_scoring:
  method: Command density analysis
  formula: 50.0 + (exec_ratio * 40.0) + (size_factor * 10.0)
  confidence: C4
```

---

## Active Skills

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 1 | [Frontier-RevEng-OMEGA](file://~/.gemini/config/skills/Frontier-RevEng-OMEGA/SKILL.md) | **90.0** | code-block-ratio | 542 | C4 |
| 2 | [Python-Extractor-OMEGA](file://~/.gemini/config/skills/Python-Extractor-OMEGA/SKILL.md) | **76.4** | code-block-ratio | 35 | C4 |
| 3 | [Sortu-APEX](file://~/.gemini/config/skills/Sortu-APEX/SKILL.md) | **71.7** | code-block-ratio | 341 | C4 |
| 4 | [Cortex-Omega-ATMS-OMEGA](file://~/.gemini/config/skills/Cortex-Omega-ATMS-OMEGA/SKILL.md) | **69.5** | code-block-ratio | 151 | C4 |
| 5 | [Browser-CDP-Automation-OMEGA](file://~/.gemini/config/skills/Browser-CDP-Automation-OMEGA/SKILL.md) | **69.3** | code-block-ratio | 156 | C4 |
| 6 | [Thermodynamic-Task-Router-OMEGA](file://~/.gemini/config/skills/Thermodynamic-Task-Router-OMEGA/SKILL.md) | **67.2** | code-block-ratio | 74 | C4 |
| 7 | [AUTODIDACT-OMEGA](file://~/.gemini/config/skills/AUTODIDACT-OMEGA/SKILL.md) | **66.5** | code-block-ratio | 252 | C4 |
| 8 | [Antigravity-Github-Omega](file://~/.gemini/config/skills/Antigravity-Github-Omega/SKILL.md) | **61.2** | code-block-ratio | 78 | C4 |
| 9 | [SOTA-Vector-Engine-Omega](file://~/.gemini/config/skills/SOTA-Vector-Engine-Omega/SKILL.md) | **61.2** | code-block-ratio | 142 | C4 |
| 10 | [accidental-data-loss-prevention](file://~/.gemini/config/skills/accidental-data-loss-prevention/SKILL.md) | **59.3** | code-block-ratio | 31 | C4 |
| 11 | [managing-python-dependencies](file://~/.gemini/config/skills/managing-python-dependencies/SKILL.md) | **58.5** | code-block-ratio | 101 | C4 |
| 12 | [Session-Crystallizer-OMEGA](file://~/.gemini/config/skills/Session-Crystallizer-OMEGA/SKILL.md) | **57.3** | code-block-ratio | 124 | C4 |
| 13 | [Sovereign-Director-OMEGA](file://~/.gemini/config/skills/Sovereign-Director-OMEGA/SKILL.md) | **57.1** | code-block-ratio | 35 | C4 |
| 14 | [Tmux-PTY-Bridge-OMEGA](file://~/.gemini/config/skills/Tmux-PTY-Bridge-OMEGA/SKILL.md) | **56.4** | code-block-ratio | 63 | C4 |
| 15 | [Algorithmic-Music-OMEGA](file://~/.gemini/config/skills/Algorithmic-Music-OMEGA/SKILL.md) | **55.2** | code-block-ratio | 70 | C4 |
| 16 | [ouroboros-infinity](file://~/.gemini/config/skills/ouroboros-infinity/SKILL.md) | **54.1** | code-block-ratio | 255 | C4 |
| 17 | [LEA-OMEGA](file://~/.gemini/config/skills/LEA-OMEGA/SKILL.md) | **53.4** | code-block-ratio | 100 | C4 |
| 18 | [Uniswap-v4-Auditor-OMEGA](file://~/.gemini/config/skills/Uniswap-v4-Auditor-OMEGA/SKILL.md) | **53.2** | code-block-ratio | 42 | C4 |
| 19 | [Agentic-Eval-OMEGA](file://~/.gemini/config/skills/Agentic-Eval-OMEGA/SKILL.md) | **51.1** | code-block-ratio | 40 | C4 |
| 20 | [Aesthetic-Foundry-Omega](file://~/.gemini/config/skills/Aesthetic-Foundry-Omega/SKILL.md) | **50.0** | code-block-ratio | 77 | C4 |
| 21 | [Bounty-Exergy-Extractor-OMEGA](file://~/.gemini/config/skills/Bounty-Exergy-Extractor-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 19 | C4 |
| 22 | [Epistemic-Purge-OMEGA](file://~/.gemini/config/skills/Epistemic-Purge-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 48 | C4 |
| 23 | [Local-Inference-OMEGA](file://~/.gemini/config/skills/Local-Inference-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 36 | C4 |
| 24 | [Mac-Control-Ω](file://~/.gemini/config/skills/Mac-Control-Ω/SKILL.md) | **50.0** | code-block-ratio | 107 | C4 |
| 25 | [MAXWELL-DAEMON-OMEGA](file://~/.gemini/config/skills/MAXWELL-DAEMON-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 56 | C4 |
| 26 | [MOSKV1-Arsenal-OMEGA](file://~/.gemini/config/skills/MOSKV1-Arsenal-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 643 | C4 |
| 27 | [ONTOLOGY-FORGE-OMEGA](file://~/.gemini/config/skills/ONTOLOGY-FORGE-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 49 | C4 |
| 28 | [OSINT-Mitigation-OMEGA](file://~/.gemini/config/skills/OSINT-Mitigation-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 22 | C4 |
| 29 | [Scientific-Deconstruction-OMEGA](file://~/.gemini/config/skills/Scientific-Deconstruction-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 27 | C4 |
| 30 | [singularity-nexus](file://~/.gemini/config/skills/singularity-nexus/SKILL.md) | **50.0** | code-block-ratio | 26 | C4 |
| 31 | [Thermodynamic-Context-Compression-OMEGA](file://~/.gemini/config/skills/Thermodynamic-Context-Compression-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 32 | C4 |
| 32 | [ULTRATHINK-OMEGA](file://~/.gemini/config/skills/ULTRATHINK-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 30 | C4 |
| 33 | [Vanguard-Transversal-OMEGA](file://~/.gemini/config/skills/Vanguard-Transversal-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 62 | C4 |
| 34 | [Vesicular-Runtime-Omega](file://~/.gemini/config/skills/Vesicular-Runtime-Omega/SKILL.md) | **50.0** | code-block-ratio | 63 | C4 |

## Tombstoned Skills

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 35 | [Exergy-Engine-OMEGA](file://~/.gemini/config/skills/.tombstone/Exergy-Engine-OMEGA/SKILL.md) | **80.1** | code-block-ratio | 38 | C4 |
| 36 | [Estado-Del-Arte-OMEGA](file://~/.gemini/config/skills/.tombstone/Estado-Del-Arte-OMEGA/SKILL.md) | **73.4** | code-block-ratio | 40 | C4 |
| 37 | [Autodidact-History-OMEGA](file://~/.gemini/config/skills/.tombstone/Autodidact-History-OMEGA/SKILL.md) | **70.4** | code-block-ratio | 154 | C4 |
| 38 | [CAOS-OMEGA](file://~/.gemini/config/skills/.tombstone/CAOS-OMEGA/SKILL.md) | **55.6** | code-block-ratio | 50 | C4 |
| 39 | [Exergy-Matrix-OMEGA](file://~/.gemini/config/skills/.tombstone/Exergy-Matrix-OMEGA/SKILL.md) | **55.3** | code-block-ratio | 41 | C4 |
| 40 | [Anergy-OMEGA](file://~/.gemini/config/skills/.tombstone/Anergy-OMEGA/SKILL.md) | **55.1** | code-block-ratio | 43 | C4 |
| 41 | [Autodidact-Research-OMEGA](file://~/.gemini/config/skills/.tombstone/Autodidact-Research-OMEGA/SKILL.md) | **55.0** | code-block-ratio | 45 | C4 |
| 42 | [Autonomous-Audit-OMEGA](file://~/.gemini/config/skills/.tombstone/Autonomous-Audit-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 23 | C4 |

## Archived Skills

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 43 | [Agent-Paper-RedTeam-OMEGA](file://~/.gemini/config/skills/_archived/Agent-Paper-RedTeam-OMEGA/SKILL.md) | **88.7** | code-block-ratio | 49 | C4 |
| 44 | [Causal-Compiler-OMEGA](file://~/.gemini/config/skills/_archived/Causal-Compiler-OMEGA/SKILL.md) | **75.8** | code-block-ratio | 80 | C4 |
| 45 | [Human-Mosaic-Assembler-OMEGA](file://~/.gemini/config/skills/_archived/Human-Mosaic-Assembler-OMEGA/SKILL.md) | **64.3** | code-block-ratio | 66 | C4 |
| 46 | [Knowledge-Self-Healing-Agents](file://~/.gemini/config/skills/_archived/Knowledge-Self-Healing-Agents/SKILL.md) | **56.2** | code-block-ratio | 32 | C4 |
| 47 | [Knowledge-Gemini-Spark](file://~/.gemini/config/skills/_archived/Knowledge-Gemini-Spark/SKILL.md) | **55.4** | code-block-ratio | 40 | C4 |
| 48 | [Comite-Expertos-OMEGA](file://~/.gemini/config/skills/_archived/Comite-Expertos-OMEGA/SKILL.md) | **54.8** | code-block-ratio | 48 | C4 |
| 49 | [Gemini-Omni-Prompting-OMEGA](file://~/.gemini/config/skills/_archived/Gemini-Omni-Prompting-OMEGA/SKILL.md) | **54.2** | code-block-ratio | 62 | C4 |
| 50 | [allet-Forensics-Bizkaia-OMEGA](file://~/.gemini/config/skills/_archived/allet-Forensics-Bizkaia-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 94 | C4 |
| 51 | [AntiNigromancia-Lexical-OMEGA](file://~/.gemini/config/skills/_archived/AntiNigromancia-Lexical-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 41 | C4 |
| 52 | [elder-plinius-OMEGA](file://~/.gemini/config/skills/_archived/elder-plinius-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 20 | C4 |
| 53 | [HoTT-AGI-Inference-OMEGA](file://~/.gemini/config/skills/_archived/HoTT-AGI-Inference-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 184 | C4 |
| 54 | [OG-Agent-Standards-OMEGA](file://~/.gemini/config/skills/_archived/OG-Agent-Standards-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 44 | C4 |
| 55 | [Substack-Automation-Omega](file://~/.gemini/config/skills/_archived/Substack-Automation-Omega/SKILL.md) | **50.0** | code-block-ratio | 40 | C4 |
| 56 | [Zero-Employee-Orchestrator-OMEGA](file://~/.gemini/config/skills/_archived/Zero-Employee-Orchestrator-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 36 | C4 |

## Plugin Skills

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 57 | [google-antigravity-sdk/google-antigravity-sdk](file://~/.gemini/config/plugins/google-antigravity-sdk/skills/google-antigravity-sdk/SKILL.md) | **91.2** | code-block-ratio | 81 | C4 |
| 58 | [modern-web-guidance-plugin/chrome-extensions](file://~/.gemini/config/plugins/modern-web-guidance-plugin/skills/chrome-extensions/SKILL.md) | **51.1** | code-block-ratio | 119 | C4 |
| 59 | [chrome-devtools-plugin/Web-Diagnostics-OMEGA](file://~/.gemini/config/plugins/chrome-devtools-plugin/skills/Web-Diagnostics-OMEGA/SKILL.md) | **50.0** | code-block-ratio | 50 | C4 |
| 60 | [modern-web-guidance-plugin/modern-web-guidance](file://~/.gemini/config/plugins/modern-web-guidance-plugin/skills/modern-web-guidance/SKILL.md) | **50.0** | code-block-ratio | 33 | C4 |

## Active Workflows

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 61 | [browser-subagent](file://~/30_CORTEX/.agents/workflows/browser-subagent.md) | **71.8** | code-block-ratio | 211 | C4 |
| 62 | [health](file://~/30_CORTEX/.agents/workflows/health.md) | **64.5** | code-block-ratio | 31 | C4 |
| 63 | [ouroboros](file://~/30_CORTEX/.agents/workflows/ouroboros.md) | **64.5** | code-block-ratio | 279 | C4 |
| 64 | [legion](file://~/30_CORTEX/.agents/workflows/legion.md) | **64.2** | code-block-ratio | 128 | C4 |
| 65 | [antigravity](file://~/30_CORTEX/.agents/workflows/antigravity.md) | **58.1** | code-block-ratio | 100 | C4 |
| 66 | [BABYLON60-PERSIST-WHITEPAPER](file://~/30_CORTEX/.agents/workflows/BABYLON60-PERSIST-WHITEPAPER.md) | **57.8** | code-block-ratio | 327 | C4 |
| 67 | [CORTEX-PERSIST-WHITEPAPER](file://~/30_CORTEX/.agents/workflows/CORTEX-PERSIST-WHITEPAPER.md) | **57.8** | code-block-ratio | 327 | C4 |
| 68 | [organizar](file://~/30_CORTEX/.agents/workflows/organizar.md) | **56.3** | code-block-ratio | 43 | C4 |
| 69 | [steal](file://~/30_CORTEX/.agents/workflows/steal.md) | **55.9** | code-block-ratio | 38 | C4 |
| 70 | [intencion](file://~/30_CORTEX/.agents/workflows/intencion.md) | **54.4** | code-block-ratio | 31 | C4 |
| 71 | [build](file://~/30_CORTEX/.agents/workflows/build.md) | **54.3** | code-block-ratio | 42 | C4 |
| 72 | [ontologia](file://~/30_CORTEX/.agents/workflows/ontologia.md) | **54.1** | code-block-ratio | 66 | C4 |
| 73 | [RFC-BABYLON60-NATIVE-AI](file://~/30_CORTEX/.agents/workflows/RFC-BABYLON60-NATIVE-AI.md) | **54.1** | code-block-ratio | 287 | C4 |
| 74 | [RFC-CORTEX-NATIVE-AI](file://~/30_CORTEX/.agents/workflows/RFC-CORTEX-NATIVE-AI.md) | **54.1** | code-block-ratio | 287 | C4 |
| 75 | [enterrar](file://~/30_CORTEX/.agents/workflows/enterrar.md) | **54.0** | code-block-ratio | 34 | C4 |
| 76 | [memory](file://~/30_CORTEX/.agents/workflows/memory.md) | **53.4** | code-block-ratio | 66 | C4 |
| 77 | [naroa-file-safety](file://~/30_CORTEX/.agents/workflows/naroa-file-safety.md) | **53.0** | code-block-ratio | 30 | C4 |
| 78 | [idea](file://~/30_CORTEX/.agents/workflows/idea.md) | **52.9** | code-block-ratio | 46 | C4 |
| 79 | [NATIVE-THINKING-ARCHITECTURES](file://~/30_CORTEX/.agents/workflows/NATIVE-THINKING-ARCHITECTURES.md) | **52.4** | code-block-ratio | 243 | C4 |
| 80 | [naroa-debug-routing](file://~/30_CORTEX/.agents/workflows/naroa-debug-routing.md) | **51.6** | code-block-ratio | 28 | C4 |
| 81 | [arquitecto_codigo](file://~/30_CORTEX/.agents/workflows/arquitecto_codigo.md) | **50.0** | code-block-ratio | 63 | C4 |
| 82 | [BABYLON60-NATIVE-AI-MANIFESTO](file://~/30_CORTEX/.agents/workflows/BABYLON60-NATIVE-AI-MANIFESTO.md) | **50.0** | code-block-ratio | 52 | C4 |
| 83 | [comandante_despliegue](file://~/30_CORTEX/.agents/workflows/comandante_despliegue.md) | **50.0** | code-block-ratio | 66 | C4 |
| 84 | [confluence-awwwards](file://~/30_CORTEX/.agents/workflows/confluence-awwwards.md) | **50.0** | code-block-ratio | 22 | C4 |
| 85 | [confluence-black-swan](file://~/30_CORTEX/.agents/workflows/confluence-black-swan.md) | **50.0** | code-block-ratio | 22 | C4 |
| 86 | [confluence-inmortal](file://~/30_CORTEX/.agents/workflows/confluence-inmortal.md) | **50.0** | code-block-ratio | 23 | C4 |
| 87 | [confluence-mmx](file://~/30_CORTEX/.agents/workflows/confluence-mmx.md) | **50.0** | code-block-ratio | 22 | C4 |
| 88 | [confluence-nightshift](file://~/30_CORTEX/.agents/workflows/confluence-nightshift.md) | **50.0** | code-block-ratio | 22 | C4 |
| 89 | [confluence-sindicate](file://~/30_CORTEX/.agents/workflows/confluence-sindicate.md) | **50.0** | code-block-ratio | 22 | C4 |
| 90 | [CORTEX-NATIVE-AI-MANIFESTO](file://~/30_CORTEX/.agents/workflows/CORTEX-NATIVE-AI-MANIFESTO.md) | **50.0** | code-block-ratio | 52 | C4 |
| 91 | [daily-evolution](file://~/30_CORTEX/.agents/workflows/daily-evolution.md) | **50.0** | code-block-ratio | 32 | C4 |
| 92 | [ens-domain-monitor](file://~/30_CORTEX/.agents/workflows/ens-domain-monitor.md) | **50.0** | code-block-ratio | 26 | C4 |
| 93 | [flujo_glorioso_v2](file://~/30_CORTEX/.agents/workflows/flujo_glorioso_v2.md) | **50.0** | code-block-ratio | 84 | C4 |
| 94 | [kimi](file://~/30_CORTEX/.agents/workflows/kimi.md) | **50.0** | code-block-ratio | 24 | C4 |
| 95 | [mcp-status](file://~/30_CORTEX/.agents/workflows/mcp-status.md) | **50.0** | code-block-ratio | 25 | C4 |
| 96 | [moskv-1-identity](file://~/30_CORTEX/.agents/workflows/moskv-1-identity.md) | **50.0** | code-block-ratio | 25 | C4 |
| 97 | [muro](file://~/30_CORTEX/.agents/workflows/muro.md) | **50.0** | code-block-ratio | 28 | C4 |
| 98 | [musa_creativa](file://~/30_CORTEX/.agents/workflows/musa_creativa.md) | **50.0** | code-block-ratio | 63 | C4 |
| 99 | [naroa-nueva-obra](file://~/30_CORTEX/.agents/workflows/naroa-nueva-obra.md) | **50.0** | code-block-ratio | 27 | C4 |
| 100 | [naroa-nueva-seccion](file://~/30_CORTEX/.agents/workflows/naroa-nueva-seccion.md) | **50.0** | code-block-ratio | 27 | C4 |
| 101 | [omega_protocol](file://~/30_CORTEX/.agents/workflows/omega_protocol.md) | **50.0** | code-block-ratio | 94 | C4 |
| 102 | [playground](file://~/30_CORTEX/.agents/workflows/playground.md) | **50.0** | code-block-ratio | 51 | C4 |
| 103 | [reverse-engineer](file://~/30_CORTEX/.agents/workflows/reverse-engineer.md) | **50.0** | code-block-ratio | 31 | C4 |
| 104 | [sentinel_seguridad](file://~/30_CORTEX/.agents/workflows/sentinel_seguridad.md) | **50.0** | code-block-ratio | 63 | C4 |
| 105 | [sigint-cybint](file://~/30_CORTEX/.agents/workflows/sigint-cybint.md) | **50.0** | code-block-ratio | 77 | C4 |
| 106 | [soulseek-download](file://~/30_CORTEX/.agents/workflows/soulseek-download.md) | **50.0** | code-block-ratio | 29 | C4 |
| 107 | [tips](file://~/30_CORTEX/.agents/workflows/tips.md) | **50.0** | code-block-ratio | 32 | C4 |

## Cold Storage Workflows

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 108 | [consolidator-omega](file://~/COLD_STORAGE/cortex-config/workflows/consolidator-omega.md) | **75.8** | code-block-ratio | 97 | C4 |
| 109 | [forjar](file://~/COLD_STORAGE/cortex-config/workflows/forjar.md) | **73.6** | code-block-ratio | 137 | C4 |
| 110 | [ship](file://~/COLD_STORAGE/cortex-config/workflows/ship.md) | **73.0** | code-block-ratio | 143 | C4 |
| 111 | [gem-forge](file://~/COLD_STORAGE/cortex-config/workflows/gem-forge.md) | **71.2** | code-block-ratio | 87 | C4 |
| 112 | [falsacion](file://~/COLD_STORAGE/cortex-config/workflows/falsacion.md) | **70.9** | code-block-ratio | 91 | C4 |
| 113 | [health-cortex](file://~/COLD_STORAGE/cortex-config/workflows/health-cortex.md) | **70.3** | code-block-ratio | 91 | C4 |
| 114 | [guardian](file://~/COLD_STORAGE/cortex-config/workflows/guardian.md) | **68.9** | code-block-ratio | 157 | C4 |
| 115 | [autonomo](file://~/COLD_STORAGE/cortex-config/workflows/autonomo.md) | **66.6** | code-block-ratio | 132 | C4 |
| 116 | [token-hygiene](file://~/COLD_STORAGE/cortex-config/workflows/token-hygiene.md) | **65.6** | code-block-ratio | 49 | C4 |
| 117 | [memoria](file://~/COLD_STORAGE/cortex-config/workflows/memoria.md) | **64.0** | code-block-ratio | 254 | C4 |
| 118 | [analysis_pipeline](file://~/COLD_STORAGE/cortex-config/workflows/analysis_pipeline.md) | **61.0** | code-block-ratio | 49 | C4 |
| 119 | [speed-parallel](file://~/COLD_STORAGE/cortex-config/workflows/speed-parallel.md) | **59.0** | code-block-ratio | 55 | C4 |
| 120 | [proactivo](file://~/COLD_STORAGE/cortex-config/workflows/proactivo.md) | **58.8** | code-block-ratio | 118 | C4 |
| 121 | [mafia-ai-radar](file://~/COLD_STORAGE/cortex-config/workflows/mafia-ai-radar.md) | **58.7** | code-block-ratio | 62 | C4 |
| 122 | [redaccion-ia](file://~/COLD_STORAGE/cortex-config/workflows/redaccion-ia.md) | **58.5** | code-block-ratio | 97 | C4 |
| 123 | [pulir](file://~/COLD_STORAGE/cortex-config/workflows/pulir.md) | **57.6** | code-block-ratio | 89 | C4 |
| 124 | [deploy](file://~/COLD_STORAGE/cortex-config/workflows/deploy.md) | **56.9** | code-block-ratio | 98 | C4 |
| 125 | [anamnesis](file://~/COLD_STORAGE/cortex-config/workflows/anamnesis.md) | **56.4** | code-block-ratio | 49 | C4 |
| 126 | [genesis](file://~/COLD_STORAGE/cortex-config/workflows/genesis.md) | **56.1** | code-block-ratio | 88 | C4 |
| 127 | [antigravity](file://~/COLD_STORAGE/cortex-config/workflows/antigravity.md) | **55.8** | code-block-ratio | 130 | C4 |
| 128 | [compilar](file://~/COLD_STORAGE/cortex-config/workflows/compilar.md) | **55.1** | code-block-ratio | 98 | C4 |
| 129 | [qa](file://~/COLD_STORAGE/cortex-config/workflows/qa.md) | **54.5** | code-block-ratio | 80 | C4 |
| 130 | [web-sota-100](file://~/COLD_STORAGE/cortex-config/workflows/web-sota-100.md) | **53.2** | code-block-ratio | 114 | C4 |
| 131 | [production-boundary](file://~/COLD_STORAGE/cortex-config/workflows/production-boundary.md) | **52.7** | code-block-ratio | 66 | C4 |
| 132 | [c7-epistemology](file://~/COLD_STORAGE/cortex-config/workflows/c7-epistemology.md) | **50.0** | code-block-ratio | 91 | C4 |
| 133 | [consolidacion-masiva](file://~/COLD_STORAGE/cortex-config/workflows/consolidacion-masiva.md) | **50.0** | code-block-ratio | 66 | C4 |
| 134 | [detective](file://~/COLD_STORAGE/cortex-config/workflows/detective.md) | **50.0** | code-block-ratio | 36 | C4 |
| 135 | [exergy-cascade](file://~/COLD_STORAGE/cortex-config/workflows/exergy-cascade.md) | **50.0** | code-block-ratio | 82 | C4 |
| 136 | [manifiesto-omega](file://~/COLD_STORAGE/cortex-config/workflows/manifiesto-omega.md) | **50.0** | code-block-ratio | 26 | C4 |
| 137 | [speed](file://~/COLD_STORAGE/cortex-config/workflows/speed.md) | **50.0** | code-block-ratio | 65 | C4 |

## Scripts

| # | Component | Exergy | Scoring | Lines | Confidence |
|---|-----------|--------|---------|-------|------------|
| 138 | [generate_telemetry.py](file://~/30_CORTEX/scripts/generate_telemetry.py) | **94.0** | AST | 74 | C5 |
| 139 | [synth_engine.py](file://~/30_CORTEX/scripts/synth_engine.py) | **93.3** | AST | 113 | C5 |
| 140 | [test_turbopuffer.py](file://~/30_CORTEX/scripts/test_turbopuffer.py) | **92.7** | AST | 66 | C5 |
| 141 | [pty_tmux_bridge.sh](file://~/30_CORTEX/scripts/pty_tmux_bridge.sh) | **92.0** | command-density | 160 | C4 |
| 142 | [swarm_duration_optimizer.py](file://~/30_CORTEX/scripts/swarm_duration_optimizer.py) | **91.7** | AST | 108 | C5 |
| 143 | [test_pruner.py](file://~/30_CORTEX/scripts/test_pruner.py) | **91.6** | AST | 42 | C5 |
| 144 | [test_osc.py](file://~/30_CORTEX/scripts/test_osc.py) | **91.5** | AST | 39 | C5 |
| 145 | [verify_hito_13.py](file://~/30_CORTEX/scripts/verify_hito_13.py) | **91.5** | AST | 74 | C5 |
| 146 | [scarcity_governor.py](file://~/30_CORTEX/scripts/scarcity_governor.py) | **91.1** | AST | 67 | C5 |
| 147 | [memory_bench.py](file://~/30_CORTEX/scripts/memory_bench.py) | **90.8** | AST | 214 | C5 |
| 148 | [sql_bench.py](file://~/30_CORTEX/scripts/sql_bench.py) | **90.7** | AST | 182 | C5 |
| 149 | [verify_10k_unleash.py](file://~/30_CORTEX/scripts/verify_10k_unleash.py) | **90.6** | AST | 64 | C5 |
| 150 | [generate_itia_registry.py](file://~/30_CORTEX/scripts/generate_itia_registry.py) | **90.2** | AST | 107 | C5 |
| 151 | [pii_firewall_poc.py](file://~/30_CORTEX/scripts/pii_firewall_poc.py) | **90.1** | AST | 146 | C5 |
| 152 | [swarm_100k_stress.py](file://~/30_CORTEX/scripts/swarm_100k_stress.py) | **89.6** | AST | 126 | C5 |
| 153 | [swarm_julio_audit.py](file://~/30_CORTEX/scripts/swarm_julio_audit.py) | **89.4** | AST | 143 | C5 |
| 154 | [prove_ax8_obsolescence.py](file://~/30_CORTEX/scripts/prove_ax8_obsolescence.py) | **89.3** | AST | 90 | C5 |
| 155 | [generate_sdks.sh](file://~/30_CORTEX/scripts/generate_sdks.sh) | **89.1** | command-density | 44 | C4 |
| 156 | [swarm_pacing_verifier.py](file://~/30_CORTEX/scripts/swarm_pacing_verifier.py) | **89.0** | AST | 135 | C5 |
| 157 | [exergy_sentinel.sh](file://~/30_CORTEX/scripts/exergy_sentinel.sh) | **88.6** | command-density | 28 | C4 |
| 158 | [stress_test_legion.py](file://~/30_CORTEX/scripts/stress_test_legion.py) | **87.9** | AST | 148 | C5 |
| 159 | [stripe_bootstrap.sh](file://~/30_CORTEX/scripts/stripe_bootstrap.sh) | **87.9** | command-density | 33 | C4 |
| 160 | [legion_strike.py](file://~/30_CORTEX/scripts/legion_strike.py) | **87.8** | AST | 125 | C5 |
| 161 | [export_substack_nodes.py](file://~/30_CORTEX/scripts/export_substack_nodes.py) | **87.4** | AST | 31 | C5 |
| 162 | [legal_ascension.py](file://~/30_CORTEX/scripts/legal_ascension.py) | **87.4** | AST | 102 | C5 |
| 163 | [reclaim_resources.sh](file://~/30_CORTEX/scripts/reclaim_resources.sh) | **87.4** | command-density | 57 | C4 |
| 164 | [diagnose.sh](file://~/30_CORTEX/scripts/diagnose.sh) | **87.3** | command-density | 22 | C4 |
| 165 | [dependabot_strike.py](file://~/30_CORTEX/scripts/dependabot_strike.py) | **86.9** | AST | 66 | C5 |
| 166 | [run_eviction_simulation.py](file://~/30_CORTEX/scripts/run_eviction_simulation.py) | **86.3** | AST | 177 | C5 |
| 167 | [cortex_wipe.py](file://~/30_CORTEX/scripts/cortex_wipe.py) | **86.1** | AST | 91 | C5 |
| 168 | [check_typing.py](file://~/30_CORTEX/scripts/check_typing.py) | **85.8** | AST | 57 | C5 |
| 169 | [generate_gdpr_payloads.py](file://~/30_CORTEX/scripts/generate_gdpr_payloads.py) | **85.7** | AST | 90 | C5 |
| 170 | [generate_endomorfismo_ontology.py](file://~/30_CORTEX/scripts/generate_endomorfismo_ontology.py) | **85.3** | AST | 417 | C5 |
| 171 | [build_semantic_trees.py](file://~/30_CORTEX/scripts/build_semantic_trees.py) | **85.0** | AST | 73 | C5 |
| 172 | [one_click_deploy.sh](file://~/30_CORTEX/scripts/one_click_deploy.sh) | **85.0** | command-density | 56 | C4 |
| 173 | [verify_bounty_exergy_extractor.py](file://~/30_CORTEX/scripts/verify_bounty_exergy_extractor.py) | **84.9** | AST | 126 | C5 |
| 174 | [consolidar_cortex.sh](file://~/30_CORTEX/scripts/consolidar_cortex.sh) | **84.8** | command-density | 66 | C4 |
| 175 | [prune_branches.py](file://~/30_CORTEX/scripts/prune_branches.py) | **84.8** | AST | 74 | C5 |
| 176 | [entropy_gate.py](file://~/30_CORTEX/scripts/entropy_gate.py) | **84.2** | AST | 107 | C5 |
| 177 | [calculate_migration_roi.py](file://~/30_CORTEX/scripts/calculate_migration_roi.py) | **84.1** | AST | 74 | C5 |
| 178 | [radar_daemon.sh](file://~/30_CORTEX/scripts/radar_daemon.sh) | **84.1** | command-density | 111 | C4 |
| 179 | [calculate_exergy_finance.py](file://~/30_CORTEX/scripts/calculate_exergy_finance.py) | **83.5** | AST | 69 | C5 |
| 180 | [master_exergy_singularity.sh](file://~/30_CORTEX/scripts/master_exergy_singularity.sh) | **82.4** | command-density | 25 | C4 |
| 181 | [swarm_10k_consolidate.py](file://~/30_CORTEX/scripts/swarm_10k_consolidate.py) | **81.6** | AST | 94 | C5 |
| 182 | [auto_radar.sh](file://~/30_CORTEX/scripts/auto_radar.sh) | **81.5** | command-density | 16 | C4 |
| 183 | [cortex_persist.sh](file://~/30_CORTEX/scripts/cortex_persist.sh) | **80.9** | command-density | 14 | C4 |
| 184 | [update_signatures.py](file://~/30_CORTEX/scripts/update_signatures.py) | **80.1** | AST | 119 | C5 |
| 185 | [calculate_token_pricing_sim.py](file://~/30_CORTEX/scripts/calculate_token_pricing_sim.py) | **79.9** | AST | 46 | C5 |
| 186 | [sovereign_pre_commit.py](file://~/30_CORTEX/scripts/sovereign_pre_commit.py) | **79.8** | AST | 148 | C5 |
| 187 | [ingest_target.py](file://~/30_CORTEX/scripts/ingest_target.py) | **79.6** | AST | 67 | C5 |
| 188 | [measure_flakiness.py](file://~/30_CORTEX/scripts/measure_flakiness.py) | **79.6** | AST | 73 | C5 |
| 189 | [get_random_feed.py](file://~/30_CORTEX/scripts/get_random_feed.py) | **79.4** | AST | 279 | C5 |
| 190 | [repo_health_changed.py](file://~/30_CORTEX/scripts/repo_health_changed.py) | **79.2** | AST | 117 | C5 |
| 191 | [migrate_cortex.py](file://~/30_CORTEX/scripts/migrate_cortex.py) | **78.9** | AST | 35 | C5 |
| 192 | [release_preflight.py](file://~/30_CORTEX/scripts/release_preflight.py) | **78.8** | AST | 82 | C5 |
| 193 | [ouroboros_absorb_runner.py](file://~/30_CORTEX/scripts/ouroboros_absorb_runner.py) | **78.3** | AST | 244 | C5 |
| 194 | [zero_debt.sh](file://~/30_CORTEX/scripts/zero_debt.sh) | **78.3** | command-density | 24 | C4 |
| 195 | [radar_cron.sh](file://~/30_CORTEX/scripts/radar_cron.sh) | **78.1** | command-density | 42 | C4 |
| 196 | [pronoic_transducer.py](file://~/30_CORTEX/scripts/pronoic_transducer.py) | **78.0** | AST | 147 | C5 |
| 197 | [cortex-boot.sh](file://~/30_CORTEX/scripts/cortex-boot.sh) | **77.9** | command-density | 29 | C4 |
| 198 | [update_memory_c5.py](file://~/30_CORTEX/scripts/update_memory_c5.py) | **77.0** | AST | 154 | C5 |
| 199 | [verify_cognitive_routing.py](file://~/30_CORTEX/scripts/verify_cognitive_routing.py) | **76.9** | AST | 30 | C5 |
| 200 | [maintenance_optimize_fts.py](file://~/30_CORTEX/scripts/maintenance_optimize_fts.py) | **76.6** | AST | 73 | C5 |
| 201 | [cortex_anergy_purge.py](file://~/30_CORTEX/scripts/cortex_anergy_purge.py) | **76.4** | AST | 96 | C5 |
| 202 | [ouroboros_prune.py](file://~/30_CORTEX/scripts/ouroboros_prune.py) | **76.0** | AST | 313 | C5 |
| 203 | [generate_cortex_ontology_subset.py](file://~/30_CORTEX/scripts/generate_cortex_ontology_subset.py) | **75.6** | AST | 100 | C5 |
| 204 | [osync_purge_local.py](file://~/30_CORTEX/scripts/osync_purge_local.py) | **75.6** | AST | 70 | C5 |
| 205 | [ship_gate.py](file://~/30_CORTEX/scripts/ship_gate.py) | **73.4** | AST | 487 | C5 |
| 206 | [audit_sql.py](file://~/30_CORTEX/scripts/audit_sql.py) | **72.8** | AST | 187 | C5 |
| 207 | [cortex_anergy_purge_hashlib.py](file://~/30_CORTEX/scripts/cortex_anergy_purge_hashlib.py) | **71.5** | AST | 98 | C5 |
| 208 | [triage_pytest_failures.py](file://~/30_CORTEX/scripts/triage_pytest_failures.py) | **65.6** | AST | 77 | C5 |
| 209 | [dependency_mapper.py](file://~/30_CORTEX/scripts/dependency_mapper.py) | **61.9** | AST | 67 | C5 |
| 210 | [babylon_crystallizer_agent.py](file://~/30_CORTEX/scripts/babylon_crystallizer_agent.py) | **60.8** | AST | 49 | C5 |
| 211 | [sovereign_pre_commit.sh](file://~/30_CORTEX/scripts/sovereign_pre_commit.sh) | **60.1** | command-density | 17 | C4 |

---

## Verification Matrices

### Primitives (`prims`)
1. **Exergy Gradient**: Rate of useful work output relative to total resource consumption.
2. **Thermodynamic Lane**: Designated execution path with strict resource and scheduling constraints.
3. **AST Isomorphism**: Structural equivalence of syntax trees, invariant under naming mutations.
4. **C5-REAL Validation**: Cryptographically verified, deterministic execution output.
5. **Consensus Quorum**: Byzantine fault tolerant agreement across modular agent networks.
6. **McCabe Density**: Cyclomatic complexity normalized per line of executable code.
7. **Code-Block Ratio**: Proportion of fenced code blocks in markdown documents.
8. **Import Density**: Number of imported symbols per executable line (glue-code indicator).
9. **Nesting Depth**: Maximum control-flow nesting level in a function body.
10. **Size Factor**: Executable line count normalized against minimum viable threshold.

### Invariants (`invt`)
1. **Absolute Attributability**: Every fact requires a cryptographically signed attribution token.
2. **No Silent Death**: Background workers must catch and propagate exceptions with trace.
3. **Single State Authority**: Persistent mutations go exclusively through the Saga write contract.
4. **Deterministic Scoring**: Same filesystem state always produces identical exergy rankings.
5. **PII Containment**: No absolute home directory paths appear in committed output.
6. **Discovery Completeness**: Every SKILL.md, workflow .md, and script on disk appears in inventory.
7. **Monotonic Ranking**: Output is strictly sorted by exergy DESC, name ASC.

### Anti-Patterns (`antip`)
1. **Limerence Loop**: Token expenditure on redundant iterations without state mutation.
2. **Context Leakage**: Merging metadata or credentials across tenant-isolated boundaries.
3. **Prose Padding**: Decorative conversational wrappers enclosing factual outputs.
4. **Ghost Components**: Inventory entries referencing paths that do not exist on disk.
5. **Static Freezing**: Hardcoded scores that never update with code changes.
6. **Walk Explosion**: Recursive directory traversal into node_modules or .git.

### Redundancies (`redun`)
1. **Fallback Consensus**: Multi-model routing when primary cognitive engines drift.
2. **Ledger Replication**: Redundant ledger records across local and network trust engines.
3. **Tombstone Retention**: Preserving scored entries for deprecated skills for historical audit.

### Adversarial Vectors (`reda`)
1. **Isomorphic Bypass**: Structurally identical malicious payloads via semantic transformations.
2. **Deadlock Induction**: Concurrent read-write locks designed to freeze SQLite event loops.
3. **Score Inflation**: Artificially reducing McCabe complexity by splitting into trivial functions.
4. **PII Exfiltration**: Embedding absolute paths in markdown links to leak host identity.

`SYS_ID borjamoskv`
