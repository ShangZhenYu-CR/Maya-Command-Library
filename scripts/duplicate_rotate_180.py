import maya.cmds as cmds

def duplicate_and_rotate_180():
    """复制当前选中的物体，并让复制体沿当前旋转轴旋转 180 度。
    
    - 自动识别当前 Rotate Tool 的激活轴（X/Y/Z）
    - 如果当前不是旋转工具，则默认沿 Y 轴旋转
    - 复制后自动选中新物体
    """
    selected = cmds.ls(selection=True)
    
    if not selected:
        cmds.warning("没有选中任何物体！")
        return
    
    # 获取当前旋转轴
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
    
    # 复制
    duplicates = cmds.duplicate(selected, returnRootsOnly=True)
    
    # 构建旋转值
    rotate_value = [0, 0, 0]
    if axis == "X":
        rotate_value[0] = 180
    elif axis == "Y":
        rotate_value[1] = 180
    elif axis == "Z":
        rotate_value[2] = 180
    
    for dup in duplicates:
        cmds.rotate(
            rotate_value[0], rotate_value[1], rotate_value[2],
            dup, relative=True, objectSpace=True
        )
    
    cmds.select(duplicates)
    print(f"已复制并沿 {axis} 轴旋转 180 度")

# 执行
duplicate_and_rotate_180()
