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

### 5. 快速匹配枢轴位置与移动工具朝向

**介绍：** 轻量 pivot 版：将目标的旋转/缩放枢轴位置匹配到参考物体的世界空间旋转枢轴，使用 Maya 原生枢轴补偿保持对象变换，并将 Move 移动工具朝向设为参考物体朝向。代码不读取或逐个修改模型顶点。

**功能范围：** 不匹配 Channel Box 数值，不永久改变对象本地轴，也不做轴向烘焙；Move 工具朝向属于工具设置。参考物体不修改。

**用法：** 在物体选择模式下先选一个或多个目标，最后选参考物体，在 Maya Script Editor 的 Python 标签页运行下方完整代码。目标不能是引用物体或锁定节点，枢轴相关属性须可写，并须开启 Undo。

**撤销范围：** Undo 块只覆盖枢轴改动。最后的目标选择、切换 Move 工具和工具朝向设置在该撤销块之外，不保证与枢轴改动一次撤销。

**验证范围：** 已通过 Python AST 语法检查；我们尚未进行 Maya 实机测试，不承诺所有场景瞬间完成。请先用两个新建立方体测试。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
# 兼容旧文件路径：此文件现在为轻量 pivot 版（快速匹配枢轴位置与移动工具朝向）。
# 不同步 Channel Box，不永久改变对象本地轴，不遍历或修改模型顶点。
import maya.cmds as cmds


def match_pivot_fast():
    sel = cmds.ls(sl=True, long=True) or []
    if len(sel) < 2 or any(cmds.nodeType(n) != 'transform' for n in sel):
        raise RuntimeError('先选目标，最后选参考；使用物体选择模式。')
    if not cmds.undoInfo(q=True, state=True):
        raise RuntimeError('请先开启 Undo。')

    targets, ref = sel[:-1], sel[-1]
    pos = cmds.xform(ref, q=True, ws=True, rp=True)
    attrs = ('rotatePivot', 'scalePivot',
             'rotatePivotTranslate', 'scalePivotTranslate')

    # 只检查变换属性，不扫描模型顶点。
    for obj in targets:
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            raise RuntimeError('不修改引用物体：' + obj)
        if (cmds.lockNode(obj, q=True, lock=True) or [False])[0]:
            raise RuntimeError('节点已锁定：' + obj)
        for attr in attrs:
            names = [attr] + (cmds.attributeQuery(
                attr, node=obj, listChildren=True) or [])
            for name in names:
                plug = obj + '.' + name
                if not cmds.getAttr(plug, settable=True):
                    raise RuntimeError('属性被锁定或驱动：' + plug)

    before = {n: cmds.xform(n, q=True, ws=True, matrix=True)
              for n in targets}
    changed = False
    cmds.undoInfo(openChunk=True, chunkName='MatchPivotFast')
    try:
        for obj in targets:
            cmds.xform(obj, ws=True, pivots=pos, preserve=True)
            changed = True
            after = cmds.xform(obj, q=True, ws=True, matrix=True)
            if any(abs(a-b) > 1e-7 * max(1.0, abs(a), abs(b))
                   for a, b in zip(before[obj], after)):
                raise RuntimeError('变换保持校验失败：' + obj)
    except Exception:
        cmds.undoInfo(closeChunk=True)
        if changed:
            cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)

    cmds.select(targets, r=True)
    cmds.setToolTo('Move')
    cmds.manipMoveContext('Move', e=True, mode=6, orientObject=ref)
    print('完成：枢轴位置已匹配；移动工具使用参考朝向。')


