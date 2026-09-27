# Classroom demo — 10 September 2026

Double-click **Start.cmd** in this folder. Open http://127.0.0.1:8511 if the browser does not open automatically. Keep this laptop plugged in for live AI inference. The prepared examples and installed model cache work locally; no installation is needed on this laptop.

## Five-minute walkthrough

1. **Classroom demo tab:** introduce the pipeline: image/video → IVP enhancement and features → AI observations → rule evidence → export. Explain that automatic violation analysis is still in development.
2. **Workspace:** choose “Low-light street · simulated darkness”. Change the sidebar preset from Original to Low light. Show Before / after, Processing stages, and Quality + histograms. Darkness is simulated; this is a controlled enhancement demonstration.
3. Choose “Noisy street · simulated noise” and the Noisy footage preset. Show the filter controls. In Feature views, demonstrate edges, thresholding, colour masks and morphology. Colour masks do not establish traffic-light meaning.
4. **Classroom demo:** show Road users + video. Cyan boxes and IDs visualise actual recorded YOLO detections. Play the exported MP4. This is a four-second still-photo clip with test audio, not moving traffic. It verifies inference, tracking IDs, timing and audio export.
5. Switch Saved AI example to Crossing segmentation, then Traffic-sign recognition. Explain how semantic road segmentation constrains IVP white-region extraction, and how IVP sign proposals feed classification.
6. Optional live inference: Workspace → Original street → Original preset → AI analysis → Analyse image with AI. Wait for the background job below the export controls. If time is short, return to the saved examples, which need no model loading.
7. Open a result’s downloads to show processed media, settings, masks, coordinate mapping, and per-frame AI decisions.

## What to say

“Our IVP pipeline enhances and measures footage, extracts masks and road features, and preserves video timing. Our AI integration detects road users, tracks them, segments the road and recognises some signs. The rule engine combines observations over time and leaves uncertain cases unassessed. We are still validating automatic road interpretation and traffic-rule accuracy.”

There are no confirmed violation examples in this prepared gallery. Do not describe cyan detection boxes as green violation boxes. A pedestrian’s bare head is not evidence of a motorcycle helmet violation. The nine rule identifiers and tested logic do not mean all nine are validated on real traffic.

## Recovery

- If live AI is slow, use Classroom demo; it reads completed outputs from demo/results without loading models.
- Cancel an active job using Cancel processing. Do not launch multiple processing jobs together.
- If the app was closed, use Start.cmd again. Stop.cmd stops the web server.
- Keep demo, .venv, ai-runtime.json, and the configured H: model/runtime folders in place. This is prepared for the current laptop, not packaged as a portable installer.
- Sample attribution appears in the app. Demo assets can be rebuilt with `.venv\Scripts\python.exe prepare_demo.py` from the existing QA source files and saved runs.

Further AI development is deferred until after today’s demonstration; the original project goal remains unfinished.
