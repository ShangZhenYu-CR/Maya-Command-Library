# -*- coding: utf-8 -*-
"""MCL Model Renamer V3 extension.

Requires the accepted V2 module ``mcl_model_renamer.py`` beside this file.
V3 adds multi-selection spatial analysis, preview, and batch apply while leaving
V1/V2 source unchanged.
"""
from __future__ import annotations

import math

import mcl_model_renamer as base

cmds = base.cmds

WINDOW_NAME = "MCLModelRenamerV3Window"
WINDOW_TITLE = "MCL Model Renamer V3"
UNDO_CHUNK_AUTO = "MCL_Model_Renamer_V3_AutoPairs"
AUTO_CENTER_LIMIT = 0.25
AUTO_SIZE_LIMIT = 0.35
AUTO_SIZE_WEIGHT = 0.35
AUTO_AMBIGUITY_GAP = 0.05
ALLOW_SELECTED_NAME_REUSE_DEFAULT = True
_EPSILON = 1e-8


def bbox_center_size(bounds):
    if bounds is None or len(bounds) != 6:
        raise base.RenameError("World bounding box must contain 6 numeric values.")
    values = tuple(float(value) for value in bounds)
    xmin, ymin, zmin, xmax, ymax, zmax = values
    if xmax < xmin or ymax < ymin or zmax < zmin:
        raise base.RenameError("World bounding box minimum exceeds maximum.")
    center = ((xmin + xmax) * 0.5, (ymin + ymax) * 0.5, (zmin + zmax) * 0.5)
    size = (xmax - xmin, ymax - ymin, zmax - zmin)
    return center, size


def _distance3(a, b):
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def bbox_pair_metric(first_bounds, second_bounds):
    first_center, first_size = bbox_center_size(first_bounds)
    second_center, second_size = bbox_center_size(second_bounds)
    first_diag = math.sqrt(sum(value * value for value in first_size))
    second_diag = math.sqrt(sum(value * value for value in second_size))
    scale = max((first_diag + second_diag) * 0.5, _EPSILON)
    center_norm = _distance3(first_center, second_center) / scale
    size_mismatch = sum(
        abs(a - b) / max(abs(a), abs(b), _EPSILON)
        for a, b in zip(first_size, second_size)
    ) / 3.0
    score = center_norm + AUTO_SIZE_WEIGHT * size_mismatch
    return {
        "center_norm": center_norm,
        "size_mismatch": size_mismatch,
        "score": score,
        "eligible": center_norm <= AUTO_CENTER_LIMIT and size_mismatch <= AUTO_SIZE_LIMIT,
    }


def _pair_sort_key(first_record, second_record):
    a, _ = bbox_center_size(first_record["bounds"])
    b, _ = bbox_center_size(second_record["bounds"])
    center = tuple((x + y) * 0.5 for x, y in zip(a, b))
    nodes = tuple(sorted((first_record["node"], second_record["node"])))
    return (round(center[0], 8), round(center[2], 8), round(center[1], 8), nodes[0], nodes[1])


def auto_pair_records(records):
    """Return conservative mutual-best pairs without using selection order."""
    by_node = {record["node"]: record for record in records}
    if len(by_node) != len(records):
        raise base.RenameError("Auto-pair records must have unique nodes.")
    best = {}
    reasons = {}
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
            reasons[node] = "no_eligible_match"
            continue
        if len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= AUTO_AMBIGUITY_GAP:
            reasons[node] = "ambiguous_match"
            continue
        best[node] = candidates[0]

    paired = set()
    pairs = []
    for node in sorted(by_node):
        if node in paired or node not in best:
            continue
        other = best[node][1]
        other_best = best.get(other)
        if other_best is None or other_best[1] != node:
            reasons.setdefault(node, "not_mutual_best")
            continue
        if other in paired:
            continue
        metric = best[node][2]
        pairs.append({
            "first": by_node[node], "second": by_node[other],
            "score": metric["score"], "center_norm": metric["center_norm"],
            "size_mismatch": metric["size_mismatch"],
        })
        paired.update((node, other))
    pairs.sort(key=lambda item: _pair_sort_key(item["first"], item["second"]))
    unresolved = [(node, reasons.get(node, "not_mutual_best")) for node in sorted(by_node) if node not in paired]
    return {"pairs": pairs, "unresolved": unresolved}


