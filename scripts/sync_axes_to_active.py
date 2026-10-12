import maya.cmds as cmds

def sync_axes_to_active():
    """把选中物体的坐标轴（旋转）同步成当前活动物体（最后选中的那个）。
    
    - 最后选中的物体作为目标（active）
    - 其他选中物体的世界旋转会被设置为与目标物体一致
    - 使用 xform 直接设置 world rotation，更可靠
    """
    selected = cmds.ls(selection=True, type="transform")
    
    if len(selected) < 2:
        cmds.warning("请至少选中两个物体（最后选中的作为目标）！")
        return
    
    # 最后选中的作为活动物体
    active = selected[-1]
    sources = selected[:-1]
    
    # 获取活动物体的世界旋转
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
    
    cmds.select(selected)  # 保持原选择
    print(f"已将 {success_count} 个物体的坐标轴同步到: {active}")
    cmds.inViewMessage(
        amg=f'<hl>已同步 {success_count} 个物体的坐标轴</hl>',
        pos='midCenter',
        fade=True
    )

# 执行
sync_axes_to_active()
