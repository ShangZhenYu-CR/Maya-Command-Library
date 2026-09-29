# Validation — MCL-1 V3

Date: 2026-09-29  
Current attempt: MCL Model Renamer 0.3.0 / V3  
Baseline: accepted V2 Commit `b77f098f18f93568508d40a243faead7ef5d0b39`  
Branch: `MCL-1-model-renamer-v3`

## Baseline preservation

V3 is a companion extension. The accepted V2 file `mcl_model_renamer.py` is intentionally not modified by V3. GitHub V2→V3 diff/read-back is used to verify this.

## V3 host-independent checks

Environment: Python 3.13.5 / pytest 9.0.2.

```text
python -m compileall -q mcl_model_renamer_v3.py
pytest -q
........... [100%]
11 passed
```

The V3 tests use a focused V2 API test double for the already-accepted helper contract. They do not replace V2 acceptance evidence or real Maya verification.

Covered: center/size metric, far/size mismatch rejection, selection-order-independent pairing, four-model/two-pair Apply, changed-selection and changed-bounds re-analysis, odd selection, equal Face Count, ambiguous cluster, mid-batch rollback, Analyze/Apply signature contract, and absence of destructive/global Maya operations.

## Pending real Maya host verification

- V3 unified window and preview readability;
- real multi-pair spatial matching;
- stable numbering under changed selection order;
- ambiguous/unpaired blocking;
- Analyze → move a model → Apply stale-analysis rejection;
- whole-batch Undo;
- V1/V2 buttons still work through the V3 window;
- specific Maya-version compatibility.

This is verification evidence, not user acceptance.
