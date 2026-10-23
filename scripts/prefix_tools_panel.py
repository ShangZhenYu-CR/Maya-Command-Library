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
    """选中两个物体：一个带前缀、一个不带。
    把带前缀的名字去掉前缀后，赋给不带前缀的那个。
    """
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

    cmds.text(label="添加前缀：选中任意物体
赋予名字：正好选中两个（一个带前缀，一个不带）",
              align="center", font="smallPlainLabelFont")

    cmds.showWindow(win)


# 打开面板
open_prefix_tools_panel()
