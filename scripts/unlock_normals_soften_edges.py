import maya.cmds as cmds

def unlock_normals_soften_edges():
    """解锁选中模型的法线并软化边缘，然后删除历史。
    
    - 解锁法线（unFreezeNormal）
    - 软化所有边（angle=180）
    - 删除建模历史
    """
    sel = cmds.ls(selection=True, long=True)
    
    if not sel:
        cmds.warning("没有选中任何物体！")
        return
    
    processed = []
    
    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True)
        
        if shapes:
            try:
                # Unlock Normals
                cmds.polyNormalPerVertex(shapes[0], unFreezeNormal=True)
                
                # Soften Edge
                cmds.polySoftEdge(obj, angle=180)
                
                processed.append(obj)
            except Exception as e:
                cmds.warning(f"处理失败 {obj}: {e}")
    
    if processed:
        # Delete History
        cmds.delete(processed, constructionHistory=True)
        print(f"Normals unlocked + edges softened: {processed}")
        cmds.inViewMessage(
            amg=f'<hl>已解锁法线并软化边: {len(processed)} 个物体</hl>',
            pos='midCenter',
            fade=True
        )
    else:
        cmds.warning("没有找到可处理的 mesh。")

# 执行
unlock_normals_soften_edges()
