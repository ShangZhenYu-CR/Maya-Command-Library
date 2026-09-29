# MCL Model Renamer — V2

Jira: **MCL-1**  
Current attempt: **0.2.0 / V2**  
Last accepted result: **0.1.0 / V1 — `1ccb910e71d5210b4e7ccedf2c4c12cba81ec572`**

## Purpose

Two naming modes share the same Base and Index.

### Single mode — V1 retained

```text
{Base}_{Index}_{Role}
```

Example:

```text
A_01_low
A_02_low
A_03_low
```

### Pair High / Low mode — V2

Select exactly two local Mesh transforms. The tool compares total polygon Face Count across non-intermediate Mesh shapes:

- higher Face Count → `{Base}_{Index}_high`
- lower Face Count → `{Base}_{Index}_low`
- both use the same Index
- Index advances once only after both exact renames succeed
- equal Face Count stops without renaming

Example:

```text
A_05_high
A_05_low
next index -> 06
```

## V2 UI

- Base Name
- Index
- Role (single mode only)
- Single Preview
- Pair Preview
- **Rename Selected** — V1 single mode
- **Rename Pair High / Low** — V2 pair mode
- **Reset to 01**

## Pair validation and safety

Before changing the scene, V2 requires:

- exactly two distinct selected items;
- both are local Transform nodes;
- both contain at least one non-intermediate Mesh shape;
- neither is referenced;
- neither is locked;
- Face Count values can be read;
- Face Counts are different;
- both exact target names are free.

If any preflight fails, neither model is renamed and Index does not advance.

If the first model has already been renamed and the second rename unexpectedly fails, the tool attempts to restore the first model automatically. If rollback is incomplete, the error explicitly tells the user to use Maya Undo immediately.

Maya automatic suffixes such as `A_01_high1` are not accepted.

## Namespace behavior

The existing namespace of each Transform is preserved; only the leaf name changes.

Example:

```text
characterA:pCube1 -> characterA:A_01_high
characterB:pCube2 -> characterB:A_01_low
```

## Installation

Copy these files into a Maya scripts directory:

```text
<Documents>/maya/scripts/
├─ mcl_model_renamer.py
└─ SHELF_LAUNCHER.py
```

No third-party dependency is required.

## Daily launch

In **Maya Script Editor → Python**:

```python
import mcl_model_renamer
mcl_model_renamer.show()
```

The same code can be used in a Shelf button.

## Usage — Single mode

1. Select exactly one local Mesh Transform.
2. Set Base Name, Index, and Role.
3. Confirm Single Preview.
4. Click **Rename Selected**.
5. On exact success, Index advances once.

## Usage — Pair mode

1. Select exactly two local Mesh Transforms.
2. Set Base Name and Index. The Role field is ignored by pair mode.
3. Confirm Pair Preview, for example `A_01_high / A_01_low`.
4. Click **Rename Pair High / Low**.
5. The higher-poly model becomes `_high`, the lower-poly model becomes `_low`.
6. If both succeed, Index advances once.

## Undo

Single and pair actions each use one Maya Undo chunk as their target behavior.

V2 does not synchronize the UI Index with Maya Undo. After undoing a rename, manually restore Index if needed.

## Out of scope

- V3 multi-model spatial pairing.
- Guessing High / Low when Face Counts are equal.
- Manual pair editor.
- Shape or Group auto-renaming.
- Persistent settings.
- History deletion.
- Freeze Transform.
- Material changes.
- Hierarchy changes.
- Maya global-setting changes.

## Compatibility

Host-independent checks do not prove compatibility with a specific Maya release. Actual Maya version support is recorded only after real host verification.
