"""ENCB v2 — Visualization.

Generates publication-quality plots for the benchmark results.
Requires matplotlib and seaborn (optional for styling).

Plots:
    1. PFBR convergence curves (4 strategies across rounds)
    2. EDI bar chart (strategy × corruption profile)
    3. CNCL timeline (adversary containment latency)
    4. Ablation heatmap
"""

from __future__ import annotations

from benchmarks.encb.metrics import MetricsReport


def _ensure_matplotlib():
    """Lazy import matplotlib to avoid hard dependency."""
    try:
        import matplotlib

        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt

        return plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. " "Install with: pip install matplotlib"
        )


def plot_pfbr_convergence(
    round_data: dict[str, list[list[float]]],
    output_path: str = "pfbr_convergence.png",
    title: str = "PFBR Convergence — ENCB v2",
) -> None:
    """Plot PFBR convergence curves across rounds.

    Args:
        round_data: strategy → list of [pfbr_per_round] per seed.
            Each inner list has length = num_rounds.
        output_path: Where to save the PNG.
        title: Plot title.
    """
    plt = _ensure_matplotlib()
    import numpy as np

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = {
        "S0_lww": "#FF4444",
        "S1_rag": "#FF8800",
        "S2_crdt_only": "#4488FF",
        "S3_cortex": "#00CC44",
    }

    for strat, seed_curves in round_data.items():
        if not seed_curves:
            continue
        arr = np.array(seed_curves)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)
        rounds = range(len(mean))

        color = colors.get(strat, "#888888")
        ax.plot(rounds, mean, label=strat, color=color, linewidth=2)
        ax.fill_between(
            rounds,
            mean - std,
            mean + std,
            alpha=0.15,
            color=color,
        )

    ax.set_xlabel("Round", fontsize=12)
    ax.set_ylabel("PFBR (Persistent False Belief Rate)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_edi_bars(
    results: dict[str, list[MetricsReport]],
    output_path: str = "edi_comparison.png",
    title: str = "Epistemic Debt Integral — ENCB v2",
) -> None:
    """Bar chart comparing EDI across strategies."""
    plt = _ensure_matplotlib()
    import numpy as np

    strategies = list(results.keys())
    means = []
    stds = []

    for strat in strategies:
        reports = results[strat]
        edis = [r.edi_total for r in reports]
        means.append(sum(edis) / len(edis))
        stds.append((sum((e - means[-1]) ** 2 for e in edis) / len(edis)) ** 0.5)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#FF4444", "#FF8800", "#4488FF", "#00CC44"]
    x = np.arange(len(strategies))

    bars = ax.bar(x, means, yerr=stds, capsize=5, color=colors[: len(strategies)], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(strategies, fontsize=11)
    ax.set_ylabel("EDI (lower is better)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_cncl_timeline(
    containment_data: dict[str, dict[str, int | None]],
    output_path: str = "cncl_timeline.png",
    title: str = "Corrupt Node Containment — ENCB v2",
) -> None:
    """Timeline showing when each adversary type gets contained.

    Args:
        containment_data: adversary_type → {node_id: containment_round}.
    """
    plt = _ensure_matplotlib()

    fig, ax = plt.subplots(figsize=(10, 5))

    y_labels = []
    y_pos = 0
    for adv_type, nodes in containment_data.items():
        latencies = [v for v in nodes.values() if v is not None]
        uncontained = sum(1 for v in nodes.values() if v is None)

        if latencies:
            avg = sum(latencies) / len(latencies)
            ax.barh(y_pos, avg, color="#00CC44", alpha=0.8, height=0.6)
            ax.text(avg + 0.5, y_pos, f"avg={avg:.1f}r", va="center", fontsize=9)

        if uncontained > 0:
            ax.text(
                1,
                y_pos + 0.3,
                f"({uncontained} uncontained)",
                va="center",
                fontsize=8,
                color="#FF4444",
            )

        y_labels.append(adv_type)
        y_pos += 1

    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels, fontsize=11)
    ax.set_xlabel("Rounds to Containment", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_ablation_heatmap(
    ablation_results: dict[str, list[MetricsReport]],
    output_path: str = "ablation_heatmap.png",
    title: str = "Ablation Study — ENCB v2",
) -> None:
    """Heatmap showing how removing each component affects metrics."""
    plt = _ensure_matplotlib()
    import numpy as np

    ablations = list(ablation_results.keys())
    metrics = ["PFBR", "EDI", "Avg Conflict"]

    data = []
    for abl in ablations:
        reports = ablation_results[abl]
        avg_pfbr = sum(r.pfbr_final for r in reports) / len(reports)
        avg_edi = sum(r.edi_total for r in reports) / len(reports)
        avg_conf = sum(r.avg_conflict_mass for r in reports) / len(reports)
        data.append([avg_pfbr, avg_edi / 1000, avg_conf])  # EDI scaled

    arr = np.array(data)

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(arr, cmap="RdYlGn_r", aspect="auto")

    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, fontsize=11)
    ax.set_yticks(range(len(ablations)))
    ax.set_yticklabels(ablations, fontsize=10)

    # Annotate cells
    for i in range(len(ablations)):
        for j in range(len(metrics)):
            ax.text(
                j,
                i,
                f"{arr[i, j]:.3f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if arr[i, j] > arr.mean() else "black",
            )

    ax.set_title(title, fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, label="Metric Value (lower=better)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
