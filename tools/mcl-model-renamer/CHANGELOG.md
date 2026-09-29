# Changelog

## 0.2.0 — 2026-09-29

### Added

- Two-model **Rename Pair High / Low** mode.
- Total Face Count comparison across non-intermediate Mesh shapes.
- Higher Face Count → `_high`; lower Face Count → `_low`.
- Equal Face Count rejection without scene modification.
- Pair preview using the current Base and Index.
- Pair-level preflight for both targets before scene mutation.
- Automatic rollback attempt if a later pair rename fails.
- Pair operation uses one Maya Undo chunk target.
- Fake Maya transaction tests for success, equal-count rejection, conflict rejection, and rollback.

### Preserved

- V1 single-model `{Base}_{Index}_{Role}` behavior.
- V1 exact-name conflict protection.
- V1 namespace preservation.
- Success-only Index advancement.

## 0.1.0 — 2026-09-29

### Added

- Initial MCL-1 V1 implementation.
- `{Base}_{Index}_{Role}` naming rule.
- Single local mesh-transform validation.
- Namespace-preserving leaf rename.
- Exact short-name conflict protection.
- Success-only index advancement.
- One-action Maya Undo chunk target.
- Lightweight `maya.cmds` UI and Shelf launcher.
