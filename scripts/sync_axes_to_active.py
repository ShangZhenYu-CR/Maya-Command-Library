import maya.cmds as cmds

def sync_axes_to_active():
    """把选中物体的坐标轴（朝向）同步成当前活动物体（最后选中的那个）。
    
    - 最后选中的物体作为目标（active）
    - 使用临时 Orient Constraint 强制匹配朝向，然后删除约束
    - 这种方式比直接设置 xform rotation 更可靠，能真正对齐局部坐标轴
    """
    selected = cmds.ls(selection=True, type="transform")
    
    if len(selected) < 2:
        cmds.warning("请至少选中两个物体（最后选中的作为目标）！")
        return
    
    # 最后选中的作为活动物体
    active = selected[-1]
    sources = selected[:-1]
    
    success_count = 0
    for src in sources:
        try:
            # 创建临时朝向约束强制匹配
            constraint = cmds.orientConstraint(active, src, maintainOffset=False)[0]
            # 立即删除约束，保留已匹配的旋转
            cmds.delete(constraint)
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

# 执行
sync_axes_to_active()
