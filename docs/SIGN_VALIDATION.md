# Sign recognition checks — 9 September 2026

The local classifier is `bazyl/gtsrb-model`, revision `95f6c95c765e1705d7f92161a5a42a40a5bd8338`. It is a ViT model trained on GTSRB. Its published evaluation score is not an accuracy measurement for our project or Indian traffic footage.

Model source: https://huggingface.co/bazyl/gtsrb-model

Sign-crop samples came from the model author's demonstration at https://huggingface.co/spaces/bazyl/gtsrb/tree/main/examples. The original files and experiment reports are in `temp/qa/signs`, outside submission output. These are cropped sign photographs; the experiment does not test sign localisation in full traffic scenes.

| File | Model classification | Our resulting observation |
|---|---|---|
| 00009.png | Ahead only | Recognised candidate after colour/shape corroboration |
| 00027.png | No passing vehicles over 3.5 tons | Cannot assess; outside current supported rule constraints |
| 00052.png | No vehicles | Recognised candidate after colour/shape corroboration |
| 00072.png | Beware of ice/snow | Cannot assess; outside current supported rule constraints |
| traffic_bus.jpg | Turn right ahead (incorrect on a nonsign image) | Rejected by corroboration filter |

The initial filter rejected both supported sign photographs. Inspection showed that fixed colour/shape thresholds were too brittle for faded colours and partial occlusion. The refined filter combines modest colour thresholds, morphological closing, convex-hull shape checks, and classifier score/margin requirements. It accepts the two supported examples and still rejects the bus photograph. This small development check is not independent validation or a benchmark.

Reports: `temp/qa/signs/results.json` and `temp/qa/signs/results_refined.json`.

## Full processing-path check

The initial image job `runs/20260909-213625-052b8474` failed to route the no-vehicles sign to the classifier: Grounding DINO called it a traffic light. Added an independent IVP proposal path using circular red/blue colour regions, morphological closing, convex hulls, size/aspect checks, and duplicate suppression. Classification still decides the sign label; the geometric proposal alone does not.

The subsequent completed job `runs/20260909-213746-6af376d8` exports a recognised No vehicles candidate with `proposal_source: ivp_colour_shape`. It has no associated approach and generates no violation. The scene inspector and downloadable JSON/masks expose the observation for review. This is an end-to-end test on a cropped photograph, not evidence of reliable full-road restriction enforcement.

The classifier also exposes a null class label; it remains unsupported. A detected truck is not assumed to exceed a weight restriction. Keep-left/right signs are not interpreted as prohibited turns. Recognised sign candidates have no associated approach by default; road applicability and exception plates still need assessment. Explicit no-left/no-right/no-U-turn sign coverage and real-scene evaluations remain outstanding.

The upstream model's original `pytorch_model.bin` is loaded explicitly with the pinned revision. This avoids an automatic network conversion lookup during every startup. The tested second classification run completed in about six seconds with cached weights.
