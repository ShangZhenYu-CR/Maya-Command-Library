# Changelog

## 0.3.0 — 2026-09-29

### Added

- Companion `mcl_model_renamer_v3.py` extension built on the accepted V2 module without modifying V2 source.
- Analyze → Preview → Apply multi-model Auto Pair workflow.
- World-space center and bounding-box-size matching.
- Mutual-best pairing and ambiguity rejection.
- Stable pair numbering by world center (`X → Z → Y`) independent of selection order.
- Apply-time state signature validation.
- Whole-batch preflight, rollback attempt, and one Undo chunk target.
- V3 fake-host tests for successful multi-pair Apply, stale-analysis rejection, ambiguity, odd selection, equal Face Count, and rollback.

## 0.2.0 — 2026-09-29

- Two-model Face Count High / Low mode.

## 0.1.0 — 2026-09-29

- Initial sequential `{Base}_{Index}_{Role}` rename mode.
