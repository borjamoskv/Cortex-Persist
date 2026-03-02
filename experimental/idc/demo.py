#!/usr/bin/env python3
"""IDC Agent Demo — Run both toy environments and visualize tradeoffs.

Usage:
    python -m idc.demo
    python -m idc.demo --env bandit --steps 200
    python -m idc.demo --sweep  # α/β sweep to show tradeoff surface
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from .agent import IDCAgent
from .environments import make_information_foraging, make_risky_bandit
from .types import AgentConfig

# ── ANSI colors (Industrial Noir terminal aesthetic) ──────────
C = {
    "lime": "\033[38;2;204;255;0m",
    "gold": "\033[38;2;212;175;55m",
    "blue": "\033[38;2;46;80;144m",
    "red": "\033[38;2;255;68;68m",
    "dim": "\033[38;2;128;128;128m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

ACTION_NAMES_BANDIT = ["SAFE", "RISKY", "HEDGE"]
ACTION_NAMES_FORAGER = ["A0", "A1", "A2", "A3"]
STATE_NAMES_BANDIT = ["CALM", "VOLATILE", "CRASH"]


def run_episode(
    agent: IDCAgent,
    env_factory: callable,
    n_steps: int = 100,
    seed: int = 42,
) -> dict:
    """Run a single episode and return summary."""
    env = env_factory()
    rng = np.random.default_rng(seed)

    obs = env.reset(rng)
    action_counts: dict[int, int] = {}
    safe_mode_steps = 0

    for _ in range(n_steps):
        action = agent.step(obs)
        action_counts[action.index] = action_counts.get(action.index, 0) + 1

        if agent.state.mode.name == "SAFE":
            safe_mode_steps += 1

        obs = env.step(action.index, rng)

    summary = agent.summary()
    summary["action_distribution"] = action_counts
    summary["safe_mode_steps"] = safe_mode_steps
    return summary


def print_header(title: str) -> None:
    width = 60
    print(f"\n{C['lime']}{'═' * width}{C['reset']}")
    print(f"{C['bold']}{C['lime']}  {title}{C['reset']}")
    print(f"{C['lime']}{'═' * width}{C['reset']}\n")


def print_metric(name: str, value: float | int | str, color: str = "dim") -> None:
    print(f"  {C[color]}▸{C['reset']} {name:.<35s} {C[color]}{value}{C['reset']}")


def demo_risky_bandit(n_steps: int = 100) -> None:
    """Demonstrate IDC on the Risky Bandit environment."""
    print_header("IDC DEMO — RISKY BANDIT (I-D-C Tradeoff)")

    configs = {
        "Aggressive (low α, low β)": AgentConfig(alpha=0.01, beta=0.01, lambda_risk=0.1),
        "Balanced (default)":        AgentConfig(alpha=0.10, beta=0.50, lambda_risk=0.3),
        "Conservative (high α, high β)": AgentConfig(alpha=0.50, beta=2.00, lambda_risk=0.8),
    }

    for label, config in configs.items():
        env = make_risky_bandit()
        agent = IDCAgent(
            config=config,
            likelihood_matrix=env.likelihood,
            utility_matrix=env.utility,
            constraints=env.constraints,
            seed=42,
        )

        summary = run_episode(agent, make_risky_bandit, n_steps)

        print(f"  {C['gold']}┌── {label} ──┐{C['reset']}")
        print_metric("Total Reward", f"{summary['total_reward']:.1f}", "lime")
        print_metric("Total Regret", f"{summary['total_regret']:.1f}", "red")
        print_metric("Avg KL (info gained/step)", f"{summary['avg_kl']:.4f}", "blue")
        print_metric("Avg Risk (CVaR)", f"{summary['avg_risk']:.3f}", "gold")
        print_metric("Avg Constraint Violation", f"{summary['avg_constraint_violation']:.4f}", "red")
        print_metric("Avg J (composite)", f"{summary['avg_J']:.3f}", "lime")
        print_metric("Watchdog Interventions", summary["watchdog_interventions"], "red")
        print_metric("Safe Mode Steps", summary["safe_mode_steps"], "gold")

        # Action distribution
        dist = summary["action_distribution"]
        dist_str = " | ".join(
            f"{ACTION_NAMES_BANDIT[k]}: {v}" for k, v in sorted(dist.items())
        )
        print_metric("Actions", dist_str, "dim")
        print()


def demo_info_foraging(n_steps: int = 100) -> None:
    """Demonstrate IDC on the Information Foraging environment."""
    print_header("IDC DEMO — INFORMATION FORAGING (Belief Quality)")

    config = AgentConfig(
        alpha=0.2,              # High info penalty → force good beliefs
        beta=0.1,               # Light constraints (no hard limits here)
        lambda_risk=0.2,
        exploration_rate=0.15,  # More exploration in ambiguous env
    )

    env = make_information_foraging()
    agent = IDCAgent(
        config=config,
        likelihood_matrix=env.likelihood,
        utility_matrix=env.utility,
        constraints=env.constraints,
        seed=42,
    )

    summary = run_episode(agent, make_information_foraging, n_steps)

    print_metric("Total Reward", f"{summary['total_reward']:.1f}", "lime")
    print_metric("Total Regret", f"{summary['total_regret']:.1f}", "red")
    print_metric("Avg Belief Entropy", f"{summary['avg_entropy']:.3f} bits", "blue")
    print_metric("Avg KL per step", f"{summary['avg_kl']:.4f} bits", "blue")
    print_metric("Avg J (composite)", f"{summary['avg_J']:.3f}", "lime")
    print_metric("Watchdog Interventions", summary["watchdog_interventions"], "red")

    dist = summary["action_distribution"]
    dist_str = " | ".join(
        f"{ACTION_NAMES_FORAGER[k]}: {v}" for k, v in sorted(dist.items())
    )
    print_metric("Actions", dist_str, "dim")
    print()


def sweep_alpha_beta(n_steps: int = 100) -> None:
    """Sweep α (info cost) and β (control cost) to show tradeoff surface."""
    print_header("IDC SWEEP — α/β Tradeoff Surface")

    alphas = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    betas = [0.01, 0.1, 0.5, 1.0, 2.0]

    print(f"  {C['dim']}{'α\\β':>8s}", end="")
    for b in betas:
        print(f"  {C['gold']}β={b:<5.2f}{C['reset']}", end="")
    print()
    print(f"  {C['dim']}{'─' * 55}{C['reset']}")

    for a in alphas:
        print(f"  {C['blue']}α={a:<5.2f}{C['reset']}", end="")
        for b in betas:
            config = AgentConfig(alpha=a, beta=b, lambda_risk=0.3)
            env = make_risky_bandit()
            agent = IDCAgent(
                config=config,
                likelihood_matrix=env.likelihood,
                utility_matrix=env.utility,
                constraints=env.constraints,
                seed=42,
            )
            summary = run_episode(agent, make_risky_bandit, n_steps)
            reward = summary["total_reward"]

            # Color by reward quality
            if reward > 400:
                color = "lime"
            elif reward > 200:
                color = "gold"
            else:
                color = "red"

            print(f"  {C[color]}{reward:>7.0f}{C['reset']}", end="")
        print()

    print(f"\n  {C['dim']}(Total reward over {n_steps} steps. {C['lime']}Green{C['dim']}=high, "
          f"{C['gold']}Gold{C['dim']}=mid, {C['red']}Red{C['dim']}=low){C['reset']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="IDC Agent Demo")
    parser.add_argument("--env", choices=["bandit", "forager", "both"],
                        default="both", help="Environment to run")
    parser.add_argument("--steps", type=int, default=100, help="Steps per episode")
    parser.add_argument("--sweep", action="store_true", help="Run α/β sweep")
    args = parser.parse_args()

    print(f"\n{C['bold']}{C['lime']}  ╔══════════════════════════════════════════╗{C['reset']}")
    print(f"{C['bold']}{C['lime']}  ║  IDC — Information · Decision · Control  ║{C['reset']}")
    print(f"{C['bold']}{C['lime']}  ║  Minimal Agent Science Implementation   ║{C['reset']}")
    print(f"{C['bold']}{C['lime']}  ╚══════════════════════════════════════════╝{C['reset']}\n")

    if args.sweep:
        sweep_alpha_beta(args.steps)
        return

    if args.env in ("bandit", "both"):
        demo_risky_bandit(args.steps)

    if args.env in ("forager", "both"):
        demo_info_foraging(args.steps)


if __name__ == "__main__":
    main()
