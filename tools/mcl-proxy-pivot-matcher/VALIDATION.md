# Validation — MCL-2 V1

Date: 2026-09-29  
Current Attempt: MCL Proxy Pivot Matcher V1  
Bound spatial reference: MCL-1 V3 `5c650ddea9b80c65769ff914e8cf1127c706208c`

## Host-independent environment

- Python: 3.13.5
- `python -m compileall -q`: PASS
- `python -m pytest -q --color=no`: PASS

```text
...........                                                              [100%]
11 passed in 0.03s
```

## Covered

- center / size spatial metric
- stable pairing independent of selection order
- one-to-one Target ↔ Proxy mapping with unused proxies allowed
- ambiguous candidate blocking
- `|proxy` missing guard
- proxy object rejected as final Target
- read-only Analyze
- Analyze/Apply stale-bounds guard
- `matchTransform(..., pivots=True)` only
- one Undo chunk around the full Apply batch
- partial failure closes the Undo chunk and explicitly instructs Undo
- static absence of rename / history deletion / freeze / soft-edge / optionVar / global selection-order changes

## Pending Maya host verification

- actual `|proxy` descendant discovery in production scenes
- actual Match Pivots result including pivot orientation
- final-model world-space geometry remains visually stationary
- proxy models remain unchanged
- one Maya Undo restores the whole successful batch
- partial-failure recovery with one Undo
- referenced / locked / nested-group edge cases in real scenes
- specific Maya-version compatibility

This is verification evidence, not user acceptance.
