from mac_maestro import ClickAction, MacMaestro
from mac_maestro.backends.mock import MockBackend
from mac_maestro.models import AXNodeSnapshot


def test_runtime_click_flow() -> None:
    root = AXNodeSnapshot(
        element_id="root",
        role="AXWindow",
        title="Main",
        children=[
            AXNodeSnapshot(
                element_id="btn_new",
                role="AXButton",
                title="New Document",
            )
        ],
    )
    backend = MockBackend(root=root)
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)

    trace = maestro.run([ClickAction(role="AXButton", title="New Document")])

    assert trace.ok is True
    assert backend.executed[0]["kind"] == "click"
    assert backend.executed[0]["element_id"] == "btn_new"
