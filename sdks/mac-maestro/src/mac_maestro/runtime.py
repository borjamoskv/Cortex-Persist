from __future__ import annotations

from .backends.protocol import BackendProtocol
from .errors import MacMaestroError
from .matcher import find_best_match
from .models import ClickAction, ElementSelector, PressAction, RunTrace, TypeAction, UIAction
from .safety import SafetyPolicy
from .trace import TraceCollector


class MacMaestro:
    def __init__(
        self,
        bundle_id: str,
        backend: BackendProtocol,
        safety_policy: SafetyPolicy | None = None,
    ) -> None:
        self.bundle_id = bundle_id
        self.backend = backend
        self.safety_policy = safety_policy or SafetyPolicy()

    def run(self, actions: list[UIAction]) -> RunTrace:
        trace = TraceCollector()

        try:
            for idx, action in enumerate(actions):
                action_kind = getattr(action, "kind", action.__class__.__name__)

                root = self.backend.snapshot(self.bundle_id)
                trace.add(
                    phase="snapshot",
                    action_index=idx,
                    action_kind=action_kind,
                    message="Snapshot captured",
                    payload={"bundle_id": self.bundle_id},
                )

                self.safety_policy.validate(action)
                trace.add(
                    phase="safety",
                    action_index=idx,
                    action_kind=action_kind,
                    message="Safety check passed",
                )

                match action:
                    case ClickAction():
                        selector = ElementSelector(**action.model_dump(exclude={"kind"}))
                        matched = find_best_match(root, selector)
                        trace.add(
                            phase="match",
                            action_index=idx,
                            action_kind=action_kind,
                            message="Element matched",
                            payload=matched.model_dump(mode="json"),
                        )
                        self.backend.click(matched)
                        trace.add(
                            phase="execute",
                            action_index=idx,
                            action_kind=action_kind,
                            message="Click executed",
                            payload={"element_id": matched.element_id},
                        )

                    case TypeAction():
                        matched = None
                        if action.target is not None:
                            matched = find_best_match(root, action.target)
                            trace.add(
                                phase="match",
                                action_index=idx,
                                action_kind=action_kind,
                                message="Type target matched",
                                payload=matched.model_dump(mode="json"),
                            )
                        self.backend.type_text(action, matched)
                        trace.add(
                            phase="execute",
                            action_index=idx,
                            action_kind=action_kind,
                            message="Type executed",
                            payload={"chars": len(action.text)},
                        )

                    case PressAction():
                        self.backend.press(action)
                        trace.add(
                            phase="execute",
                            action_index=idx,
                            action_kind=action_kind,
                            message="Key press executed",
                            payload={
                                "key_code": action.key_code,
                                "modifiers": [m.value for m in action.modifiers],
                            },
                        )

                trace.add(
                    phase="result",
                    action_index=idx,
                    action_kind=action_kind,
                    message="Action completed",
                )

            return trace.success()

        except MacMaestroError as exc:
            trace.add(
                phase="error",
                action_index=idx,
                action_kind=action_kind,
                message=str(exc),
            )
            return trace.failure()
