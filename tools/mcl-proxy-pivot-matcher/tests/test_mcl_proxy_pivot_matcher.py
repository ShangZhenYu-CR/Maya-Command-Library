import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import mcl_proxy_pivot_matcher as tool


def bounds(cx, cy, cz, sx=2.0, sy=2.0, sz=2.0):
    return (
        cx - sx / 2.0, cy - sy / 2.0, cz - sz / 2.0,
        cx + sx / 2.0, cy + sy / 2.0, cz + sz / 2.0,
    )


class FakeMaya:
    def __init__(self, targets, proxies, target_boxes, proxy_boxes, transform_values, fail_target=None):
        self.selection = list(targets)
        self.proxy_root = "|proxy"
        self.targets = set(targets)
        self.proxies = set(proxies)
        self.transforms = {self.proxy_root} | self.targets | self.proxies
        self.shapes = {}
        for node in self.targets | self.proxies:
            self.shapes[node] = [node + "|Shape"]
        self.boxes = {}
        self.boxes.update(target_boxes)
        self.boxes.update(proxy_boxes)
        self.values = {
            node: {
                "translate": tuple(data["translate"]),
                "rotate": tuple(data["rotate"]),
                "scale": tuple(data["scale"]),
            }
            for node, data in transform_values.items()
        }
        self.match_calls = []
        self.move_calls = []
        self.rotate_calls = []
        self.scale_calls = []
        self.undo_calls = []
        self.fail_target = fail_target

    def ls(self, value=None, selection=False, long=False, flatten=False, **kwargs):
        if selection:
            return list(self.selection)
        if value == self.proxy_root:
            return [self.proxy_root] if self.proxy_root in self.transforms else []
        if value in self.transforms:
            return [value]
        return []

    def listRelatives(self, node, shapes=False, fullPath=False, allDescendents=False,
                      type=None, **kwargs):
        if node == self.proxy_root and allDescendents and type == "transform":
            return sorted(self.proxies)
        if shapes:
            return list(self.shapes.get(node, []))
        return []

    def nodeType(self, node):
        if node in self.transforms:
            return "transform"
        if node.endswith("|Shape"):
            return "mesh"
        return "unknown"

    def getAttr(self, attr, settable=False, **kwargs):
        if attr.endswith(".intermediateObject"):
            return False
        if settable:
            return True
        node, plug = attr.rsplit(".", 1)
        if plug in ("translate", "rotate", "scale"):
            return [self.values[node][plug]]
        return None

    def referenceQuery(self, node, **kwargs):
        return False

    def lockNode(self, node, **kwargs):
        return [False]

    def exactWorldBoundingBox(self, node):
        return self.boxes[node]

    def undoInfo(self, **kwargs):
        self.undo_calls.append(kwargs)

    def move(self, x, y, z, target, **kwargs):
        self.move_calls.append((target, (x, y, z), kwargs))
        self.values[target]["translate"] = (x, y, z)

    def rotate(self, x, y, z, target, **kwargs):
        self.rotate_calls.append((target, (x, y, z), kwargs))
        self.values[target]["rotate"] = (x, y, z)

    def scale(self, x, y, z, target, **kwargs):
        self.scale_calls.append((target, (x, y, z), kwargs))
        self.values[target]["scale"] = (x, y, z)

    def matchTransform(self, target, proxy, **kwargs):
        if target == self.fail_target:
            raise RuntimeError("simulated match failure")
        self.match_calls.append((target, proxy, kwargs))

def setup(fake):
    tool.cmds = fake


def records():
    target_records = [
        {"node": "|FinalA", "bounds": bounds(0.02, 0, 0)},
        {"node": "|FinalB", "bounds": bounds(10.02, 0, 0)},
    ]
    proxy_records = [
        {"node": "|proxy|ProxyA", "bounds": bounds(0, 0, 0)},
        {"node": "|proxy|ProxyB", "bounds": bounds(10, 0, 0)},
        {"node": "|proxy|Unused", "bounds": bounds(100, 0, 0)},
    ]
    return target_records, proxy_records


def make_fake(order=None, fail_target=None):
    targets = order or ["|FinalA", "|FinalB"]
    proxies = ["|proxy|ProxyA", "|proxy|ProxyB", "|proxy|Unused"]
    target_boxes = {
        "|FinalA": bounds(0.02, 0, 0),
        "|FinalB": bounds(10.02, 0, 0),
    }
    proxy_boxes = {
        "|proxy|ProxyA": bounds(0, 0, 0),
        "|proxy|ProxyB": bounds(10, 0, 0),
        "|proxy|Unused": bounds(100, 0, 0),
    }
    transform_values = {
        "|FinalA": {"translate": (9, 9, 9), "rotate": (1, 2, 3), "scale": (2, 2, 2)},
        "|FinalB": {"translate": (8, 8, 8), "rotate": (4, 5, 6), "scale": (3, 3, 3)},
        "|proxy|ProxyA": {"translate": (1, 2, 3), "rotate": (10, 20, 30), "scale": (1, 1, 1)},
        "|proxy|ProxyB": {"translate": (4, 5, 6), "rotate": (0, 90, 0), "scale": (1, 1, 1)},
        "|proxy|Unused": {"translate": (100, 0, 0), "rotate": (0, 0, 0), "scale": (1, 1, 1)},
    }
    return FakeMaya(
        targets, proxies, target_boxes, proxy_boxes, transform_values,
        fail_target=fail_target,
    )