match_pivot_fast()
```

</details>

**文件：** [`scripts/match_all_transforms_keep_mesh.py`](scripts/match_all_transforms_keep_mesh.py)。为兼容旧链接保留文件路径，现已替换为轻量 pivot 版；旧逐顶点实现已从现行入口移除，Git 历史保留。

---

### 6. 对齐模型：同步 Channel Box 并移动、旋转、缩放

**介绍：** 将目标物体的位移、旋转、缩放、Shear、Rotate Axis、旋转顺序和枢轴属性同步成最后选中的参考物体。模型会随变换实际移动、旋转、缩放，不进行顶点反补偿；参考物体不修改。

**用法：** 在物体模式下先选一个或多个目标，最后按住 Shift 选参考物体，将下方完整代码粘贴到 Maya Script Editor 的 Python 标签页运行。操作合并为一次 Undo。

**条件：** 目标与参考须处于同一父级，Inherits Transform 状态和 Offset Parent Matrix 相同；目标不能是引用物体，待修改属性不能锁定或受驱动，且须开启 Maya Undo。

**验证范围：** 已通过 Python 语法检查，尚未在 Maya 中完成运行验证。建议先在场景副本上试用。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def align_model_to_last():
    # 先选需要对齐的模型，最后 Shift 选参考物体。
    selected = cmds.ls(sl=True, long=True) or []
    if len(selected) < 2 or any(
        cmds.nodeType(x) != "transform" for x in selected
    ):
        raise RuntimeError("请在物体模式下先选目标，最后选参考物体。")
    if not cmds.undoInfo(q=True, state=True):
        raise RuntimeError("请先开启 Maya Undo。")

    reference = selected[-1]
    targets = selected[:-1]
    attrs = (
        "translate", "rotate", "scale", "shear", "rotateAxis",
        "rotatePivot", "scalePivot",
        "rotatePivotTranslate", "scalePivotTranslate"
    )
    values = {
        a: cmds.getAttr(reference + "." + a)[0] for a in attrs
    }
    order = cmds.getAttr(reference + ".rotateOrder")
    parent = cmds.listRelatives(reference, parent=True, fullPath=True) or []

    for obj in targets:
        if (cmds.listRelatives(obj, parent=True, fullPath=True) or []) != parent:
            raise RuntimeError("请让目标与参考处于同一父级：" + obj)
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            raise RuntimeError("不修改引用物体：" + obj)
        if cmds.getAttr(obj + ".inheritsTransform") != cmds.getAttr(
            reference + ".inheritsTransform"
        ):
            raise RuntimeError("Inherits Transform 状态不同：" + obj)
        if cmds.attributeQuery("offsetParentMatrix", node=obj, exists=True):
            if cmds.getAttr(obj + ".offsetParentMatrix") != cmds.getAttr(
                reference + ".offsetParentMatrix"
            ):
                raise RuntimeError("Offset Parent Matrix 不同：" + obj)
        for attr in attrs + ("rotateOrder",):
            children = cmds.attributeQuery(
                attr, node=obj, listChildren=True) or [attr]
            for child in children:
                if not cmds.getAttr(obj + "." + child, settable=True):
                    raise RuntimeError("属性被锁定或驱动：" + obj + "." + child)

    changed = False
    cmds.undoInfo(openChunk=True, chunkName="AlignModelToLast")
    try:
        for obj in targets:
            cmds.setAttr(obj + ".rotateOrder", order)
            changed = True
            for attr in attrs:
                cmds.setAttr(obj + "." + attr, *values[attr])
        print("完成：目标的位移、旋转、缩放及坐标系已匹配参考。")
    except Exception:
        cmds.undoInfo(closeChunk=True)
        if changed:
            cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)

align_model_to_last()
```

</details>

**文件：** [`scripts/align_model_to_last.py`](scripts/align_model_to_last.py)

---

### 7. 解锁法线并软化边

**介绍：** 对选中的 mesh 解锁法线（unFreezeNormal）并软化所有边（angle=180），然后删除建模历史。适用于修复硬边或锁定法线的模型。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def unlock_normals_soften_edges():
    sel = cmds.ls(selection=True, long=True)
    if not sel:
        cmds.warning("没有选中任何物体！")
        return
    processed = []
    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True)
        if shapes:
            try:
                cmds.polyNormalPerVertex(shapes[0], unFreezeNormal=True)
                cmds.polySoftEdge(obj, angle=180)
                processed.append(obj)
            except Exception as e:
                cmds.warning(f"处理失败 {obj}: {e}")
    if processed:
        cmds.delete(processed, constructionHistory=True)
        print(f"Normals unlocked + edges softened: {processed}")
        cmds.inViewMessage(
            amg=f'<hl>已解锁法线并软化边: {len(processed)} 个物体</hl>',
            pos='midCenter',
            fade=True
        )
    else:
        cmds.warning("没有找到可处理的 mesh。")

