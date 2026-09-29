# Validation — MCL-1 V2

Date: 2026-09-29  
Current attempt: MCL Model Renamer 0.2.0 / V2  
Baseline: accepted V1 Commit `1ccb910e71d5210b4e7ccedf2c4c12cba81ec572`  
Branch: `MCL-1-model-renamer-v2`

## Host-independent checks

Environment:

```text
Python 3.13.5
```

Commands executed against the V2 implementation content:

```bash
python -m compileall -q .
python -m pytest -q
```

Observed result:

```text
.............................                                            [100%]
29 passed in 0.05s
```

## V1 regression coverage

- `{Base}_{Index}_{Role}` generation.
- Two-digit minimum Index and 99 → 100.
- Namespace-preserving leaf target construction.
- Invalid Base / Role / Index rejection.
- V1 Rename Selected UI entry retained.
- Reference, lock, non-intermediate Mesh, exact-name conflict, and no-auto-suffix safeguards retained.

## V2 logic coverage

- `{Base}_{Index}_high` / `{Base}_{Index}_low` pair name generation.
- First model higher Face Count → first is high.
- Second model higher Face Count → second is high.
- Equal Face Count raises a user-facing error.
- Negative invalid Face Count is rejected.

## Fake Maya transaction coverage

A focused fake `maya.cmds` host verifies:

1. Successful pair rename assigns the correct High / Low roles and advances Index once.
2. Equal Face Count performs no Rename calls.
3. Existing target-name conflict performs no Rename calls.
4. Simulated failure on the second rename rolls the first rename back to its original name.
5. Pair operation opens and closes one Undo chunk.

This fake-host evidence validates control flow only; it is not Autodesk Maya host evidence.

## Static safety coverage

Confirmed present:

- `referenceQuery`
- `lockNode`
- `noIntermediate=True`
- `polyEvaluate(..., face=True)`
- pair preflight
- exact-name verification
- pair rollback path
- separate pair Undo chunk

Confirmed absent:

- History deletion
- Freeze Transform
- `polySoftEdge`
- `optionVar` writes

## Pending real Maya host verification

The following remain unverified in Autodesk Maya:

- V2 UI rendering and callbacks.
- Face Count values returned for real selected transforms.
- Higher/lower assignment with real polygon meshes.
- Equal Face Count stop behavior.
- Pair name conflicts in a real scene.
- Referenced / Locked behavior.
- Namespace behavior.
- Unexpected second-rename failure and rollback in Maya.
- One-step Undo of the pair.
- V1 single-mode regression in the real host.
- Compatibility with any specific Maya version.

This document records test evidence only. It is not user acceptance.
