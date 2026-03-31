from dataclasses import dataclass, field

@dataclass
class MissionProfile:
    name: str
    target_repo: str
    agent_density: int
    focus_areas: list[str]
    priority: int = 1

@dataclass
class ForensicStrikeConfig:
    MAX_SWARM_AGENTS: int = 10000
    STRIKE_ID: str = "FORENSIC-STRIKE-V1"
    
    MISSIONS: list[MissionProfile] = field(default_factory=lambda: [
        MissionProfile(
            name="Legion-Sky",
            target_repo="sky-ecosystem/dss-allocator",
            agent_density=4000,
            focus_areas=["AllocatorVault.sol", "Swapper.sol", "USDS_Minting"],
            priority=1
        ),
        MissionProfile(
            name="Legion-Lido",
            target_repo="lidofinance/lido-dao",
            agent_density=3000,
            focus_areas=["WithdrawalQueue.sol", "OracleManipulation", "RebaseErrors"],
            priority=2
        ),
        MissionProfile(
            name="Legion-SSV",
            target_repo="ssv-network/ssv-contracts",
            agent_density=3000,
            focus_areas=["ConsensusLayer", "NodeRegistration", "BalanceAccounting"],
            priority=3
        )
    ])

STRIKE_V1 = ForensicStrikeConfig()
