# -*- coding: utf-8 -*-
"""MCL Proxy Pivot Matcher.

MCL-2 V1.2.

Workflow:
1. Put proxy meshes under the root group ``|proxy``.
2. Select one or more final mesh transforms.
3. Analyze conservative world-space Target -> Proxy matches.
4. Match Pivots, write Proxy T/R/S channel values exactly, and rebalance offsetParentMatrix to preserve the Target world matrix.

Spatial thresholds intentionally mirror the fixed MCL-1 V3 pairing approach
(commit 5c650ddea9b80c65769ff914e8cf1127c706208c), but this tool is standalone
and does not modify or depend on the MCL Model Renamer at runtime.
"""
from __future__ import annotations

import math

try:
    import maya.cmds as cmds
except Exception:  # Allows host-independent tests outside Maya.
    cmds = None

WINDOW_NAME = "MCLProxyPivotMatcherWindow"
WINDOW_TITLE = "MCL Proxy Pivot Matcher"
PROXY_ROOT = "|proxy"
UNDO_CHUNK = "MCL_Proxy_Pivot_Matcher"

CENTER_LIMIT = 0.25
SIZE_LIMIT = 0.35
SIZE_WEIGHT = 0.35
AMBIGUITY_GAP = 0.05
_EPSILON = 1e-8


class PivotMatchError(RuntimeError):
    pass


def _require_cmds():
    if cmds is None:
        raise PivotMatchError("maya.cmds is unavailable. Run this tool inside Autodesk Maya.")


def leaf_name(node):
    return str(node).rsplit("|", 1)[-1]


def bbox_center_size(bounds):
    if bounds is None or len(bounds) != 6:
        raise PivotMatchError("World bounding box must contain 6 numeric values.")
    values = tuple(float(value) for value in bounds)
    xmin, ymin, zmin, xmax, ymax, zmax = values
    if xmax < xmin or ymax < ymin or zmax < zmin:
        raise PivotMatchError("World bounding box minimum exceeds maximum.")
    center = ((xmin + xmax) * 0.5, (ymin + ymax) * 0.5, (zmin + zmax) * 0.5)
    size = (xmax - xmin, ymax - ymin, zmax - zmin)
    return center, size


def _distance3(a, b):
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def bbox_pair_metric(target_bounds, proxy_bounds):
    """Return the MCL conservative center/size pairing metric."""
    target_center, target_size = bbox_center_size(target_bounds)
    proxy_center, proxy_size = bbox_center_size(proxy_bounds)
    target_diag = math.sqrt(sum(value * value for value in target_size))
    proxy_diag = math.sqrt(sum(value * value for value in proxy_size))
    scale = max((target_diag + proxy_diag) * 0.5, _EPSILON)
    center_norm = _distance3(target_center, proxy_center) / scale
    size_mismatch = sum(
        abs(a - b) / max(abs(a), abs(b), _EPSILON)
        for a, b in zip(target_size, proxy_size)
    ) / 3.0
    score = center_norm + SIZE_WEIGHT * size_mismatch
    return {
        "center_norm": center_norm,
        "size_mismatch": size_mismatch,
        "score": score,
        "eligible": center_norm <= CENTER_LIMIT and size_mismatch <= SIZE_LIMIT,
    }


def _candidate_list(record, other_records):
    candidates = []
    for other in other_records:
        metric = bbox_pair_metric(record["bounds"], other["bounds"])
        if metric["eligible"]:
            candidates.append((metric["score"], other["node"], other, metric))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates


