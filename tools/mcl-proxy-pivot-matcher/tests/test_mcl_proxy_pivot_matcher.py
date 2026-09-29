import sys
import math
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
                "rotateOrder": int(data.get("rotateOrder", 0)),
            }
            for node, data in transform_values.items()
        }
        self.offset_parent = {node: tool._identity_matrix() for node in self.targets | self.proxies}
        self.match_calls = []
        self.set_calls = []
        self.rename_calls = []
        self.undo_calls = []
        self.fail_target = fail_target

    def _rotation_matrix_xyz(self, rotate):
        rx, ry, rz = [math.radians(v) for v in rotate]
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        mx = (
            1,0,0,0,
            0,cx,sx,0,
            0,-sx,cx,0,
            0,0,0,1,
        )
        my = (
            cy,0,-sy,0,
            0,1,0,0,
            sy,0,cy,0,
            0,0,0,1,
        )
        mz = (
            cz,sz,0,0,
            -sz,cz,0,0,
            0,0,1,0,
            0,0,0,1,
        )
        return tool._matrix_multiply(tool._matrix_multiply(mx, my), mz)

    def _local_matrix(self, node):
        data = self.values[node]
        sx, sy, sz = data["scale"]
        scale = (
            sx,0,0,0,
            0,sy,0,0,
            0,0,sz,0,
            0,0,0,1,
        )
        rot = self._rotation_matrix_xyz(data["rotate"])
        tx, ty, tz = data["translate"]
        trans = (
            1,0,0,0,
            0,1,0,0,
            0,0,1,0,
            tx,ty,tz,1,
        )
        return tool._matrix_multiply(tool._matrix_multiply(scale, rot), trans)

    def _world_matrix(self, node):
        return tool._matrix_multiply(self._local_matrix(node), self.offset_parent[node])

    def ls(self, value=None, selection=False, long=False, flatten=False, **kwargs):
        if selection:
            return list(self.selection)
        if value == self.proxy_root:
            return [self.proxy_root] if self.proxy_root in self.transforms else []
        if value in self.transforms:
            return [value]
        return []

    def listRelatives(self, node, shapes=False, fullPath=False, allDescendents=False,
                      type=None, parent=False, **kwargs):
        if node == self.proxy_root and allDescendents and type == "transform":
            return sorted(self.proxies)
        if shapes:
            return list(self.shapes.get(node, []))
        if parent:
            parent_path = node.rsplit("|", 1)[0]
            return [parent_path] if parent_path else []
        return []

    def nodeType(self, node):
        if node in self.transforms:
            return "transform"
        if node.endswith("|Shape"):
            return "mesh"
        return "unknown"

    def objExists(self, value):
        if value.endswith(".offsetParentMatrix"):
            node = value.rsplit(".", 1)[0]
            return node in self.transforms and node != self.proxy_root
        return value in self.transforms or value in {shape for shapes in self.shapes.values() for shape in shapes}

    def getAttr(self, attr, settable=False, **kwargs):
        if attr.endswith(".intermediateObject"):
            return False
        node, plug = attr.rsplit(".", 1)
        if settable:
            return True
        if plug in ("translate", "rotate", "scale"):
            return [self.values[node][plug]]
        if plug in ("translateX", "translateY", "translateZ",
                    "rotateX", "rotateY", "rotateZ",
                    "scaleX", "scaleY", "scaleZ"):
            base = {"t": "translate", "r": "rotate", "s": "scale"}[plug[0]]
            axis = {"X": 0, "Y": 1, "Z": 2}[plug[-1]]
            return self.values[node][base][axis]
        if plug == "rotateOrder":
            return self.values[node]["rotateOrder"]
        if plug == "matrix":
            return self._local_matrix(node)
        if plug == "worldMatrix[0]":
            return self._world_matrix(node)
        if plug == "offsetParentMatrix":
            return self.offset_parent[node]
        return None

    def setAttr(self, attr, *values, **kwargs):
        node, plug = attr.rsplit(".", 1)
        self.set_calls.append((attr, values, kwargs))
        if plug in ("translate", "rotate", "scale"):
            self.values[node][plug] = tuple(float(v) for v in values[:3])
            return
        if plug == "rotateOrder":
            self.values[node]["rotateOrder"] = int(values[0])
            return
        if plug == "offsetParentMatrix":
            matrix = values[0] if len(values) == 1 and isinstance(values[0], (list, tuple)) else values
            self.offset_parent[node] = tool._matrix16(matrix)
            return
        raise RuntimeError("unsupported setAttr {}".format(attr))

    def rename(self, node, desired):
        self.rename_calls.append((node, desired))
        parent = node.rsplit("|", 1)[0]
        new_node = (parent + "|" + desired) if parent else ("|" + desired)
        if new_node in self.transforms and new_node != node:
            raise RuntimeError("name conflict")

        def moved(value):
            if value == node:
                return new_node
            if value.startswith(node + "|"):
                return new_node + value[len(node):]
            return value

        self.transforms = {moved(value) for value in self.transforms}
        self.targets = {moved(value) for value in self.targets}
        self.proxies = {moved(value) for value in self.proxies}
        self.selection = [moved(value) for value in self.selection]

        new_shapes = {}
        for owner, shapes in self.shapes.items():
            new_owner = moved(owner)
            new_shapes[new_owner] = [moved(shape) for shape in shapes]
        self.shapes = new_shapes

        self.boxes = {moved(owner): value for owner, value in self.boxes.items()}
        self.values = {moved(owner): value for owner, value in self.values.items()}
        self.offset_parent = {moved(owner): value for owner, value in self.offset_parent.items()}
        return new_node

    def referenceQuery(self, node, **kwargs):
        return False

    def lockNode(self, node, **kwargs):
        return [False]

    def exactWorldBoundingBox(self, node):
        return self.boxes[node]

    def undoInfo(self, **kwargs):
        self.undo_calls.append(kwargs)

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


