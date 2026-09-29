# Tests

- `test_pure_logic.py`: deterministic V1 naming plus V2 pair-name / Face Count classification.
- `test_maya_contract_static.py`: source-level safety and scope contracts.
- `test_pair_fake_maya.py`: focused fake `maya.cmds` transaction tests for pair success, equal Face Count rejection, conflict rejection, and rollback.

Run from the tool directory:

```bash
python -m compileall -q .
python -m pytest -q
```

Fake-host and static tests do not replace real Autodesk Maya verification.