def pair_targets_to_proxies(target_records, proxy_records):
    """Conservative one-to-one bipartite matching.

    Each target and proxy chooses its best eligible counterpart. A pair is accepted
    only when both choices are mutual and neither side has a near-tie.
    Unused proxies are allowed; every selected target must resolve before Apply.
    """
    target_by_node = {record["node"]: record for record in target_records}
    proxy_by_node = {record["node"]: record for record in proxy_records}
    if len(target_by_node) != len(target_records):
        raise PivotMatchError("Target records must have unique nodes.")
    if len(proxy_by_node) != len(proxy_records):
        raise PivotMatchError("Proxy records must have unique nodes.")

    target_best = {}
    target_reasons = {}

    for target in sorted(target_by_node):
        candidates = _candidate_list(target_by_node[target], proxy_records)
        if not candidates:
            target_reasons[target] = "no_eligible_proxy"
            continue
        if len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= AMBIGUITY_GAP:
            target_reasons[target] = "ambiguous_proxy_candidates"
            continue
        target_best[target] = candidates[0]

    proxy_best = {}
    proxy_ambiguous = set()
    for proxy in sorted(proxy_by_node):
        candidates = _candidate_list(proxy_by_node[proxy], target_records)
        if not candidates:
            continue
        if len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= AMBIGUITY_GAP:
            proxy_ambiguous.add(proxy)
            continue
        proxy_best[proxy] = candidates[0]

    pairs = []
    paired_targets = set()
    paired_proxies = set()

    for target in sorted(target_by_node):
        if target not in target_best:
            continue
        score, proxy, proxy_record, metric = target_best[target]
        if proxy in proxy_ambiguous:
            target_reasons.setdefault(target, "proxy_has_ambiguous_targets")
            continue
        reverse = proxy_best.get(proxy)
        if reverse is None or reverse[1] != target:
            target_reasons.setdefault(target, "not_mutual_best")
            continue
        if proxy in paired_proxies:
            target_reasons.setdefault(target, "proxy_already_assigned")
            continue

        pairs.append({
            "target": target_by_node[target],
            "proxy": proxy_record,
            "score": metric["score"],
            "center_norm": metric["center_norm"],
            "size_mismatch": metric["size_mismatch"],
        })
        paired_targets.add(target)
        paired_proxies.add(proxy)

    def pair_sort_key(item):
        center, _ = bbox_center_size(item["target"]["bounds"])
        return (
            round(center[0], 8),
            round(center[2], 8),
            round(center[1], 8),
            item["target"]["node"],
            item["proxy"]["node"],
        )

    pairs.sort(key=pair_sort_key)
    unresolved = [
        (target, target_reasons.get(target, "not_mutual_best"))
        for target in sorted(target_by_node)
        if target not in paired_targets
    ]
    return {"pairs": pairs, "unresolved": unresolved}


def _long_name(node):
    _require_cmds()
    matches = cmds.ls(node, long=True) or []
    if len(matches) != 1:
        raise PivotMatchError("Could not resolve a unique DAG object: {}".format(node))
    return matches[0]


def _mesh_shapes(node):
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
    result = []
    for shape in shapes:
        if cmds.nodeType(shape) != "mesh":
            continue
        try:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
        except Exception:
            pass
        result.append(shape)
    return result


def _validate_mesh_transform(node, writable=False):
    long_node = _long_name(node)
    if cmds.nodeType(long_node) != "transform":
        raise PivotMatchError("'{}' is not a transform.".format(leaf_name(long_node)))
    if not _mesh_shapes(long_node):
        raise PivotMatchError("'{}' has no renderable mesh shape.".format(leaf_name(long_node)))

    if writable:
        try:
            if cmds.referenceQuery(long_node, isNodeReferenced=True):
                raise PivotMatchError(
                    "Target '{}' is referenced and will not be modified.".format(leaf_name(long_node))
                )
        except PivotMatchError:
            raise
        except Exception:
            pass
        try:
            locked = cmds.lockNode(long_node, query=True, lock=True) or [False]
            if any(bool(value) for value in locked):
                raise PivotMatchError(
                    "Target '{}' is locked and will not be modified.".format(leaf_name(long_node))
                )
        except PivotMatchError:
            raise
        except Exception:
            pass

    return long_node


