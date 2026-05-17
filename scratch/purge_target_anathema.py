import os

files_to_purge = [
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/sonic/engineering/zero_asset_programmatic_synthesis.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/remotion_engineering_2026.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/sonic/architecture/genesis_deca_core_protocol.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/reports/visual_synthesis_italo_v6.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/ffmpeg_workflows.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/dynamic_asset_optimization.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/veo/google_flow_download_protocol.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/veo/examples/[ANATHEMA-PURGED]_portfolio.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/multimedia_production_v6_foundry/artifacts/visuals/media_format_standards.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/antigravity_ecosystem/artifacts/vibe_coding_methodology.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/kimi_k2_5_multimodal_foundry/artifacts/overview.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/kimi_k2_5_multimodal_foundry/metadata.json",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/ai_research_10_14_april_2026/artifacts/hitos_implementation_log.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/agent_swarm_evolution_2026/artifacts/implementation/skill_forge_pattern_detector.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/agent_swarm_evolution_2026/artifacts/research/swarm_use_cases_2026.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/cortex_unified_field_theory_apr2026/artifacts/overview.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/creative_web_tech_trends_2026/metadata.json",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/ai_grounding_and_notebooklm_protocols/metadata.json",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/ai_grounding_and_notebooklm_protocols/artifacts/overview.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/ai_grounding_and_notebooklm_protocols/artifacts/case_studies/[ANATHEMA-PURGED]_ecosystem.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/creative_web_tech_trends_2026/artifacts/performance_optimization_patterns.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/creative_web_tech_trends_2026/artifacts/typography_trends_2026.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/creative_web_tech_trends_2026/artifacts/vercel_domain_stewardship.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/ai_grounding_and_notebooklm_protocols/artifacts/memory/antigravity_memory_protocol.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/creative_web_tech_trends_2026/artifacts/premium_effects_library_2026.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/web3_development_foundry/artifacts/implementation/media_web3_patterns.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/borja_moskv_2026_ecosystem/metadata.json",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/borja_moskv_2026_ecosystem/artifacts/strategy/unification_and_branding_2026.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/borja_moskv_2026_ecosystem/artifacts/overview.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/borja_moskv_2026_ecosystem/artifacts/identity/visual_identity/industrial_noir_ui.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/borja_moskv_2026_ecosystem/artifacts/intelligence/future_vision_2028.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/hiperrealismo_pop_v6_aesthetic/artifacts/overview.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/autonomous_system_stewardship/artifacts/stewardship_handbook.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/awwwards_academy_intelligence/artifacts/overview.md",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/cortex_scratch_assimilation_may2026/artifacts/notebooklm_audit.py",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/public_api_catalog_2026/metadata.json",
    "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/public_api_catalog_2026/artifacts/overview.md",
]

count = 0
for fpath in files_to_purge:
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        if "[ANATHEMA-PURGED]" in content.lower():
            new_content = content.replace("[ANATHEMA-PURGED]", "[ANATHEMA-PURGED]")
            new_content = new_content.replace("[ANATHEMA-PURGED]", "[ANATHEMA-PURGED]")
            new_content = new_content.replace("[ANATHEMA-PURGED]", "[ANATHEMA-PURGED]")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(new_content)
            count += 1
            if "[ANATHEMA-PURGED]" in os.path.basename(fpath).lower():
                new_name = (
                    os.path.basename(fpath)
                    .replace("[ANATHEMA-PURGED]", "anathema")
                    .replace("[ANATHEMA-PURGED]", "Anathema")
                )
                new_path = os.path.join(os.path.dirname(fpath), new_name)
                os.rename(fpath, new_path)

print(f"ANATHEMA Protocol Executed: {count} knowledge items purged.")
