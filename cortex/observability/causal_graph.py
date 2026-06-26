# [C5-REAL] Exergy-Maximized
import json
import os
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, DefaultDict

CRONOS_LOG = os.path.expanduser("~/.gemini/config/skills/_metrics/cronos_memory.jsonl")
GRAPH_OUT = os.path.expanduser("~/.gemini/config/skills/_metrics/causal_graph.json")
GRAPH_REPORT = os.path.expanduser("~/.gemini/config/skills/_metrics/causal_graph_report.md")


def build_causal_graph():
    """
    Transforms execution logs into a Causal Graph.
    Nodes: Workflows
    Edges: Directed transitions (A -> B)
    Weights: Frequency, Avg Latency (seconds), Transfer Score (combines exergy)
    """
    if not os.path.exists(CRONOS_LOG):
        print(f"No CRONOS log found at {CRONOS_LOG}")
        return

    records = []
    with open(CRONOS_LOG) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Filter only Executed/Completed
    records = [r for r in records if r.get("state") in ("EXECUTED", "COMPLETED")]
    # Sort by timestamp to ensure chronological order
    records.sort(key=lambda x: x.get("timestamp", ""))

    class EdgeMetrics(TypedDict):
        count: int
        latencies: list[float]
        scores_from: list[Decimal]
        scores_to: list[Decimal]

    graph: DefaultDict[str, DefaultDict[str, EdgeMetrics]] = defaultdict(
        lambda: defaultdict(
            lambda: {"count": 0, "latencies": [], "scores_from": [], "scores_to": []}
        )
    )

    nodes = set()

    for i in range(len(records) - 1):
        r_from = records[i]
        r_to = records[i + 1]

        wf_from = r_from["workflow"]
        wf_to = r_to["workflow"]

        nodes.add(wf_from)
        nodes.add(wf_to)

        # Parse timestamps to compute latency
        fmt_patterns = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"]
        t_from = None
        t_to = None

        for fmt in fmt_patterns:
            try:
                t_from = datetime.strptime(r_from["timestamp"], fmt)
                break
            except (ValueError, TypeError):
                continue

        for fmt in fmt_patterns:
            try:
                t_to = datetime.strptime(r_to["timestamp"], fmt)
                break
            except (ValueError, TypeError):
                continue

        latency_sec = 0
        if t_from and t_to:
            latency_sec = max(0, (t_to - t_from).total_seconds())

        edge = graph[wf_from][wf_to]
        edge["count"] += 1
        edge["latencies"].append(latency_sec)
        edge["scores_from"].append(Decimal(str(r_from.get("execution_score", 0))))
        edge["scores_to"].append(Decimal(str(r_to.get("execution_score", 0))))

    # Compile Final Edges
    final_graph = {"nodes": list(nodes), "edges": []}
    report_lines = [
        "# CORTEX Causal Graph Engine v1.0",
        f"> **Reality Level: C5-REAL** | Compiled: {datetime.utcnow().isoformat()}Z",
        "",
        "## Execution Topology",
        "Model predicts future execution chains based on historical exergy transfer.",
        "",
        "| Source Node | Target Node | Transitions | Avg Latency | Transfer Exergy |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]

    edges_list = []
    for wf_from, targets in graph.items():
        for wf_to, metrics in targets.items():
            count = metrics["count"]
            avg_lat = sum(metrics["latencies"]) / count if count > 0 else 0
            
            if count > 0:
                avg_score_to = sum(metrics["scores_to"]) / Decimal(count)
            else:
                avg_score_to = Decimal("0")

            # Transfer Exergy heuristically combines the probability of transition with the destination's execution score
            transfer_exergy = round(Decimal(count) * avg_score_to, 2)

            edges_list.append(
                {
                    "source": wf_from,
                    "target": wf_to,
                    "weight": count,
                    "avg_latency_sec": round(avg_lat, 2),
                    "transfer_exergy": transfer_exergy,
                }
            )

    # Sort edges by transfer_exergy descending
    edges_list.sort(key=lambda x: x["transfer_exergy"], reverse=True)
    final_graph["edges"] = edges_list

    for e in edges_list:
        lat_str = f"{e['avg_latency_sec']:.1f}s"
        report_lines.append(
            f"| `{e['source']}` | `{e['target']}` | {e['weight']} | {lat_str} | {e['transfer_exergy']} |"
        )

    report_lines.extend(
        [
            "",
            "## Next Step: Autonomous Reproduction",
            "If `Transfer Exergy` exceeds threshold, the system should pre-warm or automatically trigger the Target Node upon completion of the Source Node.",
        ]
    )

    with open(GRAPH_OUT, "w", encoding="utf-8") as f:
        json.dump(final_graph, f, indent=2)

    with open(GRAPH_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"Causal graph generated: {len(nodes)} nodes, {len(edges_list)} edges.")


if __name__ == "__main__":
    build_causal_graph()