def _proxy_root():
    _require_cmds()
    matches = cmds.ls(PROXY_ROOT, long=True) or []
    if len(matches) != 1 or matches[0] != PROXY_ROOT:
        raise PivotMatchError(
            "Root proxy group '{}' was not found. Create it and place proxy meshes under it.".format(
                PROXY_ROOT
            )
        )
    if cmds.nodeType(PROXY_ROOT) != "transform":
        raise PivotMatchError("'{}' must be a transform group.".format(PROXY_ROOT))
    return PROXY_ROOT


def _proxy_mesh_transforms():
    root = _proxy_root()
    descendants = cmds.listRelatives(
        root, allDescendents=True, fullPath=True, type="transform"
    ) or []
    proxies = []
    for node in sorted(set(descendants)):
        try:
            proxies.append(_validate_mesh_transform(node, writable=False))
        except PivotMatchError:
            # Nested helper groups are allowed; only mesh transforms become sources.
            continue
    if not proxies:
        raise PivotMatchError("'{}' contains no proxy mesh transforms.".format(PROXY_ROOT))
    return proxies


def _selected_targets():
    raw = cmds.ls(selection=True, long=True, flatten=True) or []
    if not raw:
        raise PivotMatchError("Select one or more final mesh transforms.")
    targets = []
    for node in raw:
        long_node = _validate_mesh_transform(node, writable=True)
        if long_node == PROXY_ROOT or long_node.startswith(PROXY_ROOT + "|"):
            raise PivotMatchError(
                "Proxy object '{}' cannot be selected as a final Target.".format(leaf_name(long_node))
            )
        targets.append(long_node)
    if len(set(targets)) != len(targets):
        raise PivotMatchError("Select distinct final mesh transforms.")
    return targets



def _vector_attr(node, attr):
    """Return a numeric double3 transform attribute as a 3-tuple."""
    try:
        value = cmds.getAttr(node + "." + attr)
    except Exception as exc:
        raise PivotMatchError(
            "Could not read {} from '{}': {}".format(attr, leaf_name(node), exc)
        )
    if isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise PivotMatchError(
            "Unexpected {} value on '{}': {}".format(attr, leaf_name(node), value)
        )
    return tuple(float(component) for component in value)


def _transform_values(node):
    return {
        "translate": _vector_attr(node, "translate"),
        "rotate": _vector_attr(node, "rotate"),
        "scale": _vector_attr(node, "scale"),
    }


def _validate_transform_channels_writable(node):
    for attr in (
        "translateX", "translateY", "translateZ",
        "rotateX", "rotateY", "rotateZ",
        "scaleX", "scaleY", "scaleZ",
    ):
        try:
            settable = cmds.getAttr(node + "." + attr, settable=True)
        except Exception as exc:
            raise PivotMatchError(
                "Could not inspect transform channel '{}.{}': {}".format(
                    leaf_name(node), attr, exc
                )
            )
        if not settable:
            raise PivotMatchError(
                "Target '{}.{}' is locked or connected; coordinate values cannot be synchronized safely.".format(
                    leaf_name(node), attr
                )
            )


def _values_close(first, second, tolerance=1e-6):
    return all(abs(float(a) - float(b)) <= tolerance for a, b in zip(first, second))


def _identity_matrix():
    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def _matrix16(value, label="matrix"):
    if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], (list, tuple)):
        value = value[0]
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        raise PivotMatchError("Unexpected {} value: {}".format(label, value))
    return tuple(float(component) for component in value)


def _matrix_multiply(first, second):
    a = _matrix16(first, "first matrix")
    b = _matrix16(second, "second matrix")
    result = [0.0] * 16
    for row in range(4):
        for col in range(4):
            result[row * 4 + col] = sum(
                a[row * 4 + k] * b[k * 4 + col]
                for k in range(4)
            )
    return tuple(result)


