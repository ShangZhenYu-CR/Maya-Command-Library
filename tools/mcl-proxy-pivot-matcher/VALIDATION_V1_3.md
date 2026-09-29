# Validation — MCL-2 V1.3

Date: 2026-09-29

Current Attempt: MCL Proxy Pivot Matcher V1.3

Previous fixed results:
- V1: `0f66c908413f64cdfc72a8eba0d1af8da88ee35e`
- V1.1: `07d6b283e750bc2d0cadc8a5ede3b7ee34845bbf`
- V1.2: `4d8390d4b082463013cd0c6efa639fb1afdd0c61`

Host-independent verification:
- compileall: PASS
- pytest: 19 passed
- Sync Names Off: no rename
- Sync Names On: Final takes Proxy base name
- matched Proxy gets configurable prefix, default `synced_`
- repeated prefix is not duplicated
- sibling name conflicts block before scene modification
- namespace name sync is rejected
- prefix changes require re-analysis
- V1.2 pivot / exact T/R/S / offsetParentMatrix regression remains covered

Pending Maya host verification:
- V1.2 coordinate behavior
- V1.3 UI option behavior
- Final / Proxy names in real Maya
- whole-batch Undo including names

No GitHub CI run is claimed. User acceptance remains pending.
