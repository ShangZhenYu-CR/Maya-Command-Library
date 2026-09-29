# Tests

Existing V1/V2 tests remain unchanged from the accepted V2 baseline.

V3 adds `test_v3.py`, covering spatial metrics, stable mutual pairing, batch Apply, stale-analysis rejection, ambiguity/unpaired handling, equal Face Count, rollback, and source safety contracts.

V3 extension check executed locally:

```text
python -m compileall -q mcl_model_renamer_v3.py
pytest -q
11 passed
```

Fake-host tests do not replace real Autodesk Maya verification.
