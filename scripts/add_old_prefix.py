import maya.cmds as cmds

def add_old_prefix():
    """给当前选中的物体名称添加 old_ 前缀。
    
    - 支持多选和层级物体
    - 已有 old_ 前缀的物体会被跳过
    - 从后往前处理，减少命名冲突
    """
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

# 执行
add_old_prefix()
