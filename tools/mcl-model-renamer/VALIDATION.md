# Validation — MCL-1 V1

Date: 2026-09-29  
Current attempt: MCL Model Renamer 0.1.0  
Branch: `MCL-1-model-renamer-v1`

## Host-independent checks

Environment:

```text
Python 3.13.5
```

Commands executed against the implementation content before GitHub write:

```bash
python -m compileall -q .
python -m pytest -q
```

Observed result:

```text
...................                                                      [100%]
19 passed in 0.05s
```

Coverage of these checks:

- deterministic `{Base}_{Index}_{Role}` generation;
- two-digit minimum index formatting and 99 → 100 progression;
- namespace-preserving target leaf construction;
- invalid Base / Role / Index rejection;
- static presence of reference, lock, non-intermediate mesh, conflict, exact-name, and Undo-chunk safeguards;
- static absence of out-of-scope history deletion, Freeze Transform, polySoftEdge, and optionVar writes.

## Pending Maya host verification

The following are **not yet verified in Autodesk Maya**:

- actual UI rendering and callbacks;
- valid mesh transform rename in Maya;
- empty / multi / component / non-mesh selection behavior;
- referenced and locked node behavior;
- scene short-name conflict behavior;
- exact refusal of Maya automatic numeric suffixes;
- one-action Undo behavior;
- namespace behavior in a real Maya scene;
- compatibility with any specific Maya version.

This document records test evidence only. It is not user acceptance.
