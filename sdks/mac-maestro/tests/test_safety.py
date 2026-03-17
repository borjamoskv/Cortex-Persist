import pytest
from mac_maestro.errors import SafetyViolationError
from mac_maestro.models import ClickAction
from mac_maestro.safety import SafetyPolicy


def test_blocks_destructive_clicks() -> None:
    policy = SafetyPolicy(allow_destructive=False)
    with pytest.raises(SafetyViolationError):
        policy.validate(ClickAction(role="AXButton", title="Delete"))
