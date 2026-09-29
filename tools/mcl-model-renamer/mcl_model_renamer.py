# -*- coding: utf-8 -*-
"""MCL Model Renamer V3.

V1: sequential single-model naming using {Base}_{Index}_{Role}.
V2: two-model High/Low naming based on polygon face count.
V3: analyze multiple selected meshes, auto-pair by world-space proximity and
    bounding-box similarity, preview the plan, then apply stable pair naming.
"""

from __future__ import annotations

import math
import re

try:
    from maya import cmds
except ImportError:  # Allows host-independent tests of pure helpers.
    cmds = None


WINDOW_NAME = "MCLModelRenamerWindow"
WINDOW_TITLE = "MCL Model Renamer"
UNDO_CHUNK_SINGLE = "MCL_Model_Renamer_V1_Single"
UNDO_CHUNK_PAIR = "MCL_Model_Renamer_V2_Pair"
UNDO_CHUNK_AUTO = "MCL_Model_Renamer_V3_AutoPairs"
MIN_INDEX_WIDTH = 2

AUTO_CENTER_LIMIT = 0.25
AUTO_SIZE_LIMIT = 0.35
AUTO_SIZE_WEIGHT = 0.35
AUTO_AMBIGUITY_GAP = 0.05
_EPSILON = 1e-8

_BASE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ROLE_RE = re.compile(r"^[A-Za-z0-9_]+$")


class RenameError(RuntimeError):
    """Expected user-facing validation or rename failure."""


def validate_base(base: str) -> str:
    value = (base or "").strip()
    if not value:
        raise RenameError("Base Name cannot be empty.")
    if not _BASE_RE.match(value):
        raise RenameError(
            "Base Name must start with a letter or underscore and contain only "
            "letters, numbers, or underscores."
        )
    return value


def validate_role(role: str) -> str:
    value = (role or "").strip()
    if not value:
        raise RenameError("Role cannot be empty.")
    if not _ROLE_RE.match(value):
        raise RenameError("Role can contain only letters, numbers, or underscores.")
    return value


def parse_index(index_text: str) -> int:
    value = (index_text or "").strip()
    if not value or not value.isdigit():
        raise RenameError("Index must be a non-negative whole number.")
    return int(value)


def format_index(index: int) -> str:
    if index < 0:
        raise RenameError("Index must be zero or greater.")
    return str(index).zfill(MIN_INDEX_WIDTH)


def build_name(base: str, index_text: str, role: str) -> str:
    safe_base = validate_base(base)
    safe_role = validate_role(role)
    index = parse_index(index_text)
    return "{}_{}_{}".format(safe_base, format_index(index), safe_role)


def build_pair_names(base: str, index_text: str) -> dict:
    return {
        "high": build_name(base, index_text, "high"),
        "low": build_name(base, index_text, "low"),
    }


def pair_roles_for_face_counts(first_faces: int, second_faces: int) -> tuple[str, str]:
    if first_faces < 0 or second_faces < 0:
        raise RenameError("Face Count cannot be negative.")
    if first_faces == second_faces:
        raise RenameError(
            "Both selected models have the same Face Count ({}). High / Low cannot be determined.".format(
                first_faces
            )
        )
    if first_faces > second_faces:
        return "high", "low"
    return "low", "high"


def next_index_text(index_text: str) -> str:
    return format_index(parse_index(index_text) + 1)


def advance_index_text(index_text: str, amount: int) -> str:
    if amount < 0:
        raise RenameError("Index advance amount cannot be negative.")
    return format_index(parse_index(index_text) + amount)


def leaf_name(node: str) -> str:
    return (node or "").rsplit("|", 1)[-1]


def namespace_prefix(node: str) -> str:
    leaf = leaf_name(node)
    if ":" not in leaf:
        return ""
    return leaf.rsplit(":", 1)[0] + ":"


def target_leaf_name(node: str, generated_name: str) -> str:
    return namespace_prefix(node) + generated_name


