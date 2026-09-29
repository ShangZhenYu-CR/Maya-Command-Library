# -*- coding: utf-8 -*-
"""MCL Model Renamer V2.

V1: sequential single-model naming using {Base}_{Index}_{Role}.
V2: two-model High/Low naming based on polygon face count.
"""

from __future__ import annotations

import re

try:
    from maya import cmds
except ImportError:  # Allows host-independent tests of pure helpers.
    cmds = None


WINDOW_NAME = "MCLModelRenamerWindow"
WINDOW_TITLE = "MCL Model Renamer"
UNDO_CHUNK_SINGLE = "MCL_Model_Renamer_V1_Single"
UNDO_CHUNK_PAIR = "MCL_Model_Renamer_V2_Pair"
MIN_INDEX_WIDTH = 2

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


def leaf_name(node: str) -> str:
    return (node or "").rsplit("|", 1)[-1]


def namespace_prefix(node: str) -> str:
    leaf = leaf_name(node)
    if ":" not in leaf:
        return ""
    return leaf.rsplit(":", 1)[0] + ":"


def target_leaf_name(node: str, generated_name: str) -> str:
    return namespace_prefix(node) + generated_name


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


def _selected_mesh_transforms(expected_count: int) -> list[str]:
    _require_maya()
    raw = cmds.ls(selection=True, long=True, flatten=True) or []
    if len(raw) != expected_count:
        noun = "mesh transform" if expected_count == 1 else "mesh transforms"
        raise RenameError("Select exactly {} {}.".format(expected_count, noun))

    result = [_validate_mesh_transform(node) for node in raw]
    if len(set(result)) != expected_count:
        raise RenameError("Select distinct mesh transforms.")
    return result


def _selected_mesh_transform() -> str:
    return _selected_mesh_transforms(1)[0]


def _selected_mesh_pair() -> tuple[str, str]:
    pair = _selected_mesh_transforms(2)
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
    """V1 behavior: rename exactly one selected local mesh transform."""
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
    """V2 behavior: classify exactly two meshes by Face Count and rename as a pair."""
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
            renamed_records.append(
                {
                    "node": renamed_long,
                    "original": item["original"],
                }
            )
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
    """Open the MCL Model Renamer V2 Maya window."""
    _require_maya()

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title=WINDOW_TITLE,
        sizeable=False,
        widthHeight=(360, 345),
    )

    root = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="left")
    cmds.separator(height=8, style="none")
    cmds.text(label="Sequential + High / Low naming", align="left", font="boldLabelFont")
    cmds.text(
        label="Single: {Base}_{Index}_{Role}  |  Pair: _high / _low",
        align="left",
        font="smallPlainLabelFont",
    )

    cmds.rowColumnLayout(
        numberOfColumns=2,
        columnWidth=[(1, 100), (2, 235)],
        columnSpacing=[(1, 8), (2, 0)],
    )
    cmds.text(label="Base Name", align="left")
    base_field = cmds.textField(text="A")
    cmds.text(label="Index", align="left")
    index_field = cmds.textField(text="01")
    cmds.text(label="Role (single)", align="left")
    role_field = cmds.textField(text="low")
    cmds.setParent(root)

    cmds.separator(height=4, style="none")
    cmds.text(label="Single Preview", align="left", font="smallPlainLabelFont")
    preview_field = cmds.textField(text="A_01_low", editable=False)
    cmds.text(label="Pair Preview", align="left", font="smallPlainLabelFont")
    pair_preview_field = cmds.textField(text="A_01_high  /  A_01_low", editable=False)

    status = cmds.text(
        label="Ready",
        align="left",
        height=34,
        backgroundColor=(0.22, 0.22, 0.22),
        wordWrap=True,
    )

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
            _set_status(status, "Ready", True)
        except RenameError as exc:
            cmds.textField(preview_field, edit=True, text="—")
            cmds.textField(pair_preview_field, edit=True, text="—")
            _set_status(status, str(exc), False)

    def do_rename(*_):
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

    def do_pair_rename(*_):
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
                result["high"]["faces"],
                result["low"]["faces"],
                result["next_index"],
            ),
            True,
        )

    def reset_index(*_):
        cmds.textField(index_field, edit=True, text="01")
        update_preview()
        _set_status(status, "Index reset to 01", True)

    for control in (base_field, index_field, role_field):
        cmds.textField(control, edit=True, changeCommand=update_preview)

    cmds.button(label="Rename Selected", height=34, command=do_rename)
    cmds.button(label="Rename Pair High / Low", height=38, command=do_pair_rename)
    cmds.button(label="Reset to 01", height=28, command=reset_index)
    cmds.text(
        label=(
            "V2 pair mode: select exactly 2 local mesh transforms. Higher Face Count = high; "
            "lower Face Count = low. Equal counts stop without renaming."
        ),
        align="left",
        font="smallPlainLabelFont",
        wordWrap=True,
    )
    cmds.separator(height=8, style="none")

    cmds.showWindow(window)
    return window


if __name__ == "__main__":
    show()
