from mac_maestro.matcher import find_best_match
from mac_maestro.models import AXNodeSnapshot, ElementSelector


def make_tree() -> AXNodeSnapshot:
    return AXNodeSnapshot(
        element_id="root",
        role="AXWindow",
        title="Main",
        children=[
            AXNodeSnapshot(
                element_id="btn_save",
                role="AXButton",
                title="Save",
            ),
            AXNodeSnapshot(
                element_id="input_name",
                role="AXTextField",
                title="Name",
                value="Borja",
            ),
        ],
    )


def test_find_best_match_by_role_and_title() -> None:
    root = make_tree()
    match = find_best_match(root, ElementSelector(role="AXButton", title="Save"))
    assert match.element_id == "btn_save"
    assert match.confidence > 0.5