def bbox_center_size(bounds) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if bounds is None or len(bounds) != 6:
        raise RenameError("World bounding box must contain 6 numeric values.")
    values = tuple(float(value) for value in bounds)
    xmin, ymin, zmin, xmax, ymax, zmax = values
    if xmax < xmin or ymax < ymin or zmax < zmin:
        raise RenameError("World bounding box minimum exceeds maximum.")
    center = (
        (xmin + xmax) * 0.5,
        (ymin + ymax) * 0.5,
        (zmin + zmax) * 0.5,
    )
    size = (xmax - xmin, ymax - ymin, zmax - zmin)
    return center, size


def _distance3(a, b) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def bbox_pair_metric(first_bounds, second_bounds) -> dict:
    first_center, first_size = bbox_center_size(first_bounds)
    second_center, second_size = bbox_center_size(second_bounds)

    first_diag = math.sqrt(sum(value * value for value in first_size))
    second_diag = math.sqrt(sum(value * value for value in second_size))
    scale = max((first_diag + second_diag) * 0.5, _EPSILON)
    center_norm = _distance3(first_center, second_center) / scale

    mismatches = []
    for first_value, second_value in zip(first_size, second_size):
        denom = max(abs(first_value), abs(second_value), _EPSILON)
        mismatches.append(abs(first_value - second_value) / denom)
    size_mismatch = sum(mismatches) / 3.0

    score = center_norm + AUTO_SIZE_WEIGHT * size_mismatch
    eligible = center_norm <= AUTO_CENTER_LIMIT and size_mismatch <= AUTO_SIZE_LIMIT
    return {
        "center_norm": center_norm,
        "size_mismatch": size_mismatch,
        "score": score,
        "eligible": eligible,
    }


def _pair_sort_key(first_record: dict, second_record: dict):
    first_center, _ = bbox_center_size(first_record["bounds"])
    second_center, _ = bbox_center_size(second_record["bounds"])
    center = tuple((a + b) * 0.5 for a, b in zip(first_center, second_center))
    stable_nodes = tuple(sorted((first_record["node"], second_record["node"])))
    return (
        round(center[0], 8),
        round(center[2], 8),
        round(center[1], 8),
        stable_nodes[0],
        stable_nodes[1],
    )


def auto_pair_records(records: list[dict]) -> dict:
    """Pure V3 pairing: mutual-best eligible candidates, independent of selection order."""
    if len(records) < 2:
        return {"pairs": [], "unresolved": [(record["node"], "not_enough_models") for record in records]}

    by_node = {record["node"]: record for record in records}
    if len(by_node) != len(records):
        raise RenameError("Auto-pair records must have unique node identifiers.")

    best = {}
    preliminary_reason = {}

    for node in sorted(by_node):
        candidates = []
        for other in sorted(by_node):
            if other == node:
                continue
            metric = bbox_pair_metric(by_node[node]["bounds"], by_node[other]["bounds"])
            if metric["eligible"]:
                candidates.append((metric["score"], other, metric))

        candidates.sort(key=lambda item: (item[0], item[1]))
        if not candidates:
            preliminary_reason[node] = "no_eligible_match"
            continue

        if len(candidates) > 1:
            first_score = candidates[0][0]
            second_score = candidates[1][0]
            if second_score - first_score <= AUTO_AMBIGUITY_GAP:
                preliminary_reason[node] = "ambiguous_match"
                continue

        best[node] = candidates[0]

    paired_nodes = set()
    raw_pairs = []
    for node in sorted(by_node):
        if node in paired_nodes or node not in best:
            continue
        other = best[node][1]
        other_best = best.get(other)
        if other_best is None or other_best[1] != node:
            preliminary_reason.setdefault(node, "not_mutual_best")
            continue
        if other in paired_nodes:
            continue
        metric = best[node][2]
        raw_pairs.append(
            {
                "first": by_node[node],
                "second": by_node[other],
                "score": metric["score"],
                "center_norm": metric["center_norm"],
                "size_mismatch": metric["size_mismatch"],
            }
        )
        paired_nodes.add(node)
        paired_nodes.add(other)

    raw_pairs.sort(key=lambda pair: _pair_sort_key(pair["first"], pair["second"]))

    unresolved = []
    for node in sorted(by_node):
        if node in paired_nodes:
            continue
        unresolved.append((node, preliminary_reason.get(node, "not_mutual_best")))

    return {"pairs": raw_pairs, "unresolved": unresolved}