def _selected_mesh_transforms():
    raw = cmds.ls(selection=True, long=True, flatten=True) or []
    if len(raw) < 2:
        raise base.RenameError("Select at least 2 mesh transforms.")
    result = [base._validate_mesh_transform(node) for node in raw]
    if len(set(result)) != len(result):
        raise base.RenameError("Select distinct mesh transforms.")
    return result


def _long_name(node):
    return (cmds.ls(node, long=True) or [node])[0]


def _target_conflicts(node, target_leaf, selected_nodes, allow_selected_name_reuse=True):
    """Return target occupiers that must block the V3 batch.

    When allow_selected_name_reuse is enabled, an occupier is ignored only when
    it is itself part of the current V3 selection. Those selected objects will
    be moved to temporary names before final names are applied.
    """
    current_long = _long_name(node)
    selected_long = {_long_name(item) for item in selected_nodes}
    matches = cmds.ls(target_leaf, long=True) or []
    conflicts = []

    if base.leaf_name(current_long) == target_leaf and not allow_selected_name_reuse:
        conflicts.append(current_long)

    for match in matches:
        match_long = _long_name(match)
        if allow_selected_name_reuse and match_long in selected_long:
            continue
        conflicts.append(match_long)

    return sorted(set(conflicts))


def _unique_temp_leaf(node, prefix, ordinal, reserved_names):
    namespace = base.namespace_prefix(node)
    counter = max(int(ordinal), 1)
    while True:
        candidate = "{}__MCL_V3_{}_{:03d}__".format(namespace, prefix, counter)
        if candidate not in reserved_names and not (cmds.ls(candidate, long=True) or []):
            return candidate
        counter += 1


def _rename_batch_exact(node, target_leaf):
    renamed = cmds.rename(node, target_leaf)
    renamed_long = _long_name(renamed)
    if base.leaf_name(renamed_long) != target_leaf:
        raise base.RenameError(
            "Maya did not apply the exact requested name '{}'; batch rollback will run.".format(
                target_leaf
            )
        )
    return renamed_long


def _rollback_batch(records):
    """Best-effort two-phase rollback to avoid original names blocking each other."""
    errors = []
    reserved = {record["original"] for record in records}

    for index, record in enumerate(records, 1):
        current = record.get("current", record["node"])
        if not cmds.objExists(current):
            errors.append("missing node during rollback: {}".format(current))
            continue
        if base.leaf_name(current) == record["original"]:
            record["current"] = current
            continue
        try:
            rollback_temp = _unique_temp_leaf(current, "ROLLBACK", index, reserved)
            record["current"] = _rename_batch_exact(current, rollback_temp)
        except Exception as exc:
            errors.append(str(exc))

    for record in records:
        current = record.get("current", record["node"])
        if not cmds.objExists(current):
            continue
        if base.leaf_name(current) == record["original"]:
            continue
        try:
            record["current"] = _rename_batch_exact(current, record["original"])
        except Exception as exc:
            errors.append(str(exc))

    return errors


def _world_bbox(node):
    try:
        bounds = cmds.exactWorldBoundingBox(node)
    except Exception as exc:
        raise base.RenameError("Could not read world bounding box for '{}': {}".format(base.leaf_name(node), exc))
    bbox_center_size(bounds)
    return tuple(float(value) for value in bounds)


def _round_bounds(bounds):
    return tuple(round(float(value), 6) for value in bounds)


def _analysis_signature(base_name, index_text, records, pairs, allow_selected_name_reuse):
    record_state = tuple(sorted((r["node"], r["faces"], _round_bounds(r["bounds"])) for r in records))
    pair_state = tuple((
        pair["index_text"], pair["high"]["node"], pair["high"]["target"], pair["high"]["faces"],
        pair["low"]["node"], pair["low"]["target"], pair["low"]["faces"],
    ) for pair in pairs)
    return (
        base.validate_base(base_name),
        base.format_index(base.parse_index(index_text)),
        bool(allow_selected_name_reuse),
        record_state,
        pair_state,
    )