def _matrix_inverse(matrix, tolerance=1e-12):
    source = _matrix16(matrix)
    aug = []
    for row in range(4):
        aug.append(
            list(source[row * 4:(row + 1) * 4])
            + [1.0 if row == col else 0.0 for col in range(4)]
        )

    for col in range(4):
        pivot_row = max(range(col, 4), key=lambda row: abs(aug[row][col]))
        pivot = aug[pivot_row][col]
        if abs(pivot) <= tolerance:
            raise PivotMatchError(
                "Cannot rebalance transform because the resulting local matrix is singular. "
                "Check for zero scale values."
            )
        if pivot_row != col:
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]

        pivot = aug[col][col]
        aug[col] = [value / pivot for value in aug[col]]
        for row in range(4):
            if row == col:
                continue
            factor = aug[row][col]
            if abs(factor) <= tolerance:
                continue
            aug[row] = [
                aug[row][index] - factor * aug[col][index]
                for index in range(8)
            ]

    return tuple(aug[row][col] for row in range(4) for col in range(4, 8))


def _matrices_close(first, second, tolerance=1e-6):
    return all(
        abs(float(a) - float(b)) <= tolerance
        for a, b in zip(_matrix16(first), _matrix16(second))
    )


def _matrix_attr(node, attr):
    try:
        return _matrix16(cmds.getAttr(node + "." + attr), "{}.{}".format(leaf_name(node), attr))
    except PivotMatchError:
        raise
    except Exception as exc:
        raise PivotMatchError(
            "Could not read {} from '{}': {}".format(attr, leaf_name(node), exc)
        )


def _dag_parent_world_matrix(node):
    parents = cmds.listRelatives(node, parent=True, fullPath=True, type="transform") or []
    if not parents:
        return _identity_matrix()
    if len(parents) != 1:
        raise PivotMatchError("Unexpected multiple DAG parents for '{}'.".format(leaf_name(node)))
    return _matrix_attr(parents[0], "worldMatrix[0]")


def _validate_offset_parent_matrix_writable(node):
    attr = node + ".offsetParentMatrix"
    if not cmds.objExists(attr):
        raise PivotMatchError(
            "Target '{}' has no offsetParentMatrix. This V1.2 method requires a Maya version that supports it.".format(
                leaf_name(node)
            )
        )
    try:
        if not cmds.getAttr(attr, settable=True):
            raise PivotMatchError(
                "Target '{}' offsetParentMatrix is locked or connected; coordinate values cannot be synchronized safely.".format(
                    leaf_name(node)
                )
            )
    except PivotMatchError:
        raise
    except Exception as exc:
        raise PivotMatchError(
            "Could not inspect offsetParentMatrix on '{}': {}".format(leaf_name(node), exc)
        )


def _set_vector_attr(node, attr, values):
    values = tuple(float(value) for value in values)
    try:
        cmds.setAttr(node + "." + attr, values[0], values[1], values[2], type="double3")
    except Exception as exc:
        raise PivotMatchError(
            "Could not set {} on '{}': {}".format(attr, leaf_name(node), exc)
        )


def _set_transform_values_exact(target, desired):
    _validate_transform_channels_writable(target)
    _set_vector_attr(target, "translate", desired["translate"])
    _set_vector_attr(target, "rotate", desired["rotate"])
    _set_vector_attr(target, "scale", desired["scale"])

    actual = _transform_values(target)
    for attr in ("translate", "rotate", "scale"):
        if not _values_close(actual[attr], desired[attr]):
            raise PivotMatchError(
                "Maya did not set {} on '{}' to the Proxy values. Use Undo immediately.".format(
                    attr, leaf_name(target)
                )
            )


