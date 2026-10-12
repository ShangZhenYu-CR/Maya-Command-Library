import maya.cmds as cmds

def remove_pasted_prefix():
    """移除选中物体名称中因粘贴而产生的 pasted__ 前缀。
    
    - 只处理以 pasted__ 开头的物体
    - 支持多选和层级物体
    - 从后往前处理，减少命名冲突
    """
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

# 执行
remove_pasted_prefix()
