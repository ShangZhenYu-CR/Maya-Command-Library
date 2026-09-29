import importlib, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mcl_model_renamer as base
import mcl_model_renamer_v3 as v3

def bounds(cx,cy,cz,s=2): return (cx-s/2,cy-s/2,cz-s/2,cx+s/2,cy+s/2,cz+s/2)
class Fake:
    def __init__(self, selection, specs, fail=None):
        self.selection=list(selection); self.transforms=set(specs); self.shapes={n:[n+'|S'] for n in specs}; self.faces={n+'|S':specs[n][0] for n in specs}; self.boxes={n:specs[n][1] for n in specs}; self.calls=[]; self.undo=[]; self.fail=fail
    def ls(self,v=None,selection=False,long=False,flatten=False,**k):
        if selection:return list(self.selection)
        if v in self.transforms or v in self.faces:return [v]
        return sorted(n for n in self.transforms if n.rsplit('|',1)[-1]==v) if v else []
    def objExists(self,n): return n in self.transforms or n in self.faces
    def nodeType(self,n): return 'transform' if n in self.transforms else 'mesh'
    def listRelatives(self,n,**k): return self.shapes.get(n,[])
    def referenceQuery(self,n,**k): return False
    def lockNode(self,n,**k): return [False]
    def polyEvaluate(self,s,**k): return self.faces[s]
    def exactWorldBoundingBox(self,n): return self.boxes[n]
    def undoInfo(self,**k): self.undo.append(k)
    def rename(self,n,t):
        if t==self.fail: raise RuntimeError('fail')
        new='|'+t; self.transforms.remove(n); self.transforms.add(new); self.shapes[new]=self.shapes.pop(n); self.boxes[new]=self.boxes.pop(n); self.selection=[new if x==n else x for x in self.selection]; self.calls.append((n,t)); return t

def setup(fake): base.cmds=fake; v3.cmds=fake

def specs4(): return {'|H1':(500,bounds(0,0,0)),'|L1':(100,bounds(.02,0,0)),'|H2':(600,bounds(10,0,0)),'|L2':(120,bounds(10.02,0,0))}

def test_metric_rejects_far_and_size_mismatch():
    assert v3.bbox_pair_metric(bounds(0,0,0), bounds(0,0,0))['eligible']
    assert not v3.bbox_pair_metric(bounds(0,0,0), bounds(10,0,0))['eligible']
    assert not v3.bbox_pair_metric(bounds(0,0,0,2), bounds(0,0,0,10))['eligible']

def test_pairing_stable_under_selection_order():
    s=specs4(); f=Fake(['|L2','|H1','|L1','|H2'],s); setup(f); a=v3.analyze_auto_pairs('A','01'); assert a['ready']; sig=a['signature']; f.selection.reverse(); assert v3.analyze_auto_pairs('A','01')['signature']==sig

def test_apply_four_models_two_pairs():
    s=specs4(); f=Fake(list(s),s); setup(f); a=v3.analyze_auto_pairs('A','01'); r=v3.rename_auto_pairs('A','01',a['signature']); assert r['pair_count']==2 and r['next_index']=='03'; assert {'|A_01_high','|A_01_low','|A_02_high','|A_02_low'} <= f.transforms

def test_changed_selection_requires_analyze_again():
    s=specs4(); f=Fake(list(s),s); setup(f); a=v3.analyze_auto_pairs('A','01'); f.selection=f.selection[:2]
    with pytest.raises(base.RenameError, match='Analyze again'): v3.rename_auto_pairs('A','01',a['signature'])

def test_changed_bounds_requires_analyze_again():
    s=specs4(); f=Fake(list(s),s); setup(f); a=v3.analyze_auto_pairs('A','01'); f.boxes['|L1']=bounds(.1,0,0)
    with pytest.raises(base.RenameError, match='Analyze again'): v3.rename_auto_pairs('A','01',a['signature'])

def test_odd_selection_not_ready():
    s=specs4(); f=Fake(['|H1','|L1','|H2'],s); setup(f); assert not v3.analyze_auto_pairs('A','01')['ready']

def test_equal_faces_not_ready():
    s={'|A':(100,bounds(0,0,0)),'|B':(100,bounds(.01,0,0))}; f=Fake(list(s),s); setup(f); a=v3.analyze_auto_pairs('A','01'); assert not a['ready'] and any(r=='same_face_count' for _,r in a['unresolved'])

def test_ambiguous_cluster_not_ready():
    s={'|A':(500,bounds(0,0,0)),'|B':(100,bounds(.01,0,0)),'|C':(200,bounds(-.01,0,0)),'|D':(50,bounds(10,0,0))}; f=Fake(list(s),s); setup(f); assert not v3.analyze_auto_pairs('A','01')['ready']

def test_mid_batch_failure_rolls_back():
    s=specs4(); f=Fake(list(s),s,fail='A_02_low'); setup(f); a=v3.analyze_auto_pairs('A','01')
    with pytest.raises(base.RenameError, match='Auto-pair rename failed'): v3.rename_auto_pairs('A','01',a['signature'])
    assert {'|H1','|L1','|H2','|L2'} <= f.transforms

def test_v3_source_contains_analyze_preview_apply_contract():
    source = (Path(__file__).resolve().parents[1] / 'mcl_model_renamer_v3.py').read_text(encoding='utf-8')
    for token in ('exactWorldBoundingBox', 'Analyze Auto Pairs', 'Apply Auto Pairs', 'expected_signature', 'UNDO_CHUNK_AUTO'):
        assert token in source


def test_v3_source_does_not_change_global_or_destructive_maya_state():
    source = (Path(__file__).resolve().parents[1] / 'mcl_model_renamer_v3.py').read_text(encoding='utf-8')
    for token in ('deleteHistory', 'makeIdentity', 'polySoftEdge', 'optionVar(', 'trackSelectionOrder'):
        assert token not in source
