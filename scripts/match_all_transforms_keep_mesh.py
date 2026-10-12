import maya.cmds as cmds
import maya.api.OpenMaya as om

def match_all_transforms_keep_mesh():
    sel = cmds.ls(sl=True, long=True) or []
    if len(sel) < 2 or any(cmds.nodeType(x) != "transform" for x in sel):
        raise RuntimeError("物体模式：先选需要修改的模型，最后 Shift 选参考物体。")
    if not cmds.undoInfo(q=True, state=True):
        raise RuntimeError("请先开启 Maya Undo。")
    ref, targets = sel[-1], sel[:-1]
    parent = cmds.listRelatives(ref, parent=True, fullPath=True) or []
    identity = (1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1)
    data = []
    def fail(message):
        raise RuntimeError(message)
    def is_instanced(node):
        selection = om.MSelectionList()
        selection.add(node)
        path = selection.getDagPath(0)
        return path.isInstanced()
    # 相同父级保证旋转数值一致时，轴的参考空间也一致。
    for obj in sel:
        if (cmds.listRelatives(obj, parent=True, fullPath=True) or []) != parent:
            fail("目标和参考必须在同一个父级下：" + obj)
        if is_instanced(obj):
            fail("暂不支持实例：" + obj)
        if not cmds.getAttr(obj + ".inheritsTransform"):
            fail("暂不支持关闭 Inherits Transform：" + obj)
        if cmds.attributeQuery("offsetParentMatrix", node=obj, exists=True):
            matrix = cmds.getAttr(obj + ".offsetParentMatrix")
            if any(abs(a-b) > 1e-10 for a, b in zip(matrix, identity)):
                fail("暂不支持非默认 Offset Parent Matrix：" + obj)
        if any(abs(v) > 1e-10 for v in cmds.getAttr(obj + ".shear")[0]):
            fail("暂不支持 Shear：" + obj)
        if any(v <= 1e-10 for v in cmds.getAttr(obj + ".scale")[0]):
            fail("暂不支持负缩放或零缩放：" + obj)
    for obj in targets:
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            fail("不修改引用物体：" + obj)
        if cmds.listRelatives(obj, children=True, type="transform"):
            fail("请直接选择不带子物体的模型：" + obj)
        shapes = cmds.listRelatives(
            obj, shapes=True, noIntermediate=True, fullPath=True) or []
        if not shapes or any(cmds.nodeType(s) != "mesh" for s in shapes):
            fail("目标必须是多边形模型：" + obj)
        for attr in (
            "translate", "rotate", "scale", "rotateAxis", "rotateOrder",
            "rotatePivot", "scalePivot",
            "rotatePivotTranslate", "scalePivotTranslate",
            "offsetParentMatrix", "inheritsTransform"
        ):
            plug = obj + "." + attr
            if cmds.objExists(plug) and (
                cmds.getAttr(plug, lock=True) or
                cmds.listConnections(plug, source=True, destination=False)
            ):
                fail("属性被锁定或驱动：" + plug)
        meshes = []
        for shape in shapes:
            if is_instanced(shape):
                fail("暂不支持实例 Shape：" + shape)
            for node in cmds.listHistory(shape) or []:
                types = cmds.nodeType(node, inherited=True) or []
                if ("geometryFilter" in types or
                    cmds.nodeType(node).startswith("animCurve") or
                    cmds.nodeType(node) == "expression"):
                    fail("暂不支持蒙皮、变形器或动画历史：" + obj)
            verts = shape + ".vtx[*]"
            if any(cmds.polyNormalPerVertex(
                    verts, q=True, freezeNormal=True) or []):
                fail("模型有锁定法线，本版本不处理：" + obj)
            points = cmds.xform(
                verts, q=True, worldSpace=True, translation=True) or []
            if not points:
                fail("模型没有顶点：" + obj)
            meshes.append((shape, points))
        data.append((obj, meshes))
    order = cmds.getAttr(ref + ".rotateOrder")
    copy_attrs = (
        "translate", "rotate", "scale", "shear", "rotateAxis",
        "rotatePivot", "scalePivot",
        "rotatePivotTranslate", "scalePivotTranslate"
    )
    reference_values = {
        attr: cmds.getAttr(ref + "." + attr)[0] for attr in copy_attrs
    }
    reference_matrix = cmds.xform(ref, q=True, worldSpace=True, matrix=True)
    changed = False
    cmds.undoInfo(openChunk=True, chunkName="MatchAllTransformsKeepMesh")
    try:
        for obj, meshes in data:
            cmds.setAttr(obj + ".rotateOrder", order)
            changed = True
            # 变换数值、轴朝向、枢轴位置全部复制参考物体。
            for attr in copy_attrs:
                cmds.setAttr(obj + "." + attr, *reference_values[attr])
            # 用可撤销的 Maya 命令反补偿顶点，模型在世界空间不动。
            for shape, points in meshes:
                for i in range(len(points) // 3):
                    cmds.xform(
                        "{}.vtx[{}]".format(shape, i),
                        worldSpace=True, translation=points[3*i:3*i+3])
                check = cmds.xform(
                    shape + ".vtx[*]", q=True,
                    worldSpace=True, translation=True)
                if len(check) != len(points) or any(
                    abs(a-b) > 1e-5 for a, b in zip(points, check)
                ):
                    fail("顶点位置校验失败。")
            for attr, expected in reference_values.items():
                actual = cmds.getAttr(obj + "." + attr)[0]
                if any(abs(a-b) > 1e-8 for a, b in zip(actual, expected)):
                    fail("通道数值校验失败：" + obj + "." + attr)
            actual_matrix = cmds.xform(obj, q=True, worldSpace=True, matrix=True)
            if any(abs(a-b) > 1e-8
                   for a, b in zip(actual_matrix, reference_matrix)):
                fail("坐标系校验失败：" + obj)
    except Exception:
        cmds.undoInfo(closeChunk=True)
        if changed:
            cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)
        print("完成：参考不变；目标模型不动；TRS 数值、轴及枢轴全部同步。")

match_all_transforms_keep_mesh()
