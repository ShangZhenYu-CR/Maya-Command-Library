# MCL Model Renamer — V3

Jira: **MCL-1**  
Current attempt: **0.3.1 / V3**  
Last accepted result: **0.2.0 / V2 — `b77f098f18f93568508d40a243faead7ef5d0b39`**

V3 is implemented as an extension beside the accepted V2 module. The accepted `mcl_model_renamer.py` is intentionally left unchanged; V3 imports and reuses its V1/V2 validation, Face Count, conflict, exact-rename, and rollback-safe helpers.

## Modes in the V3 window

- **Rename Selected** — V1 single-model naming.
- **Rename Pair High / Low** — V2 two-model Face Count naming.
- **Analyze Auto Pairs** — V3 read-only multi-model analysis.
- **Apply Auto Pairs** — V3 batch rename after a valid preview.

## V3 workflow

```text
Select multiple candidate meshes
        ↓
Analyze Auto Pairs
        ↓
Preview resolved pairs / UNRESOLVED items
        ↓
Apply Auto Pairs
```

Analyze never renames scene nodes.

## Pairing rules

V3 compares world-space bounding boxes using center proximity and bounding-box size similarity. Only **mutual best matches** are accepted automatically.

Conservative defaults:

- normalized center-distance limit: `0.25` of average pair bounding-box diagonal;
- average size-mismatch limit: `0.35`;
- if the two best candidate scores differ by `0.05` or less, the object is ambiguous.

Any ambiguous, unpaired, too-distant, size-mismatched, or equal-Face-Count object blocks Apply. Target-name conflicts are treated specially: by default, a target name occupied by another **selected** object is allowed because that object participates in the same batch; a target name occupied by an **unselected** object still blocks Apply.

## Stable numbering

Resolved pairs are sorted by average world center using `X → Z → Y`, so numbering is independent of Maya Selection Order. Within each pair, Face Count still decides High / Low.

## Selected name reuse

**Allow Selected Name Reuse** is enabled by default.

When enabled, selected objects are allowed to occupy names that are targets of the same V3 batch. Apply first moves every participating selected object to a unique temporary name, then writes the final names. This safely handles name swaps and cycles without accepting Maya auto-suffixes.

Unselected objects are never ignored: if an unselected scene object already owns a final target name, Analyze marks that pair as a target conflict and Apply remains blocked.

Turn the option off to restore strict behavior where even selected objects occupying target names are treated as conflicts.

## Apply safety

Analyze stores a signature for selected DAG paths, Face Counts, rounded world bounds, Base/Index, targets, and the selected-name-reuse setting. Apply re-runs analysis. If relevant selection/geometry state, naming inputs, or the conflict setting changed, Apply stops and asks for Analyze again.

The full V3 batch uses one Maya Undo chunk target. If an unexpected rename fails midway, V3 performs a two-phase best-effort rollback to avoid original names blocking each other.

## Installation

Copy these files from the same fixed V3 result into Maya `scripts`:

```text
<Documents>/maya/scripts/
├─ mcl_model_renamer.py       # accepted V2 dependency
├─ mcl_model_renamer_v3.py    # V3 extension
└─ SHELF_LAUNCHER_V3.py
```

## Daily launch

```python
import mcl_model_renamer_v3
mcl_model_renamer_v3.show()
```

## V3 usage

1. Select all candidate High/Low models.
2. Set Base Name and starting Index.
3. Click **Analyze Auto Pairs**.
4. Read the preview list.
5. If any line says `UNRESOLVED`, adjust the selection or use V2 manually.
6. If analysis is ready, click **Apply Auto Pairs**.
7. Index advances by the number of pairs after the whole batch succeeds.

## Out of scope

Manual pair editor, forced ambiguous pairing, recursive Group/Shape naming, History deletion, Freeze Transform, material/hierarchy changes, Maya global-setting changes, and `trackSelectionOrder` changes.
