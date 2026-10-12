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

**文件：** [`scripts/add_old_prefix.py`](scripts/add_old_prefix.py)（点进去可一键复制）

---

### 2. 移除 pasted__ 前缀

**介绍：** 移除选中物体名称中因粘贴而产生的 `pasted__` 前缀。只处理带有该前缀的物体，其他跳过。

**文件：** [`scripts/remove_pasted_prefix.py`](scripts/remove_pasted_prefix.py)（点进去可一键复制）

---

### 3. 复制并沿当前轴旋转 180 度

**介绍：** 复制当前选中的物体，并让复制体沿当前旋转工具的激活轴（X/Y/Z）旋转 180 度。若当前不是旋转工具，则默认沿 Y 轴。复制后自动选中新物体。

**文件：** [`scripts/duplicate_rotate_180.py`](scripts/duplicate_rotate_180.py)（点进去可一键复制）
