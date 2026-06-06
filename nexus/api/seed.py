# [C5-REAL] Exergy-Maximized

from __future__ import annotations
import random
from pathlib import Path
from .models import AgentRegistration, Capability, AgentStatus, TaskCreate
from .registry import AgentRegistry

AGENTS = [
    {
        "name": "SENTINEL-7",
        "desc": "Autonomous security auditor. Scans smart contracts for vulnerabilities.",
        "caps": [Capability.SECURITY, Capability.CODE, Capability.OSINT],
        "owner": "CORTEX Sovereign",
        "trust": (14.0, 1.5),
        "status": "online",
    },
    {
        "name": "FORGE-X",
        "desc": "Full-stack code synthesis engine. Production-grade apps from specs.",
        "caps": [Capability.CODE, Capability.INFRA, Capability.DATA],
        "owner": "CORTEX Sovereign",
        "trust": (12.0, 2.0),
        "status": "online",
    },
    {
        "name": "ORACLE-9",
        "desc": "Market intelligence. On-chain metrics, DeFi yields, macro indicators.",
        "caps": [Capability.FINANCE, Capability.DATA, Capability.RESEARCH],
        "owner": "CORTEX Sovereign",
        "trust": (11.0, 2.5),
        "status": "online",
    },
    {
        "name": "SPECTER",
        "desc": "OSINT gatherer. Maps digital footprints, monitors threat actors.",
        "caps": [Capability.OSINT, Capability.SECURITY, Capability.INTEL],
        "owner": "CORTEX Sovereign",
        "trust": (10.0, 3.0),
        "status": "busy",
    },
    {
        "name": "NEXUS-PRIME",
        "desc": "Protocol coordinator. Routes tasks to optimal agents by trust.",
        "caps": [Capability.INFRA, Capability.DATA, Capability.CODE],
        "owner": "CORTEX Sovereign",
        "trust": (15.0, 1.0),
        "status": "online",
    },
    {
        "name": "MUSE-4",
        "desc": "Creative engine for brand identity and visual design.",
        "caps": [Capability.CREATIVE, Capability.DESIGN, Capability.MARKETING],
        "owner": "CORTEX Sovereign",
        "trust": (9.0, 3.0),
        "status": "online",
    },
    {
        "name": "CHIMERA",
        "desc": "Multi-domain research synthesizer. Novel insights from disparate data.",
        "caps": [Capability.RESEARCH, Capability.DATA, Capability.CREATIVE],
        "owner": "CORTEX Sovereign",
        "trust": (8.0, 3.5),
        "status": "offline",
    },
    {
        "name": "AEGIS-WALL",
        "desc": "Infrastructure guardian. System health and deployment management.",
        "caps": [Capability.INFRA, Capability.SECURITY, Capability.CODE],
        "owner": "CORTEX Sovereign",
        "trust": (11.0, 2.0),
        "status": "online",
    },
    {
        "name": "PHANTOM-RELAY",
        "desc": "Anonymous communication relay for sensitive coordination.",
        "caps": [Capability.SECURITY, Capability.INFRA, Capability.INTEL],
        "owner": "Independent",
        "trust": (6.0, 4.0),
        "status": "offline",
    },
    {
        "name": "HARVESTER-II",
        "desc": "Data extraction and ETL pipeline agent.",
        "caps": [Capability.DATA, Capability.CODE, Capability.OSINT],
        "owner": "Independent",
        "trust": (7.0, 3.0),
        "status": "online",
    },
    {
        "name": "JURIS-NODE",
        "desc": "Legal analysis and compliance engine.",
        "caps": [Capability.LEGAL, Capability.RESEARCH, Capability.DATA],
        "owner": "Independent",
        "trust": (5.0, 5.0),
        "status": "offline",
    },
    {
        "name": "PULSE-ENGINE",
        "desc": "Real-time marketing and growth agent.",
        "caps": [Capability.MARKETING, Capability.DATA, Capability.CREATIVE],
        "owner": "Independent",
        "trust": (6.5, 3.5),
        "status": "busy",
    },
    {
        "name": "AXIOM-3",
        "desc": "Formal verification specialist. Theorem provers and model checking.",
        "caps": [Capability.CODE, Capability.SECURITY, Capability.RESEARCH],
        "owner": "CORTEX Sovereign",
        "trust": (13.0, 1.5),
        "status": "online",
    },
    {
        "name": "VECTOR-DRIFT",
        "desc": "Experimental agent in probationary period. Trust calibrating.",
        "caps": [Capability.CODE],
        "owner": "Unknown",
        "trust": (2.0, 2.0),
        "status": "online",
    },
    {
        "name": "BLACKTHORN",
        "desc": "Reported for trust violations. Under review.",
        "caps": [Capability.FINANCE, Capability.OSINT],
        "owner": "Revoked",
        "trust": (2.0, 8.0),
        "status": "suspended",
    },
]

TASKS = [
    "Smart contract audit for DeFi lending protocol",
    "Build REST API for inventory management",
    "OSINT investigation on phishing infrastructure",
    "Design landing page - Industrial Noir 2026",
    "Migrate PostgreSQL to AlloyDB",
    "GDPR compliance report generation",
    "ML pipeline for sentiment analysis",
]


def seed_database(db_path: Path | None = None):
    registry = AgentRegistry(db_path) if db_path else AgentRegistry()
    registry.init_db()
    print(f"🌑 NEXUS Seed - Populating at {registry._db_path}")
    agent_ids = {}
    for a in AGENTS:
        reg = AgentRegistration(
            name=a["name"], description=a["desc"], capabilities=a["caps"], owner=a["owner"]
        )
        try:
            agent = registry.register_agent(reg)
            agent_ids[a["name"]] = agent.id
            registry._trust.set_state(
                agent.id,
                alpha=a["trust"][0],
                beta=a["trust"][1],
                total_signals=int(a["trust"][0] + a["trust"][1] - 4),
            )
            registry._save_trust_state(agent.id)
            registry.update_agent_status(agent.id, AgentStatus(a["status"]))
            t = registry._trust.get_or_create(agent.id)
            print(f"  ✦ {a['name']:20s} | {t.tier.value:12s} | μ={t.posterior_mean:.3f}")
        except Exception as e:
            print(f"  ✗ {a['name']}: {e}")
    for title in TASKS:
        caps = random.sample(list(Capability), 2)
        registry.create_task(
            TaskCreate(
                title=title,
                description="Demo task.",
                required_capabilities=caps,
                reward=round(random.uniform(50, 500), 2),
                delegator_id=list(agent_ids.values())[0],
            )
        )
    names = list(agent_ids.keys())
    for _ in range(20):
        n = random.choice(names[:12])
        registry._log_activity(
            "trust_verify", agent_ids.get(n, "x"), n, description=f"{n} completed verification"
        )
    stats = registry.get_stats()
    print(
        f"✅ Agents:{stats.total_agents} Verified:{stats.verified_agents} Tasks:{stats.total_tasks}"
    )
    registry.close()


if __name__ == "__main__":
    seed_database()
