import maya.cmds as cmds

def get_short_name(obj):
    return obj.split('|')[-1]

def rename_object(obj, new_name):
    """Safe rename with existence check."""
    if not new_name or new_name == get_short_name(obj):
        return None
    if cmds.objExists(new_name) and new_name != get_short_name(obj):
        # Try to find unique name
        base = new_name
        i = 1
        while cmds.objExists(new_name):
            new_name = f"{base}{i}"
            i += 1
    try:
        result = cmds.rename(obj, new_name)
        return result
    except Exception as e:
        cmds.warning(f"重命名失败 {get_short_name(obj)} → {new_name}: {e}")
        return None

def add_prefix(prefix):
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        if short.startswith(prefix):
            continue
        new_name = prefix + short
        if rename_object(obj, new_name):
            count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已添加前缀 {prefix} 到 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def remove_prefix(prefix):
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        if short.startswith(prefix):
            new_name = short[len(prefix):]
            if new_name and rename_object(obj, new_name):
                count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已移除前缀 {prefix} 从 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def set_prefix(prefix):
    """Remove existing prefix if present, then add the new one (idempotent set)."""
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        # Strip if already starts with this prefix
        if short.startswith(prefix):
            base = short[len(prefix):]
        else:
            base = short
        if not base:
            continue
        new_name = prefix + base
        if new_name != short and rename_object(obj, new_name):
            count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已设置前缀 {prefix} 到 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def add_suffix(suffix):
    if not suffix:
        cmds.warning("后缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        if short.endswith(suffix):
            continue
        new_name = short + suffix
        if rename_object(obj, new_name):
            count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已添加后缀 {suffix} 到 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def remove_suffix(suffix):
    if not suffix:
        cmds.warning("后缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        if short.endswith(suffix):
            new_name = short[:-len(suffix)]
            if new_name and rename_object(obj, new_name):
                count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已移除后缀 {suffix} 从 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def set_suffix(suffix):
    if not suffix:
        cmds.warning("后缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        if short.endswith(suffix):
            base = short[:-len(suffix)]
        else:
            base = short
        if not base:
            continue
        new_name = base + suffix
        if new_name != short and rename_object(obj, new_name):
            count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已设置后缀 {suffix} 到 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def replace_prefix(old_prefix, new_prefix):
    if not old_prefix:
        cmds.warning("旧前缀不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for obj in reversed(selected):
        short = get_short_name(obj)
        if short.startswith(old_prefix):
            base = short[len(old_prefix):]
            new_name = (new_prefix or "") + base
            if new_name and rename_object(obj, new_name):
                count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已替换前缀 {old_prefix} → {new_prefix or "(空)"} 于 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def set_formal_name(formal_name):
    """Set selected objects to a formal/clean name. Multi-select appends numbers."""
    if not formal_name:
        cmds.warning("正式名不能为空！")
        return
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    count = 0
    for i, obj in enumerate(reversed(selected)):
        name = formal_name if len(selected) == 1 else f"{formal_name}{i+1:02d}"
        if rename_object(obj, name):
            count += 1
    if count:
        cmds.inViewMessage(amg=f'<hl>已设置正式名 {formal_name} 到 {count} 个物体</hl>', pos='midCenter', fade=True)
    else:
        cmds.warning("没有物体被修改。")

def transfer_name_without_prefix(prefix, hide_after=False):
    """选中两个物体：一个带前缀、一个不带。把带前缀的名字去掉前缀后赋给不带前缀的那个。"""
    if not prefix:
        cmds.warning("前缀不能为空！")
        return
    sel = cmds.ls(selection=True, long=True) or []
    if len(sel) != 2:
        cmds.warning("请正好选中两个物体！")
        return

    prefixed = None
    non_prefixed = None
    for obj in sel:
        short = get_short_name(obj)
        if short.startswith(prefix):
            prefixed = obj
        else:
            non_prefixed = obj

    if not prefixed or not non_prefixed:
        cmds.warning(f"必须一个带 '{prefix}' 前缀，一个不带！")
        return

    old_short = get_short_name(prefixed)
    new_name = old_short[len(prefix):]
    if not new_name:
        cmds.warning("去掉前缀后名称为空！")
        return

    if cmds.objExists(new_name) and new_name != get_short_name(non_prefixed):
        cmds.warning(f"名称 '{new_name}' 已存在，无法重命名！")
        return

    try:
        result = cmds.rename(non_prefixed, new_name)
        cmds.inViewMessage(amg=f'<hl>已赋予名称: {new_name}</hl>', pos='midCenter', fade=True)
        if hide_after:
            to_hide = [prefixed, result]
            cmds.hide(to_hide)
        cmds.select(result)
    except Exception as e:
        cmds.warning(f"重命名失败: {e}")

def open_naming_tools_panel():
    if cmds.window("namingToolsPanel", exists=True):
        cmds.deleteUI("namingToolsPanel")

    win = cmds.window("namingToolsPanel", title="命名工具", widthHeight=(420, 520))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnOffset=("both", 10))

    # Prefix section
    cmds.text(label="前缀", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(60, 320))
    cmds.text(label="前缀:")
    prefix_field = cmds.textField("namingPrefixField", text="old_", width=320)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=5, columnWidth5=(70, 70, 70, 70, 70))
    cmds.button(label="old_", command=lambda x: cmds.textField(prefix_field, e=True, text="old_"))
    cmds.button(label="new_", command=lambda x: cmds.textField(prefix_field, e=True, text="new_"))
    cmds.button(label="temp_", command=lambda x: cmds.textField(prefix_field, e=True, text="temp_"))
    cmds.button(label="bak_", command=lambda x: cmds.textField(prefix_field, e=True, text="bak_"))
    cmds.button(label="pasted__", command=lambda x: cmds.textField(prefix_field, e=True, text="pasted__"))
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 120, 120))
    cmds.button(label="添加前缀", height=32, command=lambda x: add_prefix(cmds.textField(prefix_field, q=True, text=True).strip()))
    cmds.button(label="移除前缀", height=32, command=lambda x: remove_prefix(cmds.textField(prefix_field, q=True, text=True).strip()))
    cmds.button(label="设置前缀", height=32, command=lambda x: set_prefix(cmds.textField(prefix_field, q=True, text=True).strip()))
    cmds.setParent("..")

    cmds.separator(height=8, style="in")

    # Suffix section
    cmds.text(label="后缀", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(60, 320))
    cmds.text(label="后缀:")
    suffix_field = cmds.textField("namingSuffixField", text="_old", width=320)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(80, 80, 80, 80))
    cmds.button(label="_old", command=lambda x: cmds.textField(suffix_field, e=True, text="_old"))
    cmds.button(label="_bak", command=lambda x: cmds.textField(suffix_field, e=True, text="_bak"))
    cmds.button(label="_temp", command=lambda x: cmds.textField(suffix_field, e=True, text="_temp"))
    cmds.button(label="_pasted", command=lambda x: cmds.textField(suffix_field, e=True, text="_pasted"))
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 120, 120))
    cmds.button(label="添加后缀", height=32, command=lambda x: add_suffix(cmds.textField(suffix_field, q=True, text=True).strip()))
    cmds.button(label="移除后缀", height=32, command=lambda x: remove_suffix(cmds.textField(suffix_field, q=True, text=True).strip()))
    cmds.button(label="设置后缀", height=32, command=lambda x: set_suffix(cmds.textField(suffix_field, q=True, text=True).strip()))
    cmds.setParent("..")

    cmds.separator(height=8, style="in")

    # Replace prefix
    cmds.text(label="替换前缀", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(70, 100, 100, 100))
    cmds.text(label="旧 → 新:")
    old_p_field = cmds.textField("namingOldPrefix", text="old_", width=100)
    new_p_field = cmds.textField("namingNewPrefix", text="new_", width=100)
    cmds.button(label="替换", height=28, command=lambda x: replace_prefix(
        cmds.textField(old_p_field, q=True, text=True).strip(),
        cmds.textField(new_p_field, q=True, text=True).strip()
    ))
    cmds.setParent("..")

    cmds.separator(height=8, style="in")

    # Formal name
    cmds.text(label="正式名", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(60, 320))
    cmds.text(label="名称:")
    formal_field = cmds.textField("namingFormalField", text="", width=320)
    cmds.setParent("..")
    cmds.button(label="设置正式名（多选自动编号）", height=32,
                command=lambda x: set_formal_name(cmds.textField(formal_field, q=True, text=True).strip()))

    cmds.separator(height=8, style="in")

    # Assign name (transfer)
    cmds.text(label="赋予名字（选中两个：一个带前缀、一个不带）", align="left", font="boldLabelFont")
    hide_check = cmds.checkBox("namingHideAfter", label="命名后隐藏这两个物体", value=False)
    cmds.button(label="去掉前缀并赋予名字", height=36,
                command=lambda x: transfer_name_without_prefix(
                    cmds.textField(prefix_field, q=True, text=True).strip(),
                    hide_after=cmds.checkBox(hide_check, q=True, value=True)
                ))

    cmds.text(label="添加/移除/设置：作用于选中物体\n赋予名字：正好选中两个（一个带当前前缀，一个不带）\n正式名：把选中物体改成指定名称（多选自动加 01, 02...）",
              align="center", font="smallPlainLabelFont")

    cmds.showWindow(win)

# 打开面板
open_naming_tools_panel()
