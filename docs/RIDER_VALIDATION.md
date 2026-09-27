# Rider association regression — 17 September 2026

Review of the two crowded Indian uploads found background people incorrectly counted on foreground motorcycles. Their lower-body boxes fitted the expanded seat rectangle even when their full bodies ended near the top of the motorcycle. This produced three false triple-riding decisions across two photographs.

The association now additionally requires a person box to reach at least 35% down the motorcycle box, and person height to be at least 60% of motorcycle height. These are scale-relative geometric checks, not learned rider verification. Existing ambiguity checks, unique head attribution, and video shared-motion requirements remain in place.

## Recorded detection replay

The frozen detections in tests/fixtures/rider_association_cases.json come from actual saved model runs. Replaying these isolates the association change from model inference differences. Expected counts were checked against the visible photos.

| Source run | Before | After |
|---|---|---|
| 20260910-142821-8a465c8e | Two triple-riding flags and one helmet flag | No triple-riding flags; one helmet flag. One associated person per foreground motorcycle |
| 20260910-142525-26d57158 | One triple-riding flag and one helmet flag | No triple-riding flags; one helmet flag. Two people retained on the foreground motorcycle |
| 20260910-144025-1ee42eb2 | Two helmet flags | Both helmet flags retained |

The full suite passed 82 tests, including a positive synthetic three-rider association to verify the rule is still reachable.

A fresh complete GPU-enabled image job, runs/20260917-115310-47213a41, reran the first problematic photograph with its original settings. It completed successfully and reported only helmet_absence, confirming removal of both false triple-riding flags through the actual worker and inference path.

## Limits

This is a fix evaluated on known development cases, not an independent accuracy benchmark. Height and position checks can reject partially occluded riders or small children, and cannot reliably distinguish a similarly sized pedestrian beside a stationary motorcycle. Positive real triple-riding recall, crowded-scene accuracy, and pose-based seat association remain unverified. No model was retrained, and no detection scores or image pixels were changed to obtain these results.
