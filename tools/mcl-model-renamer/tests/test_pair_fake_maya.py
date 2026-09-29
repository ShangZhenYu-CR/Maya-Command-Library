import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "mcl_model_renamer.py"
spec = importlib.util.spec_from_file_location("mcl_model_renamer_fake", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeCmds:
    def __init__(self, first_faces=500, second_faces=100, fail_target=None, conflict=None):
        self.selection = ["|First", "|Second"]
        self.transforms = {"|First", "|Second"}
        self.shapes = {
            "|First": ["|First|FirstShape"],
            "|Second": ["|Second|SecondShape"],
        }
        self.face_counts = {
            "|First|FirstShape": first_faces,
            "|Second|SecondShape": second_faces,
        }
        self.rename_calls = []
        self.undo_calls = []
        self.fail_target = fail_target
        if conflict:
            long_name = "|" + conflict
            self.transforms.add(long_name)
            self.shapes[long_name] = [long_name + "|Shape"]
            self.face_counts[long_name + "|Shape"] = 1

    def ls(self, value=None, selection=False, long=False, flatten=False, **kwargs):
        if selection:
            return list(self.selection)
        if value is None:
            return []
        if value in self.transforms or value in self.face_counts:
            return [value]
        matches = [node for node in self.transforms if node.rsplit("|", 1)[-1] == value]
        return sorted(matches)

    def objExists(self, node):
        return node in self.transforms or node in self.face_counts

    def nodeType(self, node):
        if node in self.transforms:
            return "transform"
        if node in self.face_counts:
            return "mesh"
        raise RuntimeError("unknown node")

    def listRelatives(self, node, shapes=False, fullPath=False, noIntermediate=False, **kwargs):
        return list(self.shapes.get(node, []))

    def referenceQuery(self, node, isNodeReferenced=False):
        return False

    def lockNode(self, node, query=False, lock=False):
        return [False]

    def polyEvaluate(self, shape, face=False):
        return self.face_counts[shape]

    def undoInfo(self, **kwargs):
        self.undo_calls.append(dict(kwargs))

    def rename(self, node, target_leaf):
        if target_leaf == self.fail_target:
            raise RuntimeError("simulated rename failure")
        if node not in self.transforms:
            raise RuntimeError("missing transform")
        new_long = "|" + target_leaf
        if new_long in self.transforms and new_long != node:
            raise RuntimeError("name conflict")

        self.transforms.remove(node)
        self.transforms.add(new_long)
        shape_list = self.shapes.pop(node, [])
        self.shapes[new_long] = shape_list
        self.selection = [new_long if item == node else item for item in self.selection]
        self.rename_calls.append((node, target_leaf))
        return target_leaf


def test_pair_success_classifies_and_increments_once():
    fake = FakeCmds(first_faces=500, second_faces=100)
    mod.cmds = fake
    result = mod.rename_pair_high_low("A", "01")

    assert result["high"]["new_name"] == "A_01_high"
    assert result["high"]["faces"] == 500
    assert result["low"]["new_name"] == "A_01_low"
    assert result["low"]["faces"] == 100
    assert result["next_index"] == "02"
    assert "|A_01_high" in fake.transforms
    assert "|A_01_low" in fake.transforms
    assert len(fake.rename_calls) == 2
    assert fake.undo_calls[0]["openChunk"] is True
    assert fake.undo_calls[-1]["closeChunk"] is True


def test_pair_equal_faces_changes_nothing():
    fake = FakeCmds(first_faces=100, second_faces=100)
    mod.cmds = fake
    with pytest.raises(mod.RenameError, match="same Face Count"):
        mod.rename_pair_high_low("A", "01")
    assert fake.rename_calls == []
    assert fake.transforms.issuperset({"|First", "|Second"})


def test_pair_conflict_changes_nothing():
    fake = FakeCmds(first_faces=500, second_faces=100, conflict="A_01_high")
    mod.cmds = fake
    with pytest.raises(mod.RenameError, match="Target name already exists"):
        mod.rename_pair_high_low("A", "01")
    assert fake.rename_calls == []
    assert fake.transforms.issuperset({"|First", "|Second", "|A_01_high"})


def test_pair_second_rename_failure_rolls_back_first():
    fake = FakeCmds(first_faces=500, second_faces=100, fail_target="A_01_low")
    mod.cmds = fake
    with pytest.raises(mod.RenameError, match="Pair rename failed"):
        mod.rename_pair_high_low("A", "01")
    assert "|First" in fake.transforms
    assert "|Second" in fake.transforms
    assert "|A_01_high" not in fake.transforms
