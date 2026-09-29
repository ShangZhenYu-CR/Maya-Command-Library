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


def test_next_index():
    assert mod.next_index_text("01") == "02"
    assert mod.next_index_text("99") == "100"


def test_namespace_is_preserved():
    node = "|root|characterA:pCube1"
    assert mod.namespace_prefix(node) == "characterA:"
    assert mod.target_leaf_name(node, "A_01_low") == "characterA:A_01_low"


def test_root_namespace_target():
    assert mod.target_leaf_name("|root|pCube1", "A_01_low") == "A_01_low"


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