unlock_normals_soften_edges()
```

</details>

**文件：** [`scripts/unlock_normals_soften_edges.py`](scripts/unlock_normals_soften_edges.py)

---

### 8. 重命名 UV 通道

**介绍：** 重命名选中模型的 UV 通道。默认预设映射：map1 → map2、uv0 → uv1。可传入自定义字典手动指定任意旧名称到新名称的映射。运行时处理所有选中的 mesh。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def rename_uv_channels(rename_map=None):
    if rename_map is None:
        rename_map = {"map1": "map2", "uv0": "uv1"}
    sel = cmds.ls(selection=True, long=True)
    if not sel:
        cmds.warning("没有选中任何物体！")
        return
    success_count = 0
    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, noIntermediate=True)
        if not shapes or cmds.nodeType(shapes[0]) != "mesh":
            continue
        shape = shapes[0]
        try:
            uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
        except Exception:
            continue
        for old_name in list(uv_sets):
            if old_name in rename_map:
                new_name = rename_map[old_name]
                if new_name in uv_sets:
                    print(f"跳过 {obj}: {new_name} 已存在")
                    continue
                try:
                    cmds.polyUVSet(shape, rename=True, uvSet=old_name, newUVSet=new_name)
                    print(f"{obj}: {old_name} → {new_name}")
                    success_count += 1
                    uv_sets.remove(old_name)
                    uv_sets.append(new_name)
                except Exception as e:
                    cmds.warning(f"重命名失败 {obj} {old_name} → {new_name}: {e}")
    if success_count:
        print(f"已重命名 {success_count} 个 UV 通道")
        cmds.inViewMessage(amg=f'<hl>已重命名 {success_count} 个 UV 通道</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有匹配到可重命名的 UV 通道。")

# 使用预设
rename_uv_channels()

# 自定义示例：
# rename_uv_channels({"map1": "uv0", "map2": "uv1"})
```

</details>

**文件：** [`scripts/rename_uv_channels.py`](scripts/rename_uv_channels.py)

---

### 9. 添加自定义前缀（面板版）

**介绍：** 弹出面板，可自定义前缀名称（默认 old_），点按钮给选中物体添加前缀。已有该前缀的会跳过。带常用预设按钮。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def add_custom_prefix(prefix):
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True)
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    success_count = 0
    for obj in reversed(selected):
        short_name = obj.split('|')[-1]
        if short_name.startswith(prefix):
            print(f"跳过已有前缀的物体: {short_name}")
            continue
        new_name = prefix + short_name
        try:
            cmds.rename(obj, new_name)
            print(f"重命名: {short_name} → {new_name}")
            success_count += 1
        except Exception as e:
            cmds.warning(f"重命名失败 {short_name}: {e}")
    if success_count:
        cmds.inViewMessage(
            amg=f'<hl>已添加前缀 {prefix} 到 {success_count} 个物体</hl>',
            pos='midCenter',
            fade=True
        )
    else:
        cmds.warning("没有物体被修改。")

def open_prefix_panel():
    if cmds.window("addPrefixPanel", exists=True):
        cmds.deleteUI("addPrefixPanel")
    win = cmds.window("addPrefixPanel", title="添加自定义前缀", widthHeight=(320, 180))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=("both", 12))
    cmds.text(label="前缀名称（可自定义）", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 200))
    cmds.text(label="前缀:")
    prefix_field = cmds.textField("prefixField", text="old_", width=200)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(90, 90, 90))
    cmds.button(label="old_", command=lambda x: cmds.textField(prefix_field, e=True, text="old_"))
    cmds.button(label="new_", command=lambda x: cmds.textField(prefix_field, e=True, text="new_"))
    cmds.button(label="temp_", command=lambda x: cmds.textField(prefix_field, e=True, text="temp_"))
    cmds.setParent("..")
    def on_apply(*args):
        prefix = cmds.textField(prefix_field, query=True, text=True).strip()
        add_custom_prefix(prefix)
    cmds.separator(height=15, style="in")
    cmds.button(label="添加前缀到选中物体", height=40, command=on_apply)
    cmds.text(label="先选中物体，再点按钮。已有该前缀的会跳过。", align="center", font="smallPlainLabelFont")
    cmds.showWindow(win)

