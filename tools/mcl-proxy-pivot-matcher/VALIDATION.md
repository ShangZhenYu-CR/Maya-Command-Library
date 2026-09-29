# Validation — MCL-2 V1.2

Date: 2026-09-29  
Current Attempt: MCL Proxy Pivot Matcher V1.2  
Previous V1 fixed result: `0f66c908413f64cdfc72a8eba0d1af8da88ee35e`  
Previous V1.1 fixed result: `07d6b283e750bc2d0cadc8a5ede3b7ee34845bbf`  
Bound spatial reference: MCL-1 V3 `5c650ddea9b80c65769ff914e8cf1127c706208c`

## Real-Maya feedback driving V1.2

V1.1 still did not synchronize Channel Box coordinate values in the user's Maya scene. V1.2 stops relying on `preserveGeometryPosition` and instead writes T/R/S explicitly, then compensates with `offsetParentMatrix` to preserve the Target world matrix.

## Host-independent environment

- Python: 3.13.5
- `python -m compileall -q`: PASS
- `python -m pytest -q --color=no`: PASS

```text
.............                                                            [100%]
13 passed in 0.03s
```

The 13-pass result was executed locally against the V1.2 implementation before GitHub write-back. GitHub final source/test files are separately read back and recorded by Blob SHA; no GitHub CI execution is claimed.

## Covered

- V1 spatial center / size metric regression
- stable pairing independent of selection order
- one-to-one Target ↔ Proxy mapping with unused proxies allowed
- ambiguous candidate blocking
- `|proxy` missing guard
- Proxy object rejected as final Target
- read-only Analyze
- Analyze/Apply stale-bounds guard
- Analyze/Apply stale Proxy T/R/S guard
- Target T/R/S values become exactly equal to Proxy values in the Fake Maya host
- `rotateOrder` is synchronized
- `offsetParentMatrix` compensation is written explicitly
- Fake Maya verifies Target world matrix is unchanged after coordinate rebalance
- pure matrix test verifies `local * offsetParent * parent == originalWorld`
- singular local matrices are rejected by matrix inversion
- pivot matching remains in the operation
- one Undo chunk around the full Apply batch
- static absence of rename / history deletion / freeze / soft-edge / optionVar / global selection-order changes
- V1.2 source no longer uses `preserveGeometryPosition`

## Pending Maya host verification

- actual Channel Box Translate / Rotate / Scale values exactly match Proxy
- Target world-space geometry / transform remains visually unchanged
- pivot position and orientation match Proxy after rebalance
- behavior when `offsetParentMatrix` is already non-identity but writable
- non-default Rotate Order behavior
- construction-history / deformer production assets
- whole-batch Undo
- specific Maya-version compatibility

This is verification evidence, not user acceptance.