def _require_maya():
    if cmds is None:
        raise RuntimeError("This operation must run inside Autodesk Maya.")


def _mesh_shapes(node: str) -> list[str]:
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True, noIntermediate=True) or []
    return [shape for shape in shapes if cmds.nodeType(shape) == "mesh"]


def _validate_mesh_transform(node: str) -> str:
    if "." in node:
        raise RenameError("Component selection is not supported. Select mesh transforms.")
    if not cmds.objExists(node):
        raise RenameError("A selected object no longer exists.")
    if cmds.nodeType(node) != "transform":
        raise RenameError("Select mesh transforms, not shapes or other node types.")

    if not _mesh_shapes(node):
        raise RenameError(
            "The selected transform '{}' does not contain a non-intermediate mesh shape.".format(
                leaf_name(node)
            )
        )

    try:
        if cmds.referenceQuery(node, isNodeReferenced=True):
            raise RenameError("Referenced objects are not renamed.")
    except RenameError:
        raise
    except Exception:
        raise RenameError("Could not determine whether a selected object is referenced.")

    try:
        lock_state = cmds.lockNode(node, query=True, lock=True) or [False]
        if any(lock_state):
            raise RenameError("The selected object '{}' is locked.".format(leaf_name(node)))
    except RenameError:
        raise
    except Exception:
        raise RenameError("Could not determine a selected object's lock state.")

    return (cmds.ls(node, long=True) or [node])[0]


def _selected_mesh_transforms(expected_count: int | None = None, minimum_count: int | None = None) -> list[str]:
    _require_maya()
    raw = cmds.ls(selection=True, long=True, flatten=True) or []
    if expected_count is not None and len(raw) != expected_count:
        noun = "mesh transform" if expected_count == 1 else "mesh transforms"
        raise RenameError("Select exactly {} {}.".format(expected_count, noun))
    if minimum_count is not None and len(raw) < minimum_count:
        raise RenameError("Select at least {} mesh transforms.".format(minimum_count))

    result = [_validate_mesh_transform(node) for node in raw]
    if len(set(result)) != len(result):
        raise RenameError("Select distinct mesh transforms.")
    return result


def _selected_mesh_transform() -> str:
    return _selected_mesh_transforms(expected_count=1)[0]


def _selected_mesh_pair() -> tuple[str, str]:
    pair = _selected_mesh_transforms(expected_count=2)
    return pair[0], pair[1]


def _face_count(node: str) -> int:
    total = 0
    for shape in _mesh_shapes(node):
        value = cmds.polyEvaluate(shape, face=True)
        try:
            total += int(value)
        except (TypeError, ValueError):
            raise RenameError("Could not read Face Count for '{}'.".format(leaf_name(node)))
    return total


def _world_bbox(node: str) -> tuple[float, float, float, float, float, float]:
    try:
        bounds = cmds.exactWorldBoundingBox(node)
    except Exception as exc:
        raise RenameError("Could not read world bounding box for '{}': {}".format(leaf_name(node), exc))
    center, size = bbox_center_size(bounds)
    _ = center, size
    return tuple(float(value) for value in bounds)


def _preflight_target(node: str, target_leaf: str):
    current_leaf = leaf_name(node)
    if current_leaf == target_leaf:
        raise RenameError("The selected object already has the target name: {}".format(target_leaf))

    matches = cmds.ls(target_leaf, long=True) or []
    current_long = (cmds.ls(node, long=True) or [node])[0]
    for match in matches:
        match_long = (cmds.ls(match, long=True) or [match])[0]
        if match_long != current_long:
            raise RenameError("Target name already exists: {}".format(target_leaf))


def _rename_exact(node: str, target_leaf: str, original_leaf: str) -> str:
    renamed = cmds.rename(node, target_leaf)
    renamed_long = (cmds.ls(renamed, long=True) or [renamed])[0]
    actual_leaf = leaf_name(renamed_long)
    if actual_leaf == target_leaf:
        return renamed_long

    try:
        cmds.rename(renamed_long, original_leaf)
    except Exception:
        raise RenameError(
            "Maya did not apply the exact requested name and the original name could not "
            "be restored automatically. Use Undo immediately."
        )
    raise RenameError(
        "Maya did not apply the exact requested name. No automatic suffix was accepted."
    )


