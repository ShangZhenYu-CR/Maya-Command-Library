# -*- coding: utf-8 -*-
"""MCL Proxy Pivot Matcher.

MCL-2 V1.

Workflow:
1. Put proxy meshes under the root group ``|proxy``.
2. Select one or more final mesh transforms.
3. Analyze conservative world-space Target -> Proxy matches.
4. Apply Maya Match Pivots in one undo chunk.

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
    return {"node": node, "bounds": _world_bbox(node)}


def _round_bounds(bounds):
    return tuple(round(float(value), 6) for value in bounds)


def _analysis_signature(target_records, proxy_records, pairs):
    targets = tuple(sorted(
        (record["node"], _round_bounds(record["bounds"]))
        for record in target_records
    ))
    proxies = tuple(sorted(
        (record["node"], _round_bounds(record["bounds"]))
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
    """Apply Match Pivots for a previously analyzed selection."""
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
            # Autodesk Maya Match Pivots equivalent:
            # only the pivot operation is requested; position/rotation/scale matching
            # is intentionally not enabled.
            cmds.matchTransform(target, proxy, pivots=True)
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
                "Matched pivots for {} final model(s).".format(result["matched_count"]),
                True,
            )
        except PivotMatchError as exc:
            _set_status(status, str(exc), False)
            cmds.warning("{}: {}".format(WINDOW_TITLE, exc))

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.button(label="Analyze", height=38, command=analyze)
    cmds.button(label="Apply Match Pivots", height=38, command=apply)
    cmds.setParent(root)
    cmds.text(
        label="If Apply reports a partial failure, use one Undo immediately.",
        align="left",
    )
    invalidate()
    cmds.showWindow(window)
    return window
