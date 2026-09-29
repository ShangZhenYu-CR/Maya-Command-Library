from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "mcl_model_renamer.py").read_text(encoding="utf-8")


def test_safety_contracts_are_present():
    assert "referenceQuery" in SOURCE
    assert "lockNode" in SOURCE
    assert "noIntermediate=True" in SOURCE
    assert "undoInfo(openChunk=True" in SOURCE
    assert "actual_leaf != target_leaf" in SOURCE
    assert "Target name already exists" in SOURCE


def test_out_of_scope_scene_mutators_are_absent():
    forbidden = [
        "deleteHistory",
        "makeIdentity",
        "polySoftEdge",
        "delete(ch=True",
        "optionVar(",
    ]
    for token in forbidden:
        assert token not in SOURCE
