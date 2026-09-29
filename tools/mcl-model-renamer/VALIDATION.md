# Validation — MCL-1 V3

Date: 2026-09-29  
Current attempt: MCL Model Renamer 0.3.1 / V3 Attempt 2  
Baseline: accepted V2 Commit `b77f098f18f93568508d40a243faead7ef5d0b39`  
Previous V3 review result: `776cfcc85059e6f7d78b36c17663044dd12103dc`  
Branch: `MCL-1-model-renamer-v3`

## Baseline preservation

V3 remains a companion extension. The accepted V2 file `mcl_model_renamer.py` is unchanged; current Git blob remains `e8d504f04267fe79990ae8bc334701873552c0c9`.

## Previous V3 verification

Before this conflict-handling patch, V3 focused tests passed:

```text
Python 3.13.5 / pytest 9.0.2
11 passed
```

That evidence belongs to the previous V3 review result and is retained as historical verification.

## Attempt 2 — selected-name-reuse checks

The current patch was write-read-back checked on GitHub and exercised with a focused executable harness for the new behavior.

Observed focused harness results:

```text
selected occupier ignored when reuse = On          PASS
same selected occupier blocks when reuse = Off     PASS
unselected external occupier still blocks          PASS
two-phase temp rename handles internal occupancy   PASS
mid-batch failure two-phase rollback restores      PASS
```

Repository tests were expanded with cases for:

- selected internal target names allowed by default;
- strict mode blocks selected target occupancy;
- unselected external target conflict remains blocking;
- selected-name-reuse setting participates in Analyze/Apply signature;
- UI/default constant is present.

The full repository pytest suite was not re-executed in the current connector runtime after this patch, so no new aggregate pytest count is claimed here.

## Behavior contract

Default:

```text
Allow Selected Name Reuse = On
```

- selected object owns target name → allowed;
- unselected object owns target name → blocked;
- duplicate final targets inside the plan → blocked;
- Apply first renames all participating objects to unique temporary names;
- final names are then written exactly;
- Maya auto-suffix results are not accepted;
- rollback uses a temporary-name phase before restoring originals.

## Still pending real Maya verification

- checkbox appears enabled by default;
- the user's original selected-name-conflict scene now Analyzes successfully;
- Apply correctly reuses selected names without numeric suffixes;
- an unselected target-name occupier still blocks;
- one Undo restores the whole V3 batch;
- V1 / V2 buttons remain normal through the V3 window;
- specific Maya-version compatibility.

This is verification evidence, not V3 user acceptance.
