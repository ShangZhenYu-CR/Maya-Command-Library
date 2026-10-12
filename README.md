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

### 4. 选中模型坐标轴同步成活动模型

**介绍：** 把其他选中物体的坐标轴（旋转/朝向）同步成当前活动物体（最后选中的那个）。使用 world 空间直接设置旋转，更可靠。执行后会有视口提示。

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
    try:
        target_rot = cmds.xform(active, query=True, worldSpace=True, rotation=True)
    except Exception as e:
        cmds.warning(f"无法获取目标旋转: {e}")
        return
    success_count = 0
    for src in sources:
        try:
            cmds.xform(src, worldSpace=True, rotation=target_rot)
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
