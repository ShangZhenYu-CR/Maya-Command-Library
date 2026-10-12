import maya.cmds as cmds

def sync_axes_to_active():
    """把选中物体的坐标轴（旋转）同步成当前活动物体（最后选中的那个）。
    
    - 最后选中的物体作为目标（active）
    - 其他选中物体的旋转会被匹配到目标物体
    - 使用 world 空间匹配旋转，让局部坐标轴朝向一致
    """
    selected = cmds.ls(selection=True, type="transform")
    
    if len(selected) < 2:
        cmds.warning("请至少选中两个物体（最后选中的作为目标）！")
        return
    
    # 最后选中的作为活动物体
    active = selected[-1]
    sources = selected[:-1]
    
    try:
        # 匹配旋转（world space）
        cmds.matchTransform(sources, active, rotation=True)
        print(f"已将 {len(sources)} 个物体的坐标轴同步到: {active}")
    except Exception as e:
        cmds.warning(f"同步失败: {e}")

# 执行
sync_axes_to_active()
