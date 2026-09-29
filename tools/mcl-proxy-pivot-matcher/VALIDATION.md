# Validation — MCL-2 V1.1

Date: 2026-09-29  
Current Attempt: MCL Proxy Pivot Matcher V1.1  
Previous V1 fixed result: `0f66c908413f64cdfc72a8eba0d1af8da88ee35e`  
Bound spatial reference: MCL-1 V3 `5c650ddea9b80c65769ff914e8cf1127c706208c`

## Real-Maya feedback driving V1.1

V1 successfully matched pivots/axes but did **not** synchronize Channel Box coordinate values. Root cause: V1 used `matchTransform(..., pivots=True)`, which only matches pivot information.

V1.1 adds T/R/S synchronization from Proxy → Target while preserving final geometry position using Maya's `preserveGeometryPosition` option, then runs Match Pivots.

## Host-independent environment

- Python: 3.13.5
- `python -m compileall -q`: PASS
- `python -m pytest -q --color=no`: PASS

```text
............                                                             [100%]
12 passed in 0.03s
```

## Covered

- V1 spatial center / size metric regression
- stable pairing independent of selection order
- one-to-one Target ↔ Proxy mapping with unused proxies allowed
- ambiguous candidate blocking
- `|proxy` missing guard
- proxy object rejected as final Target
- read-only Analyze
- Analyze/Apply stale-bounds guard
- Analyze/Apply stale Proxy T/R/S guard
- Target T/R/S values become exactly equal to Proxy values in the Fake Maya host
- Translate uses absolute parent/local-space values with `preserveGeometryPosition=True`
- Rotate uses absolute object-space values with `preserveGeometryPosition=True`
- Scale uses absolute local-space values with `preserveGeometryPosition=True`
- child transforms request `preserveChildPosition=True`
- pivot matching still uses `matchTransform(..., pivots=True)`
- one Undo chunk around the full Apply batch
- static absence of rename / history deletion / freeze / soft-edge / optionVar / global selection-order changes

## Pending Maya host verification

- actual Channel Box Translate / Rotate / Scale values exactly match Proxy
- final-model geometry remains visually stationary after T/R/S rebalance
- pivot position and orientation still match Proxy after coordinate synchronization
- behavior with non-default rotate orders
- behavior with construction history / deformers in production assets
- proxy models remain unchanged
- one Maya Undo restores the whole successful batch
- locked / connected channel error handling in real Maya
- specific Maya-version compatibility

This is verification evidence, not user acceptance.
