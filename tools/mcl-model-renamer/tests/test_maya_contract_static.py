from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "mcl_model_renamer.py").read_text(encoding="utf-8")


def test_v1_safety_contracts_remain_present():
    assert "referenceQuery" in SOURCE
    assert "lockNode" in SOURCE
    assert "noIntermediate=True" in SOURCE
    assert "actual_leaf == target_leaf" in SOURCE
    assert "Target name already exists" in SOURCE
    assert 'label="Rename Selected"' in SOURCE


def test_v2_pair_contracts_are_present():
    assert "def rename_pair_high_low" in SOURCE
    assert "polyEvaluate" in SOURCE
    assert "same Face Count" in SOURCE
    assert '"high": build_name' in SOURCE
    assert '"low": build_name' in SOURCE
    assert "UNDO_CHUNK_PAIR" in SOURCE
    assert "renamed_records" in SOURCE
    assert "rollback" in SOURCE
    assert 'label="Rename Pair High / Low"' in SOURCE


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
