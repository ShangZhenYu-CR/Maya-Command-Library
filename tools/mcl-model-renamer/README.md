# MCL Model Renamer — V1

Jira: **MCL-1**  
Status: development / current attempt  
Initial version: **0.1.0**

## Purpose

Rename one selected local Maya mesh transform at a time using a predictable sequential pattern:

```text
{Base}_{Index}_{Role}
```

Example:

```text
A_01_low
A_02_low
A_03_low
```

## V1 scope

- Base Name, Index, Role fields.
- Live preview when a field is committed.
- Exactly one selected local mesh transform.
- Preserve existing namespace and replace only the leaf name.
- Scene-wide short-name conflict preflight.
- Reject Maya auto-suffixed results such as `A_01_low1`.
- Advance Index only after exact rename success.
- Failed operations do not advance Index.
- One Maya Undo chunk per rename action.
- Reset Index to `01`.

## Out of scope

- Two-model High/Low face-count detection.
- Multi-model spatial High/Low pairing.
- One-click batch rename.
- Shape or Group auto-renaming.
- Persistent settings.
- Maya global-setting changes.
- History deletion, Freeze Transform, material changes, or hierarchy edits.

## Installation

Copy these two files into a Maya scripts directory, for example:

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

For a Shelf button, copy the complete contents of `SHELF_LAUNCHER.py`.

## Usage

1. Select exactly one local mesh **Transform** in Maya.
2. Set `Base Name`, `Index`, and `Role`.
3. Confirm the Preview, for example `A_01_low`.
4. Click **Rename Selected**.
5. On success the object is renamed exactly and Index advances to the next value.

## Validation and failure behavior

The tool stops before modifying the scene when:

- nothing or more than one item is selected;
- a component, shape, camera, light, locator, joint, or non-mesh transform is selected;
- the object is referenced;
- the object is locked;
- Base / Index / Role is invalid;
- the exact target short name already exists anywhere in the scene.

A failed rename never intentionally advances Index. Maya automatic suffixing is not accepted.

## Undo

A successful rename is wrapped in one Maya Undo chunk. `Ctrl+Z` should restore the scene rename when verified in the target Maya host.

V1 intentionally does **not** synchronize the UI Index with Maya Undo. If you undo a rename, manually set the Index back as needed.

## Compatibility

Actual Maya host compatibility is recorded only after real verification. The implementation uses `maya.cmds` only and has no PySide dependency, but that does not by itself prove support for any specific Maya version.