def rename_selected(base: str, index_text: str, role: str) -> dict:
    _require_maya()
    generated = build_name(base, index_text, role)
    node = _selected_mesh_transform()
    target_leaf = target_leaf_name(node, generated)
    _preflight_target(node, target_leaf)
    original_leaf = leaf_name(node)
    chunk_open = False
    try:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK_SINGLE)
        chunk_open = True
        renamed_long = _rename_exact(node, target_leaf, original_leaf)
        return {
            "old_name": original_leaf,
            "new_name": leaf_name(renamed_long),
            "next_index": next_index_text(index_text),
            "node": renamed_long,
        }
    except RenameError:
        raise
    except Exception as exc:
        raise RenameError("Rename failed: {}".format(exc))
    finally:
        if chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass


def rename_pair_high_low(base: str, index_text: str) -> dict:
    _require_maya()
    pair_names = build_pair_names(base, index_text)
    first, second = _selected_mesh_pair()
    first_faces = _face_count(first)
    second_faces = _face_count(second)
    first_role, second_role = pair_roles_for_face_counts(first_faces, second_faces)

    plan = [
        {
            "node": first,
            "faces": first_faces,
            "role": first_role,
            "target": target_leaf_name(first, pair_names[first_role]),
            "original": leaf_name(first),
        },
        {
            "node": second,
            "faces": second_faces,
            "role": second_role,
            "target": target_leaf_name(second, pair_names[second_role]),
            "original": leaf_name(second),
        },
    ]

    if plan[0]["target"] == plan[1]["target"]:
        raise RenameError("The two pair targets resolve to the same name.")

    for item in plan:
        _preflight_target(item["node"], item["target"])

    chunk_open = False
    renamed_records = []
    try:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK_PAIR)
        chunk_open = True
        for item in plan:
            renamed_long = _rename_exact(item["node"], item["target"], item["original"])
            renamed_records.append({"node": renamed_long, "original": item["original"]})
            item["node"] = renamed_long

        result = {"next_index": next_index_text(index_text)}
        for item in plan:
            result[item["role"]] = {
                "old_name": item["original"],
                "new_name": leaf_name(item["node"]),
                "faces": item["faces"],
                "node": item["node"],
            }
        return result
    except Exception as exc:
        rollback_errors = []
        for record in reversed(renamed_records):
            try:
                if cmds.objExists(record["node"]):
                    cmds.rename(record["node"], record["original"])
            except Exception as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        if rollback_errors:
            raise RenameError(
                "Pair rename failed and automatic rollback was incomplete. Use Undo immediately. "
                "Details: {}".format(" | ".join(rollback_errors))
            )
        if isinstance(exc, RenameError):
            raise
        raise RenameError("Pair rename failed: {}".format(exc))
    finally:
        if chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass


def _round_bounds(bounds):
    return tuple(round(float(value), 6) for value in bounds)


def _analysis_signature(base: str, index_text: str, records: list[dict], pairs: list[dict]):
    record_state = tuple(
        sorted(
            (
                record["node"],
                record["faces"],
                _round_bounds(record["bounds"]),
            )
            for record in records
        )
    )
    pair_state = tuple(
        (
            pair["index_text"],
            pair["high"]["node"],
            pair["high"]["target"],
            pair["high"]["faces"],
            pair["low"]["node"],
            pair["low"]["target"],
            pair["low"]["faces"],
        )
        for pair in pairs
    )
    return (validate_base(base), format_index(parse_index(index_text)), record_state, pair_state)


