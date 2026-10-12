# Maya Command Library

Lightweight Maya commands and tools managed through Jira project **MCL**.

## Project links

- Jira: https://coldrain1994.atlassian.net
- Project key: `MCL`
- Workflow: `MCL-WORKFLOW-V1`

## Structure

Each maintained tool lives in its own directory under `tools/` and keeps its own source, README, changelog, launcher, and focused tests where practical.

Quick one-off scripts live under `scripts/`.

## Delivery rule

A feature is not considered accepted because code exists or tests pass. Fixed-version source/download, complete Maya launch code, usage instructions, verification scope, and explicit user acceptance are recorded in the corresponding MCL Jira item.

---

## Scripts

### 1. 给选中物体添加 old_ 前缀

**介绍：** 给当前选中的所有物体名称前面加上 `old_` 前缀。支持多选和层级，已有该前缀的会自动跳过。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def add_old_prefix():
    selected = cmds.ls(selection=True, long=True)
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    for obj in reversed(selected):
        short_name = obj.split('|')[-1]
        if short_name.startswith("old_"):
            print(f"跳过已有前缀的物体: {short_name}")
            continue
        new_name = "old_" + short_name
        try:
            cmds.rename(obj, new_name)
            print(f"重命名: {short_name} → {new_name}")
        except Exception as e:
            cmds.warning(f"重命名失败 {short_name}: {e}")

add_old_prefix()
```

</details>

**文件：** [`scripts/add_old_prefix.py`](scripts/add_old_prefix.py)

---

### 2. 移除 pasted__ 前缀

**介绍：** 移除选中物体名称中因粘贴而产生的 `pasted__` 前缀。只处理带有该前缀的物体，其他跳过。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def remove_pasted_prefix():
    selected = cmds.ls(selection=True, long=True)
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    prefix = "pasted__"
    for obj in reversed(selected):
        short_name = obj.split('|')[-1]
        if short_name.startswith(prefix):
            new_name = short_name[len(prefix):]
            if not new_name:
                cmds.warning(f"移除前缀后名称为空，跳过: {short_name}")
                continue
            try:
                cmds.rename(obj, new_name)
                print(f"移除前缀: {short_name} → {new_name}")
            except Exception as e:
                cmds.warning(f"重命名失败 {short_name}: {e}")
        else:
            print(f"无 pasted__ 前缀，跳过: {short_name}")

remove_pasted_prefix()
```

</details>

**文件：** [`scripts/remove_pasted_prefix.py`](scripts/remove_pasted_prefix.py)

---

### 3. 复制并沿当前轴旋转 180 度

**介绍：** 复制当前选中的物体，并让复制体沿当前旋转工具的激活轴（X/Y/Z）旋转 180 度。若当前不是旋转工具，则默认沿 Y 轴。复制后自动选中新物体。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def duplicate_and_rotate_180():
    selected = cmds.ls(selection=True)
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    axis = "Y"
    try:
        current_tool = cmds.currentCtx()
        if current_tool == "Rotate":
            mode = cmds.manipRotateContext("Rotate", query=True, mode=True)
            axis_map = {0: "X", 1: "Y", 2: "Z"}
            axis = axis_map.get(mode, "Y")
    except Exception:
        axis = "Y"
    print(f"使用轴: {axis}")
    duplicates = cmds.duplicate(selected, returnRootsOnly=True)
    rotate_value = [0, 0, 0]
    if axis == "X":
        rotate_value[0] = 180
    elif axis == "Y":
        rotate_value[1] = 180
    elif axis == "Z":
        rotate_value[2] = 180
    for dup in duplicates:
        cmds.rotate(rotate_value[0], rotate_value[1], rotate_value[2],
                     dup, relative=True, objectSpace=True)
    cmds.select(duplicates)
    print(f"已复制并沿 {axis} 轴旋转 180 度")

duplicate_and_rotate_180()
```

</details>

**文件：** [`scripts/duplicate_rotate_180.py`](scripts/duplicate_rotate_180.py)

---

### 4. 选中模型坐标轴同步成活动模型（简易版）

**介绍：** 把其他选中物体的坐标轴（朝向）同步成当前活动物体（最后选中的那个）。使用临时 Orient Constraint 强制匹配朝向。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def sync_axes_to_active():
    selected = cmds.ls(selection=True, type="transform")
    if len(selected) < 2:
        cmds.warning("请至少选中两个物体（最后选中的作为目标）！")
        return
    active = selected[-1]
    sources = selected[:-1]
    success_count = 0
    for src in sources:
        try:
            constraint = cmds.orientConstraint(active, src, maintainOffset=False)[0]
            cmds.delete(constraint)
            success_count += 1
        except Exception as e:
            cmds.warning(f"同步失败 {src}: {e}")
    cmds.select(selected)
    print(f"已将 {success_count} 个物体的坐标轴同步到: {active}")
    cmds.inViewMessage(
        amg=f'<hl>已同步 {success_count} 个物体的坐标轴</hl>',
        pos='midCenter',
        fade=True
    )

sync_axes_to_active()
```

</details>

**文件：** [`scripts/sync_axes_to_active.py`](scripts/sync_axes_to_active.py)

---

### 5. 匹配全部变换并保持模型不动（完整版）

**介绍：** 把选中模型的 TRS 数值、轴朝向、枢轴位置全部同步成参考物体（最后选中的），同时通过反补偿顶点保持模型在世界空间的位置完全不动。支持冻结变换后的物体。需要同一父级、多边形、无蒙皮/变形器等条件。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds
import maya.api.OpenMaya as om