def analyze_auto_pairs(base_name, index_text, allow_selected_name_reuse=ALLOW_SELECTED_NAME_REUSE_DEFAULT):
    """Read-only V3 analysis. No scene nodes are renamed here."""
    base.validate_base(base_name)
    start_index = base.parse_index(index_text)
    records = [{"node": node, "bounds": _world_bbox(node), "faces": base._face_count(node)} for node in _selected_mesh_transforms()]
    selected_nodes = {record["node"] for record in records}
    pairing = auto_pair_records(records)
    unresolved = list(pairing["unresolved"])
    pairs = []
    for candidate in pairing["pairs"]:
        first, second = candidate["first"], candidate["second"]
        try:
            first_role, second_role = base.pair_roles_for_face_counts(first["faces"], second["faces"])
        except base.RenameError:
            unresolved.extend(((first["node"], "same_face_count"), (second["node"], "same_face_count")))
            continue
        pair_index = base.format_index(start_index + len(pairs))
        names = base.build_pair_names(base_name, pair_index)
        role_items = {}
        for record, role in ((first, first_role), (second, second_role)):
            role_items[role] = {
                "node": record["node"], "original": base.leaf_name(record["node"]),
                "target": base.target_leaf_name(record["node"], names[role]),
                "faces": record["faces"], "bounds": record["bounds"],
            }
        target_conflicts = []
        for role in ("high", "low"):
            item = role_items[role]
            conflicts = _target_conflicts(
                item["node"],
                item["target"],
                selected_nodes,
                allow_selected_name_reuse=allow_selected_name_reuse,
            )
            if conflicts:
                target_conflicts.append((item["target"], conflicts))

        if target_conflicts:
            conflict_names = ", ".join(target for target, _ in target_conflicts)
            reason = "target_conflict:{}".format(conflict_names)
            unresolved.extend(((first["node"], reason), (second["node"], reason)))
            continue
        pairs.append({
            "index_text": pair_index, "high": role_items["high"], "low": role_items["low"],
            "score": candidate["score"], "center_norm": candidate["center_norm"],
            "size_mismatch": candidate["size_mismatch"],
        })

    paired_nodes = {pair[role]["node"] for pair in pairs for role in ("high", "low")}
    unresolved_nodes = {node for node, _ in unresolved}
    for record in records:
        if record["node"] not in paired_nodes and record["node"] not in unresolved_nodes:
            unresolved.append((record["node"], "unresolved"))
    unresolved = sorted(set(unresolved), key=lambda item: (item[0], item[1]))
    ready = bool(pairs) and not unresolved and len(paired_nodes) == len(records)
    signature = (
        _analysis_signature(
            base_name,
            index_text,
            records,
            pairs,
            allow_selected_name_reuse=allow_selected_name_reuse,
        )
        if ready
        else None
    )
    return {
        "ready": ready,
        "pairs": pairs,
        "unresolved": unresolved,
        "signature": signature,
        "pair_count": len(pairs),
        "next_index": base.format_index(start_index + len(pairs)) if ready else base.format_index(start_index),
        "allow_selected_name_reuse": bool(allow_selected_name_reuse),
    }


def analysis_lines(analysis):
    lines = [
        "{} | HIGH {} ({}f) -> {} | LOW {} ({}f) -> {}".format(
            pair["index_text"], pair["high"]["original"], pair["high"]["faces"], pair["high"]["target"],
            pair["low"]["original"], pair["low"]["faces"], pair["low"]["target"],
        ) for pair in analysis["pairs"]
    ]
    lines.extend("UNRESOLVED | {} | {}".format(base.leaf_name(node), reason) for node, reason in analysis["unresolved"])
    return lines or ["No pair candidates found."]


