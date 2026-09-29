# MCL Proxy Pivot Matcher — MCL-2 V1

Batch-match final-model pivots to corresponding proxy models.

## Maya workflow

1. Create a root group named exactly `proxy` (`|proxy`).
2. Put proxy mesh transforms anywhere under that group.
3. Select the final mesh transforms you want to update.
4. Run the tool and click **Analyze**.
5. Review the Target <= Proxy preview.
6. If all targets resolve, click **Apply Match Pivots**.
7. If needed, use one Maya Undo immediately to restore the batch.

## Matching behavior

- Uses world-space bounding-box center distance plus size similarity.
- Uses conservative one-to-one Target ↔ Proxy matching.
- Selection order does not determine pairing.
- Unused proxy objects are allowed.
- Ambiguous, too-far, or size-mismatched targets block Apply.
- Proxy objects are read-only sources.

## Scene modification

Apply calls Maya `matchTransform(target, proxy, pivots=True)` only.
It does not request translation, rotation, or scale matching and does not rename,
delete history, freeze transforms, soften edges, or write Maya global settings.

## Installation

Copy `mcl_proxy_pivot_matcher.py` into the Maya scripts folder.

Maya Script Editor → Python:

```python
import mcl_proxy_pivot_matcher
mcl_proxy_pivot_matcher.show()
```

The same two lines can be used on a Shelf button.

## Bound reference

Spatial matching behavior was adapted from the fixed MCL-1 V3 reference result:
`5c650ddea9b80c65769ff914e8cf1127c706208c`.

MCL-2 is standalone at runtime and does not alter the MCL-1 accepted/current files.