def _rebalance_transform_values_with_offset_parent_matrix(target, proxy):
    """Set Proxy T/R/S exactly while preserving the Target world matrix.

    Maya post-multiplies matrices. With a DAG parent P, local matrix L and
    offsetParentMatrix O, the Target world matrix is L * O * P. After pivots and
    desired T/R/S are written, solve O = inverse(L) * W_before * inverse(P).
    """
    _validate_transform_channels_writable(target)
    _validate_offset_parent_matrix_writable(target)

    world_before = _matrix_attr(target, "worldMatrix[0]")
    desired = _transform_values(proxy)

    cmds.matchTransform(target, proxy, pivots=True)

    try:
        rotate_order = int(cmds.getAttr(proxy + ".rotateOrder"))
        if not cmds.getAttr(target + ".rotateOrder", settable=True):
            raise PivotMatchError(
                "Target '{}' rotateOrder is locked or connected.".format(leaf_name(target))
            )
        cmds.setAttr(target + ".rotateOrder", rotate_order)
    except PivotMatchError:
        raise
    except Exception as exc:
        raise PivotMatchError(
            "Could not synchronize rotateOrder for '{}': {}".format(leaf_name(target), exc)
        )

    _set_transform_values_exact(target, desired)

    local_after = _matrix_attr(target, "matrix")
    parent_world = _dag_parent_world_matrix(target)
    compensation = _matrix_multiply(
        _matrix_multiply(_matrix_inverse(local_after), world_before),
        _matrix_inverse(parent_world),
    )

    try:
        cmds.setAttr(target + ".offsetParentMatrix", compensation, type="matrix")
    except Exception as exc:
        raise PivotMatchError(
            "Could not write offsetParentMatrix for '{}': {}".format(leaf_name(target), exc)
        )

    actual = _transform_values(target)
    for attr in ("translate", "rotate", "scale"):
        if not _values_close(actual[attr], desired[attr]):
            raise PivotMatchError(
                "{} values on '{}' did not remain equal to Proxy values after rebalance.".format(
                    attr, leaf_name(target)
                )
            )

    world_after = _matrix_attr(target, "worldMatrix[0]")
    if not _matrices_close(world_after, world_before):
        raise PivotMatchError(
            "World transform changed while synchronizing '{}'. Use Undo immediately.".format(
                leaf_name(target)
            )
        )

    return desired


def _world_bbox(node):
    try:
        bounds = cmds.exactWorldBoundingBox(node)
    except Exception as exc:
        raise PivotMatchError(
            "Could not read world bounding box for '{}': {}".format(leaf_name(node), exc)
        )
    bbox_center_size(bounds)
    return tuple(float(value) for value in bounds)


def _record(node):
    return {
        "node": node,
        "bounds": _world_bbox(node),
        "transform": _transform_values(node),
    }


def _round_bounds(bounds):
    return tuple(round(float(value), 6) for value in bounds)


def _analysis_signature(target_records, proxy_records, pairs):
    targets = tuple(sorted(
        (
            record["node"],
            _round_bounds(record["bounds"]),
            tuple(round(value, 6) for value in record["transform"]["translate"]),
            tuple(round(value, 6) for value in record["transform"]["rotate"]),
            tuple(round(value, 6) for value in record["transform"]["scale"]),
        )
        for record in target_records
    ))
    proxies = tuple(sorted(
        (
            record["node"],
            _round_bounds(record["bounds"]),
            tuple(round(value, 6) for value in record["transform"]["translate"]),
            tuple(round(value, 6) for value in record["transform"]["rotate"]),
            tuple(round(value, 6) for value in record["transform"]["scale"]),
        )
        for record in proxy_records
    ))
    mapping = tuple(
        (pair["target"]["node"], pair["proxy"]["node"])
        for pair in pairs
    )
    return (PROXY_ROOT, targets, proxies, mapping)


def analyze_matches():
    """Read-only analysis. No pivots or transforms are modified."""
    _require_cmds()
    targets = [_record(node) for node in _selected_targets()]
    proxies = [_record(node) for node in _proxy_mesh_transforms()]
    pairing = pair_targets_to_proxies(targets, proxies)
    unresolved = pairing["unresolved"]
    ready = bool(pairing["pairs"]) and not unresolved and len(pairing["pairs"]) == len(targets)
    signature = _analysis_signature(targets, proxies, pairing["pairs"]) if ready else None
    return {
        "ready": ready,
        "pairs": pairing["pairs"],
        "unresolved": unresolved,
        "signature": signature,
        "target_count": len(targets),
        "proxy_count": len(proxies),
    }


