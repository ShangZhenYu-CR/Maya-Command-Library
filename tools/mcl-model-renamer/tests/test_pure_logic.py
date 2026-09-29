import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "mcl_model_renamer.py"
spec = importlib.util.spec_from_file_location("mcl_model_renamer", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_build_name_two_digit_minimum():
    assert mod.build_name("A", "1", "low") == "A_01_low"
    assert mod.build_name("A", "09", "low") == "A_09_low"
    assert mod.build_name("A", "100", "low") == "A_100_low"


def test_next_index_v1_regression():
    assert mod.next_index_text("01") == "02"
    assert mod.next_index_text("99") == "100"


def test_namespace_is_preserved_v1_regression():
    node = "|root|characterA:pCube1"
    assert mod.namespace_prefix(node) == "characterA:"
    assert mod.target_leaf_name(node, "A_01_low") == "characterA:A_01_low"


def test_root_namespace_target_v1_regression():
    assert mod.target_leaf_name("|root|pCube1", "A_01_low") == "A_01_low"


def test_build_pair_names():
    assert mod.build_pair_names("A", "3") == {
        "high": "A_03_high",
        "low": "A_03_low",
    }


def test_pair_roles_first_is_high():
    assert mod.pair_roles_for_face_counts(500, 100) == ("high", "low")


def test_pair_roles_second_is_high():
    assert mod.pair_roles_for_face_counts(100, 500) == ("low", "high")


def test_pair_equal_faces_stop():
    with pytest.raises(mod.RenameError, match="same Face Count"):
        mod.pair_roles_for_face_counts(500, 500)


def test_pair_negative_face_count_rejected():
    with pytest.raises(mod.RenameError):
        mod.pair_roles_for_face_counts(-1, 1)


@pytest.mark.parametrize("base", ["", "01A", "A B", "A:B", "A|B"])
def test_invalid_base(base):
    with pytest.raises(mod.RenameError):
        mod.validate_base(base)


@pytest.mark.parametrize("role", ["", "low high", "low:high", "low|high"])
def test_invalid_role(role):
    with pytest.raises(mod.RenameError):
        mod.validate_role(role)


@pytest.mark.parametrize("index", ["", "-1", "1.5", "abc"])
def test_invalid_index(index):
    with pytest.raises(mod.RenameError):
        mod.parse_index(index)