open_prefix_panel()
```

</details>

**文件：** [`scripts/add_custom_prefix_panel.py`](scripts/add_custom_prefix_panel.py)

---

### 10. 前缀工具面板（添加 + 赋予名字）

**介绍：** 合并面板。可自定义前缀（两个功能都认这个前缀）。
- 添加前缀：给选中物体加前缀（已有则跳过）
- 赋予名字：选中两个物体（一个带前缀、一个不带），把带前缀的名字去掉前缀后赋给不带前缀的那个。

<details>
<summary>点击展开代码（展开后可一键复制）</summary>

```python
import maya.cmds as cmds

def add_custom_prefix(prefix):
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True)
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    success_count = 0
    for obj in reversed(selected):
        short_name = obj.split('|')[-1]
        if short_name.startswith(prefix):
            print(f"跳过已有前缀的物体: {short_name}")
            continue
        new_name = prefix + short_name
        try:
            cmds.rename(obj, new_name)
            print(f"重命名: {short_name} → {new_name}")
            success_count += 1
        except Exception as e:
            cmds.warning(f"重命名失败 {short_name}: {e}")
    if success_count:
        cmds.inViewMessage(
            amg=f'<hl>已添加前缀 {prefix} 到 {success_count} 个物体</hl>',
            pos='midCenter', fade=True
        )
    else:
        cmds.warning("没有物体被修改。")

def transfer_name_without_prefix(prefix):
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    sel = cmds.ls(selection=True, long=True)
    if len(sel) != 2:
        cmds.warning("请正好选中两个物体！")
        return
    prefixed = None
    non_prefixed = None
    for obj in sel:
        short = obj.split('|')[-1]
        if short.startswith(prefix):
            prefixed = obj
        else:
            non_prefixed = obj
    if not prefixed or not non_prefixed:
        cmds.warning(f"必须一个带 '{prefix}' 前缀，一个不带！")
        return
    old_short = prefixed.split('|')[-1]
    new_name = old_short[len(prefix):]
    if not new_name:
        cmds.warning("去掉前缀后名称为空！")
        return
    if cmds.objExists(new_name) and new_name != non_prefixed.split('|')[-1]:
        cmds.warning(f"名称 '{new_name}' 已存在，无法重命名！")
        return
    try:
        result = cmds.rename(non_prefixed, new_name)
        print(f"已将 '{non_prefixed.split('|')[-1]}' 重命名为 '{new_name}'")
        cmds.inViewMessage(
            amg=f'<hl>已赋予名称: {new_name}</hl>',
            pos='midCenter', fade=True
        )
        cmds.select(result)
    except Exception as e:
        cmds.warning(f"重命名失败: {e}")

def open_prefix_tools_panel():
    if cmds.window("prefixToolsPanel", exists=True):
        cmds.deleteUI("prefixToolsPanel")
    win = cmds.window("prefixToolsPanel", title="前缀工具", widthHeight=(340, 260))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=("both", 12))
    cmds.text(label="前缀名称（两个功能都认这个前缀）", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70, 220))
    cmds.text(label="前缀:")
    prefix_field = cmds.textField("prefixField", text="old_", width=220)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(70, 70, 70, 70))
    cmds.button(label="old_", command=lambda x: cmds.textField(prefix_field, e=True, text="old_"))
    cmds.button(label="new_", command=lambda x: cmds.textField(prefix_field, e=True, text="new_"))
    cmds.button(label="temp_", command=lambda x: cmds.textField(prefix_field, e=True, text="temp_"))
    cmds.button(label="bak_", command=lambda x: cmds.textField(prefix_field, e=True, text="bak_"))
    cmds.setParent("..")
    def get_prefix():
        return cmds.textField(prefix_field, query=True, text=True).strip()
    cmds.separator(height=10, style="in")
    cmds.button(label="给选中物体添加前缀", height=36,
                command=lambda x: add_custom_prefix(get_prefix()))
    cmds.button(label="选中两个：去掉前缀赋予名字", height=36,
                command=lambda x: transfer_name_without_prefix(get_prefix()))
    cmds.text(label="添加前缀：选中任意物体\n赋予名字：正好选中两个（一个带前缀，一个不带）",
              align="center", font="smallPlainLabelFont")
    cmds.showWindow(win)

open_prefix_tools_panel()
```

</details>

**文件：** [`scripts/prefix_tools_panel.py`](scripts/prefix_tools_panel.py)