def test_metric_accepts_close_and_rejects_far_or_large_size_mismatch():
    assert tool.bbox_pair_metric(bounds(0,0,0), bounds(.02,0,0))["eligible"]
    assert not tool.bbox_pair_metric(bounds(0,0,0), bounds(10,0,0))["eligible"]
    assert not tool.bbox_pair_metric(
        bounds(0,0,0,2,2,2), bounds(0,0,0,10,10,10)
    )["eligible"]


def test_bipartite_pairing_is_stable_and_allows_unused_proxies():
    targets, proxies = records()
    a = tool.pair_targets_to_proxies(targets, proxies)
    b = tool.pair_targets_to_proxies(list(reversed(targets)), list(reversed(proxies)))
    mapping_a = [(p["target"]["node"], p["proxy"]["node"]) for p in a["pairs"]]
    mapping_b = [(p["target"]["node"], p["proxy"]["node"]) for p in b["pairs"]]
    assert mapping_a == mapping_b == [
        ("|FinalA", "|proxy|ProxyA"),
        ("|FinalB", "|proxy|ProxyB"),
    ]
    assert not a["unresolved"]


def test_ambiguous_proxy_candidates_block_target():
    targets = [{"node": "|Final", "bounds": bounds(0,0,0)}]
    proxies = [
        {"node": "|proxy|A", "bounds": bounds(.01,0,0)},
        {"node": "|proxy|B", "bounds": bounds(-.01,0,0)},
    ]
    result = tool.pair_targets_to_proxies(targets, proxies)
    assert not result["pairs"]
    assert result["unresolved"][0][1] == "ambiguous_proxy_candidates"


def test_analysis_is_read_only_and_ready_for_normal_scene():
    fake = make_fake()
    setup(fake)
    result = tool.analyze_matches()
    assert result["ready"]
    assert result["target_count"] == 2
    assert fake.match_calls == []
    assert result["signature"] is not None


def test_selection_order_does_not_change_signature():
    fake = make_fake(["|FinalA", "|FinalB"])
    setup(fake)
    first = tool.analyze_matches()
    fake.selection.reverse()
    second = tool.analyze_matches()
    assert first["signature"] == second["signature"]


def test_apply_syncs_trs_and_pivots_in_one_undo_chunk():
    fake = make_fake()
    setup(fake)
    analysis = tool.analyze_matches()
    result = tool.apply_matches(analysis["signature"])
    assert result["matched_count"] == 2

    assert fake.values["|FinalA"] == fake.values["|proxy|ProxyA"]
    assert fake.values["|FinalB"] == fake.values["|proxy|ProxyB"]

    preserve_flags = {
        "absolute": True,
        "preserveGeometryPosition": True,
        "preserveChildPosition": True,
    }
    assert fake.move_calls[0] == (
        "|FinalA", (1.0, 2.0, 3.0), {**preserve_flags, "localSpace": True}
    )
    assert fake.rotate_calls[0] == (
        "|FinalA", (10.0, 20.0, 30.0), {**preserve_flags, "objectSpace": True}
    )
    assert fake.scale_calls[0] == (
        "|FinalA", (1.0, 1.0, 1.0), {**preserve_flags, "localSpace": True}
    )

    assert fake.match_calls == [
        ("|FinalA", "|proxy|ProxyA", {"pivots": True}),
        ("|FinalB", "|proxy|ProxyB", {"pivots": True}),
    ]
    assert fake.undo_calls[0] == {"openChunk": True, "chunkName": tool.UNDO_CHUNK}
    assert fake.undo_calls[-1] == {"closeChunk": True}


def test_changed_world_bounds_requires_reanalysis():
    fake = make_fake()
    setup(fake)
    analysis = tool.analyze_matches()
    fake.boxes["|FinalA"] = bounds(0.20, 0, 0)
    with pytest.raises(tool.PivotMatchError, match="Analyze again"):
        tool.apply_matches(analysis["signature"])


def test_changed_proxy_coordinate_values_requires_reanalysis():
    fake = make_fake()
    setup(fake)
    analysis = tool.analyze_matches()
    fake.values["|proxy|ProxyA"]["translate"] = (7, 8, 9)
    with pytest.raises(tool.PivotMatchError, match="Analyze again"):
        tool.apply_matches(analysis["signature"])


def test_proxy_object_cannot_be_selected_as_target():
    fake = make_fake(["|proxy|ProxyA"])
    setup(fake)
    with pytest.raises(tool.PivotMatchError, match="cannot be selected"):
        tool.analyze_matches()


def test_missing_proxy_group_stops_before_changes():
    fake = make_fake()
    fake.transforms.remove("|proxy")
    setup(fake)
    with pytest.raises(tool.PivotMatchError, match="was not found"):
        tool.analyze_matches()
    assert fake.match_calls == []


def test_partial_failure_closes_chunk_and_reports_undo():
    fake = make_fake(fail_target="|FinalB")
    setup(fake)
    analysis = tool.analyze_matches()
    with pytest.raises(tool.PivotMatchError, match="Use Undo immediately"):
        tool.apply_matches(analysis["signature"])
    assert fake.match_calls == [
        ("|FinalA", "|proxy|ProxyA", {"pivots": True}),
    ]
    assert fake.undo_calls[-1] == {"closeChunk": True}


def test_static_safety_contract():
    source = (ROOT / "mcl_proxy_pivot_matcher.py").read_text(encoding="utf-8")
    assert "matchTransform(target, proxy, pivots=True)" in source
    assert "preserveGeometryPosition=True" in source
    assert "preserveChildPosition=True" in source
    assert "_sync_transform_values_preserve_geometry" in source
    for token in (
        "deleteHistory",
        "makeIdentity",
        "polySoftEdge",
        "optionVar(",
        "trackSelectionOrder",
        "cmds.rename(",
    ):
        assert token not in source