def rename_auto_pairs(
    base_name,
    index_text,
    expected_signature,
    allow_selected_name_reuse=ALLOW_SELECTED_NAME_REUSE_DEFAULT,
):
    if expected_signature is None:
        raise base.RenameError("Analyze Auto Pairs before applying.")

    analysis = analyze_auto_pairs(
        base_name,
        index_text,
        allow_selected_name_reuse=allow_selected_name_reuse,
    )
    if not analysis["ready"]:
        raise base.RenameError("Auto-pair analysis is no longer ready. Analyze again.")
    if analysis["signature"] != expected_signature:
        raise base.RenameError("Selection, transforms, topology, naming inputs, or conflict settings changed. Analyze again.")

    plan = []
    targets = []
    selected_nodes = {
        pair[role]["node"]
        for pair in analysis["pairs"]
        for role in ("high", "low")
    }

    for pair in analysis["pairs"]:
        for role in ("high", "low"):
            item = pair[role]
            conflicts = _target_conflicts(
                item["node"],
                item["target"],
                selected_nodes,
                allow_selected_name_reuse=allow_selected_name_reuse,
            )
            if conflicts:
                raise base.RenameError(
                    "Target name '{}' is occupied by an unselected object: {}".format(
                        item["target"], conflicts[0]
                    )
                )
            targets.append(item["target"])
            plan.append(
                {
                    "node": item["node"],
                    "current": item["node"],
                    "target": item["target"],
                    "original": item["original"],
                }
            )

    if len(targets) != len(set(targets)):
        raise base.RenameError("Auto-pair plan contains duplicate target names.")

    chunk_open = False
    try:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK_AUTO)
        chunk_open = True

        reserved_names = set(targets) | {item["original"] for item in plan}

        # Phase 1: release every selected object's current leaf name. This makes
        # selected-object name reuse safe even when final names form swaps/cycles.
        for index, item in enumerate(plan, 1):
            temp_leaf = _unique_temp_leaf(
                item["current"],
                "TMP",
                index,
                reserved_names,
            )
            item["current"] = _rename_batch_exact(item["current"], temp_leaf)

        # Phase 2: all selected old names are free, so final targets can be
        # written without Maya auto-suffixing or ordering dependencies.
        for item in plan:
            item["current"] = _rename_batch_exact(item["current"], item["target"])

        return {
            "pair_count": analysis["pair_count"],
            "renamed_count": len(plan),
            "next_index": analysis["next_index"],
        }

    except Exception as exc:
        rollback_errors = _rollback_batch(plan)
        if rollback_errors:
            raise base.RenameError(
                "Auto-pair rename failed and rollback was incomplete. Use Undo immediately. "
                "Details: {}".format(" | ".join(rollback_errors))
            )
        if isinstance(exc, base.RenameError):
            raise
        raise base.RenameError("Auto-pair rename failed: {}".format(exc))
    finally:
        if chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass


def _status(control, message, good=True):
    cmds.text(control, edit=True, label=message, backgroundColor=((0.30, 0.72, 0.42) if good else (0.90, 0.34, 0.36)))


