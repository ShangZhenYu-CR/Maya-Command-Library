# -*- coding: utf-8 -*-
"""MCL Model Renamer V1.

A lightweight Maya tool for sequential model naming using the fixed pattern:
    {Base}_{Index}_{Role}

V1 intentionally handles exactly one local mesh transform at a time.
"""

from __future__ import annotations

import re

try:
    from maya import cmds
except ImportError:  # Allows host-independent tests of pure helpers.
    cmds = None


WINDOW_NAME = "MCLModelRenamerWindow"
WINDOW_TITLE = "MCL Model Renamer"
UNDO_CHUNK_NAME = "MCL_Model_Renamer_V1"
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


def _selected_mesh_transform() -> str:
    _require_maya()
    raw = cmds.ls(selection=True, long=True, flatten=True) or []
    if not raw:
        raise RenameError("Select exactly one mesh transform.")
    if len(raw) != 1:
        raise RenameError("Select exactly one mesh transform.")

    node = raw[0]
    if "." in node:
        raise RenameError("Component selection is not supported in V1. Select the transform.")
    if not cmds.objExists(node):
        raise RenameError("The selected object no longer exists.")
    if cmds.nodeType(node) != "transform":
        raise RenameError("Select a mesh transform, not a shape or another node type.")

    shapes = cmds.listRelatives(node, shapes=True, fullPath=True, noIntermediate=True) or []
    mesh_shapes = [shape for shape in shapes if cmds.nodeType(shape) == "mesh"]
    if not mesh_shapes:
        raise RenameError("The selected transform does not contain a non-intermediate mesh shape.")

    try:
        if cmds.referenceQuery(node, isNodeReferenced=True):
            raise RenameError("Referenced objects are not renamed in V1.")
    except RenameError:
        raise
    except Exception:
        raise RenameError("Could not determine whether the selected object is referenced.")

    try:
        lock_state = cmds.lockNode(node, query=True, lock=True) or [False]
        if any(lock_state):
            raise RenameError("The selected object is locked and cannot be renamed.")
    except RenameError:
        raise
    except Exception:
        raise RenameError("Could not determine the selected object's lock state.")

    return (cmds.ls(node, long=True) or [node])[0]


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


def rename_selected(base: str, index_text: str, role: str) -> dict:
    """Validate and rename exactly one selected local mesh transform.

    Returns a result dictionary used by the UI. The index is advanced only after
    Maya confirms the exact requested leaf name.
    """
    _require_maya()

    generated = build_name(base, index_text, role)
    node = _selected_mesh_transform()
    target_leaf = target_leaf_name(node, generated)
    _preflight_target(node, target_leaf)

    original_leaf = leaf_name(node)
    chunk_open = False

    try:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK_NAME)
        chunk_open = True

        renamed = cmds.rename(node, target_leaf)
        renamed_long = (cmds.ls(renamed, long=True) or [renamed])[0]
        actual_leaf = leaf_name(renamed_long)

        if actual_leaf != target_leaf:
            try:
                cmds.rename(renamed_long, original_leaf)
            except Exception:
                raise RenameError(
                    "Maya did not apply the exact requested name and the original name "
                    "could not be restored automatically. Use Undo immediately."
                )
            raise RenameError(
                "Maya did not apply the exact requested name. No automatic suffix was accepted."
            )

        return {
            "old_name": original_leaf,
            "new_name": actual_leaf,
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


def _set_status(status_control, message: str, good: bool):
    color = (0.30, 0.72, 0.42) if good else (0.90, 0.34, 0.36)
    cmds.text(status_control, edit=True, label=message, font="smallPlainLabelFont")
    cmds.text(status_control, edit=True, backgroundColor=color)


def show():
    """Open the MCL Model Renamer V1 Maya window."""
    _require_maya()

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title=WINDOW_TITLE,
        sizeable=False,
        widthHeight=(340, 260),
    )

    root = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="left")
    cmds.separator(height=8, style="none")
    cmds.text(label="Sequential model naming", align="left", font="boldLabelFont")
    cmds.text(
        label="Pattern: {Base}_{Index}_{Role}",
        align="left",
        font="smallPlainLabelFont",
    )

    cmds.rowColumnLayout(
        numberOfColumns=2,
        columnWidth=[(1, 92), (2, 225)],
        columnSpacing=[(1, 8), (2, 0)],
    )
    cmds.text(label="Base Name", align="left")
    base_field = cmds.textField(text="A")
    cmds.text(label="Index", align="left")
    index_field = cmds.textField(text="01")
    cmds.text(label="Role", align="left")
    role_field = cmds.textField(text="low")
    cmds.setParent(root)

    cmds.separator(height=4, style="none")
    cmds.text(label="Preview", align="left", font="smallPlainLabelFont")
    preview_field = cmds.textField(text="A_01_low", editable=False)

    status = cmds.text(
        label="Ready",
        align="left",
        height=28,
        backgroundColor=(0.22, 0.22, 0.22),
    )

    def update_preview(*_):
        try:
            preview = build_name(
                cmds.textField(base_field, query=True, text=True),
                cmds.textField(index_field, query=True, text=True),
                cmds.textField(role_field, query=True, text=True),
            )
            cmds.textField(preview_field, edit=True, text=preview)
            _set_status(status, "Ready", True)
        except RenameError as exc:
            cmds.textField(preview_field, edit=True, text="—")
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
            "Renamed: {} -> {} | Next: {}".format(
                result["old_name"],
                result["new_name"],
                build_name(base, result["next_index"], role),
            ),
            True,
        )

    def reset_index(*_):
        cmds.textField(index_field, edit=True, text="01")
        update_preview()
        _set_status(status, "Index reset to 01", True)

    for control in (base_field, index_field, role_field):
        cmds.textField(control, edit=True, changeCommand=update_preview)

    cmds.button(label="Rename Selected", height=36, command=do_rename)
    cmds.button(label="Reset to 01", height=28, command=reset_index)
    cmds.text(
        label="V1: one local mesh transform at a time. Ctrl+Z restores the Maya rename.",
        align="left",
        font="smallPlainLabelFont",
        wordWrap=True,
    )
    cmds.separator(height=8, style="none")

    cmds.showWindow(window)
    return window


if __name__ == "__main__":
    show()
