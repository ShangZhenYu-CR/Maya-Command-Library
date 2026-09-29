# Tests

`test_pure_logic.py` runs outside Maya and checks deterministic naming/index/namespace behavior.

`test_maya_contract_static.py` checks important safety contracts in source text. It is not a substitute for real Maya host verification.

Run from the tool directory:

```bash
python -m pytest -q
```
