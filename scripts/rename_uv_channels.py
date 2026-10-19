import maya.cmds as cmds

def rename_uv_channels(rename_map=None):
    """
    重命名选中模型的 UV 通道。
    
    默认预设：
    - map1 → map2
    - uv0 → uv1
    
    可传入自定义字典手动指定旧名称到新名称的映射。
    例：rename_uv_channels({"map1": "uv0", "map2": "uv1"})
    """
    if rename_map is None:
        # 预设映射
        rename_map = {
            "map1": "map2",
            "uv0": "uv1"
        }
    
    sel = cmds.ls(selection=True, long=True)
    if not sel:
        cmds.warning("没有选中任何物体！")
        return
    
    success_count = 0
    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True, noIntermediate=True)
        if not shapes:
            continue
        
        shape = shapes[0]
        if cmds.nodeType(shape) != "mesh":
            continue
        
        try:
            uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
        except Exception:
            continue
        
        for old_name in list(uv_sets):
            if old_name in rename_map:
                new_name = rename_map[old_name]
                if new_name in uv_sets:
                    print(f"跳过 {obj}: {new_name} 已存在")
                    continue
                try:
                    cmds.polyUVSet(shape, rename=True, uvSet=old_name, newUVSet=new_name)
                    print(f"{obj}: {old_name} → {new_name}")
                    success_count += 1
                    # 更新本地列表避免重复处理
                    if old_name in uv_sets:
                        uv_sets.remove(old_name)
                    uv_sets.append(new_name)
                except Exception as e:
                    cmds.warning(f"重命名失败 {obj} {old_name} → {new_name}: {e}")
    
    if success_count:
        print(f"已重命名 {success_count} 个 UV 通道")
        cmds.inViewMessage(
            amg=f'<hl>已重命名 {success_count} 个 UV 通道</hl>',
            pos='midCenter',
            fade=True
        )
    else:
        cmds.warning("没有匹配到可重命名的 UV 通道。")

# 使用预设运行（map1→map2, uv0→uv1）
rename_uv_channels()

# 自定义示例（取消上面的调用，改用下面）：
# rename_uv_channels({"map1": "uv0", "map2": "uv1"})
# rename_uv_channels({"map1": "uvSet1"})
