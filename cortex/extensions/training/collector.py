from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cortex.extensions.episodic.base import Episode

logger = logging.getLogger("cortex.extensions.training")


@dataclass
class Action:
    tool: str
    input: Any
    observation: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Trajectory:
    session_id: str
    project: str
    issue_description: str
    actions: list[Action] = field(default_factory=list)
    outcome: str = "unknown"  # success, failure, partial
    reward: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class TrajectoryCollector:
    """
    Collects agent trajectories from CORTEX episodes for training purposes.
    Inspired by Skywork and OpenHands methodologies.
    """

    def __init__(self, episodic_memory: Any):
        self.episodic = episodic_memory

    async def collect_session_trajectory(self, session_id: str) -> Trajectory | None:
        """
        Reconstructs a trajectory for a specific session by grouping episodes.
        """
        episodes: list[Episode] = await self.episodic.get_session_timeline(session_id)
        if not episodes:
            return None

        project = episodes[0].project or "unknown"
        issue_description = self._extract_issue_description(episodes)

        actions, metadata = self._process_episodes(episodes)
        outcome = self._determine_outcome(episodes)

        return Trajectory(
            session_id=session_id,
            project=project,
            issue_description=issue_description,
            actions=[a for a in actions if a.tool != "unknown"],
            outcome=outcome,
            metadata=metadata,
        )

    def _extract_issue_description(self, episodes: list[Episode]) -> str:
        """Finds the first instruction or intent."""
        for ep in episodes:
            if ep.event_type == "decision" and ep.intent:
                return ep.intent
        return episodes[0].content

    def _process_episodes(self, episodes: list[Episode]) -> tuple[list[Action], dict[str, Any]]:
        """Processes episodes to extract actions and aggregate metadata."""
        actions: list[Action] = []
        current_action: Action | None = None
        metadata: dict[str, Any] = {}

        for ep in episodes:
            # Aggregate all metadata from all episodes
            if ep.meta:
                metadata.update(ep.meta)

            if ep.event_type == "decision":
                if current_action:
                    actions.append(current_action)

                current_action = Action(
                    tool=ep.meta.get("tool", "unknown"),
                    input=ep.meta.get("input", {}),
                    timestamp=datetime.fromisoformat(ep.created_at),
                )

            elif ep.event_type in ("discovery", "insight", "error"):
                if current_action and not current_action.observation:
                    prefix = "ERROR: " if ep.event_type == "error" else ""
                    current_action.observation = f"{prefix}{ep.content}"
                    actions.append(current_action)
                    current_action = None

        if current_action:
            actions.append(current_action)

        return actions, metadata

    def _determine_outcome(self, episodes: list[Episode]) -> str:
        """Determine outcome from milestone or last episodes."""
        for ep in reversed(episodes):
            if ep.event_type == "milestone":
                return "success" if "success" in ep.content.lower() else "partial"
            if ep.event_type == "error":
                return "failure"
        return "unknown"

    def format_for_sft(self, trajectories: list[Trajectory], format_type: str = "sharegpt") -> str:
        """
        Formats trajectories for Supervised Fine-Tuning.
        Supports 'sharegpt' (Qwen2.5 compatible) and 'openai' formats.
        """
        formatted_data = []
        for traj in trajectories:
            if not traj.actions:
                continue

            conversation = [
                {
                    "from": "system",
                    "value": f"Context: {traj.project}\nIssue: {traj.issue_description}",
                }
            ]

            for action in traj.actions:
                conversation.append(
                    {"from": "human", "value": f"Action: {action.tool}({json.dumps(action.input)})"}
                )
                if action.observation:
                    conversation.append({"from": "gpt", "value": action.observation})

            if format_type == "sharegpt":
                formatted_data.append({"conversations": conversation})
            elif format_type == "openai":
                formatted_data.append(
                    {
                        "messages": [
                            {
                                "role": "system"
                                if c["from"] == "system"
                                else ("user" if c["from"] == "human" else "assistant"),
                                "content": c["value"],
                            }
                            for c in conversation
                        ]
                    }
                )

        return json.dumps(formatted_data, indent=2)
