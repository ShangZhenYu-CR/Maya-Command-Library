# MCL Proxy Pivot Matcher — MCL-2 V1.1

Batch-match final-model pivots **and Channel Box T/R/S values** to spatially corresponding proxy models.

## Maya workflow

1. Create a root group named exactly `proxy` (`|proxy`).
2. Put proxy mesh transforms anywhere under that group.
3. Select the final mesh transforms you want to update.
4. Run the tool and click **Analyze**.
5. Review the Target <= Proxy preview.
6. If all targets resolve, click **Apply Pivots + Coordinates**.
7. Verify that the final model's Translate / Rotate / Scale values now match the Proxy while the final geometry remains visually stationary.
8. If needed, use one Maya Undo immediately to restore the batch.

## V1.1 behavior

V1 only matched pivot information. V1.1 also synchronizes the Proxy's visible Channel Box:

- Translate X/Y/Z
- Rotate X/Y/Z
- Scale X/Y/Z

The tool uses Maya `move`, `rotate`, and `scale` with `preserveGeometryPosition=True` so the transform values can change while Maya applies the opposite compensation to geometry points. `preserveChildPosition=True` is also used for child transforms. After T/R/S synchronization, the tool runs `matchTransform(..., pivots=True)` to match the Proxy pivot.

If Maya cannot set the Target channel values exactly, the batch stops and asks for Undo.

## Matching behavior

- Uses world-space bounding-box center distance plus size similarity.
- Uses conservative one-to-one Target ↔ Proxy matching.
- Selection order does not determine pairing.
- Unused proxy objects are allowed.
- Ambiguous, too-far, or size-mismatched targets block Apply.
- Analyze signatures include Target / Proxy T/R/S values; changing those values after Analyze forces re-analysis.
- Proxy objects are read-only sources.

## Safety

- Full Apply uses one Undo chunk.
- Locked / connected Target T/R/S channels block the operation before that Target is changed.
- No rename.
- No Delete History.
- No Freeze Transform.
- No global Maya settings changes.

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
