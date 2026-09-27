# AI implementation checkpoint

The AI phase is authorised and under construction. The local app now includes working experimental AI image/video jobs alongside IVP. Do not describe the modules as a finished nine-rule traffic analyser yet.

## Architecture

`perception.py` runs pretrained YOLO11s road-user detection, explicit ByteTrack tracking, and a separate helmet/bare-head detector. `scene.py` produces language-grounded scene object proposals. `segmentation.py` supplies road/sidewalk masks and camera-stability checks. `markings.py` and `arrows.py` combine proposals with classical IVP geometry. Proposals are not automatically trusted legal road boundaries. `signs.py` recognises a limited set of sign candidates; road applicability, controlling-signal association, and scene-confidence validation remain incomplete.

`contracts.py` defines source-coordinate detections and timestamped decisions. `rules.py` evaluates nine rule categories against explicit evidence. `riders.py` supplies geometric association proposals; this association has not been validated on crowded traffic and needs motion/occlusion checks before production use. Complete visibility is intentionally not inferred from detections alone.

`events.py` adds temporal confirmation and event deduplication. Transition events are preserved immediately because crossing observations may only last one frame. `render.py` draws green boxes for supplied confirmed violation decisions without modifying source pixels.

## Runtime

Run `Setup-AI.ps1 -RuntimeHome H:\CodexStorage\ivp-ai` to create the separate Python 3.11 environment on this machine. The local `ai-runtime.json` records its location and is excluded from source control. The script does not replace the IVP environment or system Python. CUDA wheels are large; retain ample space on the selected drive. Models download on first use.

After setup completes, run from the project directory:

```powershell
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m traffic_ai.smoke temp/qa/traffic_bus.jpg --output temp/qa/ai_perception.json
```

This command tests detections, not traffic-rule correctness. AI requirements are pinned in requirements-ai.txt; new reports record model revisions and detector-weight hashes.

## Sources

- Ultralytics installation and prediction API: https://docs.ultralytics.com/quickstart/
- Explicit ByteTrack usage: https://docs.ultralytics.com/modes/track/
- Helmet model and weights: https://huggingface.co/iam-tsr/yolov8n-helmet-detection
- Grounding DINO integration: https://huggingface.co/docs/transformers/model_doc/grounding-dino
- Sign classifier: https://huggingface.co/bazyl/gtsrb-model

## Outstanding acceptance work

Complete automatic scene reasoning, test pretrained perception on real traffic, integrate image/video background jobs and exports, validate all nine rule categories with positive/negative/ambiguous footage, preserve IVP timing/audio/cancellation behavior, and inspect results in the browser. Passing synthetic tests does not establish detector precision or recall. No AI accuracy claim is currently supported.