def analysis_lines(analysis):
    lines = [
        "MATCH | {}  <=  {}".format(
            leaf_name(pair["target"]["node"]),
            leaf_name(pair["proxy"]["node"]),
        )
        for pair in analysis["pairs"]
    ]
    lines.extend(
        "UNRESOLVED | {} | {}".format(leaf_name(node), reason)
        for node, reason in analysis["unresolved"]
    )
    return lines or ["No matches found."]


def apply_matches(expected_signature):
    """Apply exact Proxy coordinate values + Match Pivots for a previously analyzed selection."""
    if expected_signature is None:
        raise PivotMatchError("Analyze the selection before applying.")

    analysis = analyze_matches()
    if not analysis["ready"]:
        raise PivotMatchError("Match analysis is no longer ready. Analyze again.")
    if analysis["signature"] != expected_signature:
        raise PivotMatchError(
            "Selection, proxy contents, or world-space bounds changed. Analyze again."
        )

    chunk_open = False
    applied = 0
    try:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
        chunk_open = True
        for pair in analysis["pairs"]:
            target = pair["target"]["node"]
            proxy = pair["proxy"]["node"]

            # V1.2: directly write Proxy Channel Box T/R/S values and solve an
            # offsetParentMatrix compensation so the Target world matrix stays exact.
            _rebalance_transform_values_with_offset_parent_matrix(target, proxy)
            applied += 1
        return {"matched_count": applied, "pairs": analysis["pairs"]}
    except Exception as exc:
        raise PivotMatchError(
            "Pivot matching failed after {} successful item(s). "
            "Use Undo immediately to restore this batch. Details: {}".format(applied, exc)
        )
    finally:
        if chunk_open:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass


def _set_status(control, message, good=True):
    cmds.text(
        control,
        edit=True,
        label=message,
        backgroundColor=((0.30, 0.72, 0.42) if good else (0.90, 0.34, 0.36)),
    )


def show():
    _require_cmds()
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title=WINDOW_TITLE,
        sizeable=True,
        widthHeight=(560, 420),
    )
    root = cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    cmds.text(label="MCL Proxy Pivot Matcher", font="boldLabelFont", align="left")
    cmds.text(
        label="Proxy Source: {}  |  Select final models only".format(PROXY_ROOT),
        align="left",
    )
    status = cmds.text(
        label="Ready",
        height=36,
        backgroundColor=(0.22, 0.22, 0.22),
        wordWrap=True,
    )
    preview = cmds.textScrollList(numberOfRows=12, height=240)
    state = {"signature": None}

    def invalidate():
        state["signature"] = None
        cmds.textScrollList(preview, edit=True, removeAll=True)
        cmds.textScrollList(
            preview,
            edit=True,
            append="Select final models, then click Analyze.",
        )

    def analyze(*_):
        try:
            result = analyze_matches()
            cmds.textScrollList(preview, edit=True, removeAll=True)
            for line in analysis_lines(result):
                cmds.textScrollList(preview, edit=True, append=line)
            state["signature"] = result["signature"] if result["ready"] else None
            if result["ready"]:
                _set_status(
                    status,
                    "Ready: {} final model(s) matched to proxy sources.".format(
                        result["target_count"]
                    ),
                    True,
                )
            else:
                _set_status(
                    status,
                    "Unresolved/ambiguous target(s) found. Nothing changed.",
                    False,
                )
        except PivotMatchError as exc:
            invalidate()
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    def apply(*_):
        try:
            result = apply_matches(state["signature"])
            invalidate()
            _set_status(
                status,
                "Matched pivots + exact T/R/S values for {} final model(s).".format(result["matched_count"]),
                True,
            )
        except PivotMatchError as exc:
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.button(label="Analyze", height=38, command=analyze)
    cmds.button(label="Apply Pivots + Coordinates V1.2", height=38, command=apply)
    cmds.setParent(root)
    cmds.text(
        label="If Apply reports a partial failure, use one Undo immediately.",
        align="left",
    )
    invalidate()
    cmds.showWindow(window)
    return window
