# MCL Proxy Pivot Matcher — MCL-2 V1.2

Batch-match final-model pivots **and Channel Box T/R/S values** to spatially corresponding proxy models while preserving the Target world matrix.

## Maya workflow

1. Create a root group named exactly `proxy` (`|proxy`).
2. Put proxy mesh transforms anywhere under that group.
3. Select the final mesh transforms you want to update.
4. Run the tool and click **Analyze**.
5. Review the Target <= Proxy preview.
6. If all targets resolve, click **Apply Pivots + Coordinates V1.2**.
7. Verify the final model Translate / Rotate / Scale values match the Proxy while the final model remains in the same world-space transform.
8. Use one Maya Undo to restore the batch if needed.

## V1.2 behavior

V1 only matched pivots. V1.1 attempted T/R/S synchronization using `preserveGeometryPosition`, but real Maya testing showed the Channel Box values still did not synchronize reliably.

V1.2 changes the mechanism:

- Match Proxy pivot information.
- Copy Proxy `rotateOrder`.
- Write Proxy Translate / Rotate / Scale values directly to the Target with `setAttr`.
- Read the resulting Target local matrix.
- Solve a compensating `offsetParentMatrix` so the Target world matrix remains equal to its pre-operation world matrix.
- Verify the written T/R/S values remain exact and verify the world matrix is unchanged.

Maya post-multiplies transform matrices. V1.2 solves the compensation using:

`offsetParentMatrix = inverse(localAfter) * worldBefore * inverse(parentWorld)`

so that:

`localAfter * offsetParentMatrix * parentWorld == worldBefore`

## Matching behavior

- Uses world-space bounding-box center distance plus size similarity.
- Uses conservative one-to-one Target ↔ Proxy matching.
- Selection order does not determine pairing.
- Unused proxy objects are allowed.
- Ambiguous, too-far, or size-mismatched targets block Apply.
- Analyze signatures include Target / Proxy T/R/S values.
- Proxy objects are read-only sources.

## Safety

- Full Apply uses one Undo chunk.
- Locked / connected Target T/R/S channels block the operation.
- Locked / connected `offsetParentMatrix` blocks the operation.
- Zero/singular resulting local matrices are rejected.
- No rename.
- No Delete History.
- No Freeze Transform.
- No global Maya settings changes.

## Installation

Copy `mcl_proxy_pivot_matcher.py` into the Maya scripts folder.

Maya Script Editor → Python:

```python
import importlib
import mcl_proxy_pivot_matcher
importlib.reload(mcl_proxy_pivot_matcher)
mcl_proxy_pivot_matcher.show()
```

After restarting Maya, a Shelf button can use:

```python
import mcl_proxy_pivot_matcher
mcl_proxy_pivot_matcher.show()
```

## Bound reference

Spatial matching behavior was adapted from the fixed MCL-1 V3 reference result:
`5c650ddea9b80c65769ff914e8cf1127c706208c`.

MCL-2 is standalone at runtime and does not alter MCL-1 files.