def test_apply_syncs_trs_and_pivots_preserving_world_matrix():
    fake = make_fake()
    setup(fake)
    before_a = fake._world_matrix("|FinalA")
    before_b = fake._world_matrix("|FinalB")

    analysis = tool.analyze_matches()
    result = tool.apply_matches(analysis["signature"])
    assert result["matched_count"] == 2

    assert fake.values["|FinalA"]["translate"] == fake.values["|proxy|ProxyA"]["translate"]
    assert fake.values["|FinalA"]["rotate"] == fake.values["|proxy|ProxyA"]["rotate"]
    assert fake.values["|FinalA"]["scale"] == fake.values["|proxy|ProxyA"]["scale"]
    assert fake.values["|FinalB"]["translate"] == fake.values["|proxy|ProxyB"]["translate"]
    assert fake.values["|FinalB"]["rotate"] == fake.values["|proxy|ProxyB"]["rotate"]
    assert fake.values["|FinalB"]["scale"] == fake.values["|proxy|ProxyB"]["scale"]

    assert tool._matrices_close(fake._world_matrix("|FinalA"), before_a)
    assert tool._matrices_close(fake._world_matrix("|FinalB"), before_b)
    assert not tool._matrices_close(fake.offset_parent["|FinalA"], tool._identity_matrix())

    assert fake.match_calls == [
        ("|FinalA", "|proxy|ProxyA", {"pivots": True}),
        ("|FinalB", "|proxy|ProxyB", {"pivots": True}),
    ]
    assert fake.undo_calls[0] == {"openChunk": True, "chunkName": tool.UNDO_CHUNK}
    assert fake.undo_calls[-1] == {"closeChunk": True}


