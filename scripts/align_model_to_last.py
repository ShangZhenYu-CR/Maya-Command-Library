import maya.cmds as cmds

def align_model_to_last():
    # 先选需要对齐的模型，最后 Shift 选参考物体。
    selected = cmds.ls(sl=True, long=True) or []
    if len(selected) < 2 or any(
        cmds.nodeType(x) != "transform" for x in selected
    ):
        raise RuntimeError("请在物体模式下先选目标，最后选参考物体。")
    if not cmds.undoInfo(q=True, state=True):
        raise RuntimeError("请先开启 Maya Undo。")

    reference = selected[-1]
    targets = selected[:-1]
    attrs = (
        "translate", "rotate", "scale", "shear", "rotateAxis",
        "rotatePivot", "scalePivot",
        "rotatePivotTranslate", "scalePivotTranslate"
    )
    values = {
        a: cmds.getAttr(reference + "." + a)[0] for a in attrs
    }
    order = cmds.getAttr(reference + ".rotateOrder")
    parent = cmds.listRelatives(reference, parent=True, fullPath=True) or []

    for obj in targets:
        if (cmds.listRelatives(obj, parent=True, fullPath=True) or []) != parent:
            raise RuntimeError("请让目标与参考处于同一父级：" + obj)
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            raise RuntimeError("不修改引用物体：" + obj)
        if cmds.getAttr(obj + ".inheritsTransform") != cmds.getAttr(
            reference + ".inheritsTransform"
        ):
            raise RuntimeError("Inherits Transform 状态不同：" + obj)
        if cmds.attributeQuery("offsetParentMatrix", node=obj, exists=True):
            if cmds.getAttr(obj + ".offsetParentMatrix") != cmds.getAttr(
                reference + ".offsetParentMatrix"
            ):
                raise RuntimeError("Offset Parent Matrix 不同：" + obj)
        for attr in attrs + ("rotateOrder",):
            children = cmds.attributeQuery(
                attr, node=obj, listChildren=True) or [attr]
            for child in children:
                if not cmds.getAttr(obj + "." + child, settable=True):
                    raise RuntimeError("属性被锁定或驱动：" + obj + "." + child)

    changed = False
    cmds.undoInfo(openChunk=True, chunkName="AlignModelToLast")
    try:
        for obj in targets:
            cmds.setAttr(obj + ".rotateOrder", order)
            changed = True
            for attr in attrs:
                cmds.setAttr(obj + "." + attr, *values[attr])
        print("完成：目标的位移、旋转、缩放及坐标系已匹配参考。")
    except Exception:
        cmds.undoInfo(closeChunk=True)
        if changed:
            cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)

align_model_to_last()
