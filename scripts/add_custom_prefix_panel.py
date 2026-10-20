import maya.cmds as cmds

def add_custom_prefix(prefix):
    """给选中物体添加自定义前缀。
    
    已有该前缀的会跳过。
    """
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
    
    # 常用预设按钮
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


# 打开面板
open_prefix_panel()