def show():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    window = cmds.window(WINDOW_NAME, title=WINDOW_TITLE, sizeable=True, widthHeight=(620, 555))
    root = cmds.columnLayout(adjustableColumn=True, rowSpacing=7)
    cmds.text(label="MCL Model Renamer V3", font="boldLabelFont", align="left")
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 110), (2, 475)])
    cmds.text(label="Base Name", align="left"); base_field = cmds.textField(text="A")
    cmds.text(label="Index", align="left"); index_field = cmds.textField(text="01")
    cmds.text(label="Role (single)", align="left"); role_field = cmds.textField(text="low")
    cmds.setParent(root)
    single_preview = cmds.textField(text="A_01_low", editable=False)
    pair_preview = cmds.textField(text="A_01_high / A_01_low", editable=False)
    allow_selected_reuse = cmds.checkBox(
        label="Allow Selected Name Reuse",
        value=ALLOW_SELECTED_NAME_REUSE_DEFAULT,
        annotation=(
            "Allow selected objects to temporarily occupy V3 target names. "
            "Unselected target-name conflicts still block Apply."
        ),
    )
    status = cmds.text(label="Ready", height=36, backgroundColor=(0.22, 0.22, 0.22), wordWrap=True)
    auto_list = cmds.textScrollList(numberOfRows=8, height=190)
    state = {"signature": None}

    def invalidate():
        state["signature"] = None
        cmds.textScrollList(auto_list, edit=True, removeAll=True)
        cmds.textScrollList(auto_list, edit=True, append="Analyze selection to build V3 preview.")

    def refresh(*_):
        try:
            b = cmds.textField(base_field, query=True, text=True)
            i = cmds.textField(index_field, query=True, text=True)
            r = cmds.textField(role_field, query=True, text=True)
            cmds.textField(single_preview, edit=True, text=base.build_name(b, i, r))
            names = base.build_pair_names(b, i)
            cmds.textField(pair_preview, edit=True, text="{} / {}".format(names["high"], names["low"]))
            _status(status, "Ready", True)
        except base.RenameError as exc:
            _status(status, str(exc), False)
        invalidate()

    def single(*_):
        try:
            result = base.rename_selected(cmds.textField(base_field, q=True, text=True), cmds.textField(index_field, q=True, text=True), cmds.textField(role_field, q=True, text=True))
            cmds.textField(index_field, edit=True, text=result["next_index"]); refresh(); _status(status, "Single rename complete. Next index: {}".format(result["next_index"]), True)
        except base.RenameError as exc:
            _status(status, str(exc), False); cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    def pair(*_):
        try:
            result = base.rename_pair_high_low(cmds.textField(base_field, q=True, text=True), cmds.textField(index_field, q=True, text=True))
            cmds.textField(index_field, edit=True, text=result["next_index"]); refresh(); _status(status, "Pair rename complete. Next index: {}".format(result["next_index"]), True)
        except base.RenameError as exc:
            _status(status, str(exc), False); cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    def analyze(*_):
        try:
            result = analyze_auto_pairs(
                cmds.textField(base_field, q=True, text=True),
                cmds.textField(index_field, q=True, text=True),
                allow_selected_name_reuse=cmds.checkBox(allow_selected_reuse, q=True, value=True),
            )
            cmds.textScrollList(auto_list, edit=True, removeAll=True)
            for line in analysis_lines(result): cmds.textScrollList(auto_list, edit=True, append=line)
            state["signature"] = result["signature"] if result["ready"] else None
            _status(status, "Analyzed {} pairs. Ready to Apply.".format(result["pair_count"]) if result["ready"] else "Unresolved/ambiguous objects found. Nothing renamed.", result["ready"])
        except base.RenameError as exc:
            invalidate(); _status(status, str(exc), False); cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    def apply(*_):
        try:
            result = rename_auto_pairs(
                cmds.textField(base_field, q=True, text=True),
                cmds.textField(index_field, q=True, text=True),
                state["signature"],
                allow_selected_name_reuse=cmds.checkBox(allow_selected_reuse, q=True, value=True),
            )
            cmds.textField(index_field, edit=True, text=result["next_index"]); refresh(); _status(status, "Applied {} pairs / {} models. Next index: {}".format(result["pair_count"], result["renamed_count"], result["next_index"]), True)
        except base.RenameError as exc:
            _status(status, str(exc), False); cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    for control in (base_field, index_field, role_field):
        cmds.textField(control, edit=True, changeCommand=refresh)
    cmds.checkBox(allow_selected_reuse, edit=True, changeCommand=lambda *_: invalidate())
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1)
    cmds.button(label="Rename Selected", command=single); cmds.button(label="Rename Pair High / Low", command=pair); cmds.button(label="Reset to 01", command=lambda *_: (cmds.textField(index_field, edit=True, text="01"), refresh()))
    cmds.setParent(root)
    cmds.separator(style="in"); cmds.text(label="V3 Auto Pair: Analyze -> Preview -> Apply", font="boldLabelFont", align="left")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.button(label="Analyze Auto Pairs", height=36, command=analyze); cmds.button(label="Apply Auto Pairs", height=36, command=apply)
    cmds.setParent(root)
    invalidate(); cmds.showWindow(window); return window