def match_all_transforms_keep_mesh():
    sel = cmds.ls(sl=True, long=True) or []
    if len(sel) < 2 or any(cmds.nodeType(x) != "transform" for x in sel):
        raise RuntimeError("物体模式：先选需要修改的模型，最后 Shift 选参考物体。")
    if not cmds.undoInfo(q=True, state=True):
        raise RuntimeError("请先开启 Maya Undo。")
    ref, targets = sel[-1], sel[:-1]
    parent = cmds.listRelatives(ref, parent=True, fullPath=True) or []
    identity = (1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1)
    data = []
    def fail(message):
        raise RuntimeError(message)
    def is_instanced(node):
        selection = om.MSelectionList()
        selection.add(node)
        path = selection.getDagPath(0)
        return path.isInstanced()
    for obj in sel:
        if (cmds.listRelatives(obj, parent=True, fullPath=True) or []) != parent:
            fail("目标和参考必须在同一个父级下：" + obj)
        if is_instanced(obj):
            fail("暂不支持实例：" + obj)
        if not cmds.getAttr(obj + ".inheritsTransform"):
            fail("暂不支持关闭 Inherits Transform：" + obj)
        if cmds.attributeQuery("offsetParentMatrix", node=obj, exists=True):
            matrix = cmds.getAttr(obj + ".offsetParentMatrix")
            if any(abs(a-b) > 1e-10 for a, b in zip(matrix, identity)):
                fail("暂不支持非默认 Offset Parent Matrix：" + obj)
        if any(abs(v) > 1e-10 for v in cmds.getAttr(obj + ".shear")[0]):
            fail("暂不支持 Shear：" + obj)
        if any(v <= 1e-10 for v in cmds.getAttr(obj + ".scale")[0]):
            fail("暂不支持负缩放或零缩放：" + obj)
    for obj in targets:
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            fail("不修改引用物体：" + obj)
        if cmds.listRelatives(obj, children=True, type="transform"):
            fail("请直接选择不带子物体的模型：" + obj)
        shapes = cmds.listRelatives(
            obj, shapes=True, noIntermediate=True, fullPath=True) or []
        if not shapes or any(cmds.nodeType(s) != "mesh" for s in shapes):
            fail("目标必须是多边形模型：" + obj)
        for attr in (
            "translate", "rotate", "scale", "rotateAxis", "rotateOrder",
            "rotatePivot", "scalePivot",
            "rotatePivotTranslate", "scalePivotTranslate",
            "offsetParentMatrix", "inheritsTransform"
        ):
            plug = obj + "." + attr
            if cmds.objExists(plug) and (
                cmds.getAttr(plug, lock=True) or
                cmds.listConnections(plug, source=True, destination=False)
            ):
                fail("属性被锁定或驱动：" + plug)
        meshes = []
        for shape in shapes:
            if is_instanced(shape):
                fail("暂不支持实例 Shape：" + shape)
            for node in cmds.listHistory(shape) or []:
                types = cmds.nodeType(node, inherited=True) or []
                if ("geometryFilter" in types or
                    cmds.nodeType(node).startswith("animCurve") or
                    cmds.nodeType(node) == "expression"):
                    fail("暂不支持蒙皮、变形器或动画历史：" + obj)
            verts = shape + ".vtx[*]"
            if any(cmds.polyNormalPerVertex(
                    verts, q=True, freezeNormal=True) or []):
                fail("模型有锁定法线，本版本不处理：" + obj)
            points = cmds.xform(
                verts, q=True, worldSpace=True, translation=True) or []
            if not points:
                fail("模型没有顶点：" + obj)
            meshes.append((shape, points))
        data.append((obj, meshes))
    order = cmds.getAttr(ref + ".rotateOrder")
    copy_attrs = (
        "translate", "rotate", "scale", "shear", "rotateAxis",
        "rotatePivot", "scalePivot",
        "rotatePivotTranslate", "scalePivotTranslate"
    )
    reference_values = {
        attr: cmds.getAttr(ref + "." + attr)[0] for attr in copy_attrs
    }
    reference_matrix = cmds.xform(ref, q=True, worldSpace=True, matrix=True)
    changed = False
    cmds.undoInfo(openChunk=True, chunkName="MatchAllTransformsKeepMesh")
    try:
        for obj, meshes in data:
            cmds.setAttr(obj + ".rotateOrder", order)
            changed = True
            for attr in copy_attrs:
                cmds.setAttr(obj + "." + attr, *reference_values[attr])
            for shape, points in meshes:
                for i in range(len(points) // 3):
                    cmds.xform(
                        "{}.vtx[{}]".format(shape, i),
                        worldSpace=True, translation=points[3*i:3*i+3])
                check = cmds.xform(
                    shape + ".vtx[*]", q=True,
                    worldSpace=True, translation=True)
                if len(check) != len(points) or any(
                    abs(a-b) > 1e-5 for a, b in zip(points, check)
                ):
                    fail("顶点位置校验失败。")
            for attr, expected in reference_values.items():
                actual = cmds.getAttr(obj + "." + attr)[0]
                if any(abs(a-b) > 1e-8 for a, b in zip(actual, expected)):
                    fail("通道数值校验失败：" + obj + "." + attr)
            actual_matrix = cmds.xform(obj, q=True, worldSpace=True, matrix=True)
            if any(abs(a-b) > 1e-8
                   for a, b in zip(actual_matrix, reference_matrix)):
                fail("坐标系校验失败：" + obj)
    except Exception:
        cmds.undoInfo(closeChunk=True)
        if changed:
            cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)
        print("完成：参考不变；目标模型不动；TRS 数值、轴及枢轴全部同步。")

match_all_transforms_keep_mesh()
```

</details>

**文件：** [`scripts/match_all_transforms_keep_mesh.py`](scripts/match_all_transforms_keep_mesh.py)