def analyze_auto_pairs(base: str, index_text: str) -> dict:
    _require_maya()
    validate_base(base)
    start_index = parse_index(index_text)
    nodes = _selected_mesh_transforms(minimum_count=2)

    records = []
    for node in nodes:
        records.append(
            {
                "node": node,
                "bounds": _world_bbox(node),
                "faces": _face_count(node),
            }
        )

    pairing = auto_pair_records(records)
    unresolved = list(pairing["unresolved"])
    plan_pairs = []

    for pair in pairing["pairs"]:
        first = pair["first"]
        second = pair["second"]
        try:
            first_role, second_role = pair_roles_for_face_counts(first["faces"], second["faces"])
        except RenameError:
            unresolved.append((first["node"], "same_face_count"))
            unresolved.append((second["node"], "same_face_count"))
            continue

        pair_index = format_index(start_index + len(plan_pairs))
        names = build_pair_names(base, pair_index)
        role_records = {}
        for record, role in ((first, first_role), (second, second_role)):
            target = target_leaf_name(record["node"], names[role])
            role_records[role] = {
                "node": record["node"],
                "original": leaf_name(record["node"]),
                "target": target,
                "faces": record["faces"],
                "bounds": record["bounds"],
            }

        try:
            _preflight_target(role_records["high"]["node"], role_records["high"]["target"])
            _preflight_target(role_records["low"]["node"], role_records["low"]["target"])
        except RenameError:
            unresolved.append((first["node"], "target_conflict"))
            unresolved.append((second["node"], "target_conflict"))
            continue

        plan_pairs.append(
            {
                "index_text": pair_index,
                "high": role_records["high"],
                "low": role_records["low"],
                "score": pair["score"],
                "center_norm": pair["center_norm"],
                "size_mismatch": pair["size_mismatch"],
            }
        )

    paired_nodes = {
        item[role]["node"]
        for item in plan_pairs
        for role in ("high", "low")
    }
    for record in records:
        if record["node"] not in paired_nodes and not any(record["node"] == item[0] for item in unresolved):
            unresolved.append((record["node"], "unresolved"))

    unresolved = sorted(set(unresolved), key=lambda item: (item[0], item[1]))
    ready = bool(plan_pairs) and not unresolved and len(paired_nodes) == len(records)
    signature = _analysis_signature(base, index_text, records, plan_pairs) if ready else None

    return {
        "ready": ready,
        "pairs": plan_pairs,
        "unresolved": unresolved,
        "signature": signature,
        "pair_count": len(plan_pairs),
        "next_index": advance_index_text(index_text, len(plan_pairs)) if ready else format_index(start_index),
    }


def auto_analysis_lines(analysis: dict) -> list[str]:
    lines = []
    for pair in analysis["pairs"]:
        lines.append(
            "{} | HIGH {} ({} faces) -> {} | LOW {} ({} faces) -> {}".format(
                pair["index_text"],
                pair["high"]["original"],
                pair["high"]["faces"],
                pair["high"]["target"],
                pair["low"]["original"],
                pair["low"]["faces"],
                pair["low"]["target"],
            )
        )
    for node, reason in analysis["unresolved"]:
        lines.append("UNRESOLVED | {} | {}".format(leaf_name(node), reason))
    if not lines:
        lines.append("No pair candidates found.")
    return lines


def rename_auto_pairs(base: str, index_text: str, expected_signature) -> dict:
    _require_maya()
    if expected_signature is None:
        raise RenameError("Analyze Auto Pairs before applying.")

    analysis = analyze_auto_pairs(base, index_text)
    if not analysis["ready"]:
        raise RenameError("Auto-pair analysis is no longer ready. Analyze again.")
    if analysis["signature"] != expected_signature:
        raise RenameError("Selection, transforms, topology, or naming inputs changed. Analyze again.")

    all_targets = []
    for pair in analysis["pairs"]:
        for role in ("high", "low"):
            all_targets.append(pair[role]["target"])
    if len(all_targets) != len(set(all_targets)):
        raise RenameError("Auto-pair plan contains duplicate target names.")

    rename_plan = []
    for pair in analysis["pairs"]:
        for role in ("high", "low"):
            item = pair[role]
            _preflight_target(item["node"], item["target"])
            rename_plan.append(
                {
                    "node": item["node"],
                    "target": item["target"],
                    "original": item["original"],
                    "role": role,
                    "index_text": pair["index_text"],
                }
            )

    chunk_open = False
    renamed_records = []
    try:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK_AUTO)
        chunk_open = True
        for item in rename_plan:
            renamed_long = _rename_exact(item["node"], item["target"], item["original"])
            renamed_records.append({"node": renamed_long, "original": item["original"]})
            item["node"] = renamed_long

        return {
            "pair_count": analysis["pair_count"],
            "renamed_count": len(rename_plan),
            "next_index": analysis["next_index"],
            "pairs": analysis["pairs"],
        }
    except Exception as exc:
        rollback_errors = []
        for record in reversed(renamed_records):
            try:
                if cmds.objExists(record["node"]):
                    cmds.rename(record["node"], record["original"])
            except Exception as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        if rollback_errors:
            raise RenameError(
                "Auto-pair rename failed and rollback was incomplete. Use Undo immediately. "
                "Details: {}".format(" | ".join(rollback_errors))
            )
        if isinstance(exc, RenameError):
            raise
        raise RenameError("Auto-pair rename failed: {}".format(exc))
    finally:
        if chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass


def _set_status(status_control, message: str, good: bool):
    color = (0.30, 0.72, 0.42) if good else (0.90, 0.34, 0.36)
    cmds.text(
        status_control,
        edit=True,
        label=message,
        font="smallPlainLabelFont",
        backgroundColor=color,
    )


def show():
    _require_maya()

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title=WINDOW_TITLE,
        sizeable=True,
        widthHeight=(620, 570),
    )

    root = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="left")
    cmds.separator(height=8, style="none")
    cmds.text(label="Sequential + High / Low + Auto Pair", align="left", font="boldLabelFont")
    cmds.text(
        label="V3 adds Analyze -> Preview -> Apply for multiple High/Low pairs.",
        align="left",
        font="smallPlainLabelFont",
    )

    cmds.rowColumnLayout(
        numberOfColumns=2,
        columnWidth=[(1, 110), (2, 475)],
        columnSpacing=[(1, 8), (2, 0)],
    )
    cmds.text(label="Base Name", align="left")
    base_field = cmds.textField(text="A")
    cmds.text(label="Index", align="left")
    index_field = cmds.textField(text="01")
    cmds.text(label="Role (single)", align="left")
    role_field = cmds.textField(text="low")
    cmds.setParent(root)

    cmds.text(label="Single Preview", align="left", font="smallPlainLabelFont")
    preview_field = cmds.textField(text="A_01_low", editable=False)
    cmds.text(label="Pair Preview", align="left", font="smallPlainLabelFont")
    pair_preview_field = cmds.textField(text="A_01_high  /  A_01_low", editable=False)

    auto_state = {"signature": None}
    auto_preview = None
    status = None

    def invalidate_auto():
        auto_state["signature"] = None
        if auto_preview:
            cmds.textScrollList(auto_preview, edit=True, removeAll=True)
            cmds.textScrollList(auto_preview, edit=True, append="Analyze selection to build V3 preview.")

    def update_preview(*_):
        base = cmds.textField(base_field, query=True, text=True)
        index_text = cmds.textField(index_field, query=True, text=True)
        role = cmds.textField(role_field, query=True, text=True)
        try:
            single_preview = build_name(base, index_text, role)
            pair_preview = build_pair_names(base, index_text)
            cmds.textField(preview_field, edit=True, text=single_preview)
            cmds.textField(
                pair_preview_field,
                edit=True,
                text="{}  /  {}".format(pair_preview["high"], pair_preview["low"]),
            )
            if status:
                _set_status(status, "Ready", True)
        except RenameError as exc:
            cmds.textField(preview_field, edit=True, text="—")
            cmds.textField(pair_preview_field, edit=True, text="—")
            if status:
                _set_status(status, str(exc), False)
        invalidate_auto()

    def do_rename():
        base = cmds.textField(base_field, query=True, text=True)
        index_text = cmds.textField(index_field, query=True, text=True)
        role = cmds.textField(role_field, query=True, text=True)
        try:
            result = rename_selected(base, index_text, role)
        except RenameError as exc:
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))
            return
        cmds.textField(index_field, edit=True, text=result["next_index"])
        update_preview()
        _set_status(
            status,
            "Renamed: {} -> {} | Next index: {}".format(
                result["old_name"], result["new_name"], result["next_index"]
            ),
            True,
        )

    def do_pair_rename():
        base = cmds.textField(base_field, query=True, text=True)
        index_text = cmds.textField(index_field, query=True, text=True)
        try:
            result = rename_pair_high_low(base, index_text)
        except RenameError as exc:
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))
            return
        cmds.textField(index_field, edit=True, text=result["next_index"])
        update_preview()
        _set_status(
            status,
            "Pair renamed | high: {} faces | low: {} faces | Next index: {}".format(
                result["high"]["faces"], result["low"]["faces"], result["next_index"]
            ),
            True,
        )

    def do_auto_analyze():
        base = cmds.textField(base_field, query=True, text=True)
        index_text = cmds.textField(index_field, query=True, text=True)
        try:
            analysis = analyze_auto_pairs(base, index_text)
        except RenameError as exc:
            invalidate_auto()
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))
            return

        cmds.textScrollList(auto_preview, edit=True, removeAll=True)
        for line in auto_analysis_lines(analysis):
            cmds.textScrollList(auto_preview, edit=True, append=line)

        if analysis["ready"]:
            auto_state["signature"] = analysis["signature"]
            _set_status(
                status,
                "Analyzed {} pairs. Preview is ready; Apply will re-check before renaming.".format(
                    analysis["pair_count"]
                ),
                True,
            )
        else:
            auto_state["signature"] = None
            _set_status(
                status,
                "Analysis found unresolved or ambiguous objects. Nothing was renamed.",
                False,
            )

    def do_auto_apply():
        base = cmds.textField(base_field, query=True, text=True)
        index_text = cmds.textField(index_field, query=True, text=True)
        try:
            result = rename_auto_pairs(base, index_text, auto_state["signature"])
        except RenameError as exc:
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))
            return
        cmds.textField(index_field, edit=True, text=result["next_index"])
        invalidate_auto()
        try:
            cmds.textField(
                preview_field,
                edit=True,
                text=build_name(base, result["next_index"], cmds.textField(role_field, query=True, text=True)),
            )
            next_pair = build_pair_names(base, result["next_index"])
            cmds.textField(
                pair_preview_field,
                edit=True,
                text="{}  /  {}".format(next_pair["high"], next_pair["low"]),
            )
        except RenameError:
            pass
        _set_status(
            status,
            "Applied {} auto pairs / {} models. Next index: {}".format(
                result["pair_count"], result["renamed_count"], result["next_index"]
            ),
            True,
        )

    def reset_index():
        cmds.textField(index_field, edit=True, text="01")
        update_preview()
        _set_status(status, "Index reset to 01", True)

    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, columnWidth3=(250, 250, 100))
    cmds.button(label="Rename Selected", height=34, command=lambda *_: do_rename())
    cmds.button(label="Rename Pair High / Low", height=34, command=lambda *_: do_pair_rename())
    cmds.button(label="Reset to 01", height=34, command=lambda *_: reset_index())
    cmds.setParent(root)

    cmds.separator(height=8, style="in")
    cmds.text(label="V3 Auto Pair", align="left", font="boldLabelFont")
    cmds.text(
        label=(
            "Pairing uses world-space center proximity + bounding-box size similarity, then only "
            "accepts mutual best matches. Ambiguous/unpaired objects block Apply."
        ),
        align="left",
        font="smallPlainLabelFont",
        wordWrap=True,
    )

    auto_preview = cmds.textScrollList(numberOfRows=8, allowMultiSelection=False, height=190)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnWidth2=(300, 300))
    cmds.button(label="Analyze Auto Pairs", height=36, command=lambda *_: do_auto_analyze())
    cmds.button(label="Apply Auto Pairs", height=36, command=lambda *_: do_auto_apply())
    cmds.setParent(root)

    status = cmds.text(
        label="Ready",
        align="left",
        height=42,
        backgroundColor=(0.22, 0.22, 0.22),
        wordWrap=True,
    )

    for control in (base_field, index_field, role_field):
        cmds.textField(control, edit=True, changeCommand=update_preview)

    invalidate_auto()
    cmds.separator(height=8, style="none")
    cmds.showWindow(window)
    return window


if __name__ == "__main__":
    show()