def test_matrix_rebalance_formula_preserves_world_with_parent_matrix():
    local = (
        2,0,0,0,
        0,3,0,0,
        0,0,4,0,
        5,6,7,1,
    )
    parent = (
        1,0,0,0,
        0,1,0,0,
        0,0,1,0,
        10,20,30,1,
    )
    world = (
        1,0,0,0,
        0,1,0,0,
        0,0,1,0,
        100,200,300,1,
    )
    compensation = tool._matrix_multiply(
        tool._matrix_multiply(tool._matrix_inverse(local), world),
        tool._matrix_inverse(parent),
    )
    rebuilt = tool._matrix_multiply(tool._matrix_multiply(local, compensation), parent)
    assert tool._matrices_close(rebuilt, world)


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


def test_name_sync_off_does_not_rename_anything():
    fake = make_fake()
    setup(fake)
    analysis = tool.analyze_matches(sync_names=False)
    result = tool.apply_matches(analysis["signature"], sync_names=False)
    assert result["renamed_count"] == 0
    assert fake.rename_calls == []
    assert "|FinalA" in fake.targets
    assert "|proxy|ProxyA" in fake.proxies


def test_name_sync_on_copies_proxy_base_name_and_prefixes_proxy():
    fake = make_fake()
    setup(fake)
    analysis = tool.analyze_matches(sync_names=True, proxy_prefix="synced_")
    lines = tool.analysis_lines(analysis)
    assert "NAME | FinalA -> ProxyA | ProxyA -> synced_ProxyA" in lines
    result = tool.apply_matches(
        analysis["signature"], sync_names=True, proxy_prefix="synced_"
    )
    assert result["renamed_count"] == 4
    assert "|ProxyA" in fake.targets
    assert "|ProxyB" in fake.targets
    assert "|proxy|synced_ProxyA" in fake.proxies
    assert "|proxy|synced_ProxyB" in fake.proxies
    assert "|proxy|Unused" in fake.proxies


def test_name_sync_is_idempotent_for_already_prefixed_proxy():
    fake = make_fake()
    setup(fake)
    fake.rename("|proxy|ProxyA", "synced_ProxyA")
    analysis = tool.analyze_matches(sync_names=True, proxy_prefix="synced_")
    entry = next(item for item in analysis["name_plan"] if item["proxy"].endswith("synced_ProxyA"))
    assert entry["target_name"] == "ProxyA"
    assert entry["proxy_name"] == "synced_ProxyA"


def test_name_sync_conflict_blocks_before_scene_changes():
    fake = make_fake()
    fake.transforms.add("|ProxyA")
    setup(fake)
    with pytest.raises(tool.PivotMatchError, match="Name conflict"):
        tool.analyze_matches(sync_names=True, proxy_prefix="synced_")
    assert fake.match_calls == []
    assert fake.set_calls == []
    assert fake.undo_calls == []


def test_name_sync_namespace_is_rejected():
    fake = make_fake()
    setup(fake)
    fake.rename("|proxy|ProxyA", "ns:ProxyA")
    with pytest.raises(tool.PivotMatchError, match="does not support namespaces"):
        tool.analyze_matches(sync_names=True, proxy_prefix="synced_")


def test_name_sync_prefix_change_requires_reanalysis():
    fake = make_fake()
    setup(fake)
    analysis = tool.analyze_matches(sync_names=True, proxy_prefix="synced_")
    with pytest.raises(tool.PivotMatchError, match="Analyze again"):
        tool.apply_matches(
            analysis["signature"], sync_names=True, proxy_prefix="done_"
        )


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
    assert "offsetParentMatrix" in source
    assert "_rebalance_transform_values_with_offset_parent_matrix" in source
    assert 'cmds.setAttr(target + ".offsetParentMatrix"' in source
    assert "cmds.rename(" in source
    assert "DEFAULT_SYNCED_PREFIX" in source
    assert "preserveGeometryPosition=True" not in source
    for token in (
        "deleteHistory",
        "makeIdentity",
        "polySoftEdge",
        "optionVar(",
        "trackSelectionOrder",
    ):
        assert token not in source
