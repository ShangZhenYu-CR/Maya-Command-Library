# 兼容旧文件路径：此文件现在为轻量 pivot 版（快速匹配枢轴位置与移动工具朝向）。
# 不同步 Channel Box，不永久改变对象本地轴，不遍历或修改模型顶点。
import maya.cmds as cmds


def match_pivot_fast():
    sel = cmds.ls(sl=True, long=True) or []
    if len(sel) < 2 or any(cmds.nodeType(n) != 'transform' for n in sel):
        raise RuntimeError('先选目标，最后选参考；使用物体选择模式。')
    if not cmds.undoInfo(q=True, state=True):
        raise RuntimeError('请先开启 Undo。')

    targets, ref = sel[:-1], sel[-1]
    pos = cmds.xform(ref, q=True, ws=True, rp=True)
    attrs = ('rotatePivot', 'scalePivot',
             'rotatePivotTranslate', 'scalePivotTranslate')

    # 只检查变换属性，不扫描模型顶点。
    for obj in targets:
        if cmds.referenceQuery(obj, isNodeReferenced=True):
            raise RuntimeError('不修改引用物体：' + obj)
        if (cmds.lockNode(obj, q=True, lock=True) or [False])[0]:
            raise RuntimeError('节点已锁定：' + obj)
        for attr in attrs:
            names = [attr] + (cmds.attributeQuery(
                attr, node=obj, listChildren=True) or [])
            for name in names:
                plug = obj + '.' + name
                if not cmds.getAttr(plug, settable=True):
                    raise RuntimeError('属性被锁定或驱动：' + plug)

    before = {n: cmds.xform(n, q=True, ws=True, matrix=True)
              for n in targets}
    changed = False
    cmds.undoInfo(openChunk=True, chunkName='MatchPivotFast')
    try:
        for obj in targets:
            cmds.xform(obj, ws=True, pivots=pos, preserve=True)
            changed = True
            after = cmds.xform(obj, q=True, ws=True, matrix=True)
            if any(abs(a-b) > 1e-7 * max(1.0, abs(a), abs(b))
                   for a, b in zip(before[obj], after)):
                raise RuntimeError('变换保持校验失败：' + obj)
    except Exception:
        cmds.undoInfo(closeChunk=True)
        if changed:
            cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)

    cmds.select(targets, r=True)
    cmds.setToolTo('Move')
    cmds.manipMoveContext('Move', e=True, mode=6, orientObject=ref)
    print('完成：枢轴位置已匹配；移动工具使用参考朝向。')


match_pivot_fast()
