# Traffic Lab — IVP and AI

**New installation:** follow the [Windows installation guide](INSTALL.md) for prerequisites, cloning, IVP setup, optional local AI setup, verification and troubleshooting.

The [AI explainer PDF](output/pdf/AI_Traffic_Analyser_Explained.pdf) describes the architecture as of 24 September 2026. See [PROGRESS.md](PROGRESS.md) for subsequent changes.

A local image and video processing application for the combined IVP and AI traffic-camera project. The IVP workflow is implemented; the AI workflow is experimental and under active development. It runs vehicle/person and helmet detection, tracking, scene-feature extraction, and evidence-based rule logic. Full automatic interpretation of all nine traffic-rule categories is not complete or accuracy-validated.

## Current handoff — 18 October 2026

**Use the existing installation:** double-click [Start.cmd](Start.cmd), then open [Traffic Lab](http://127.0.0.1:8511/). The H-drive Python environment and local model already exist on this computer; no setup or download is needed to show the demo.

**Show the verified result immediately:** open **Saved runs**, search `20261018-000645-35608fe8`, and choose **Open result ↗** for `india-city.mp4`. Close the result dialog and return to the workspace to use **Play result** and inspect the IVP stages. This 20-second result is already loaded. Clear the library search to see other runs.

**Process footage yourself:** load the Indian city demo or upload a video, choose **Vehicles · local detector + IVP**, then **Track automatically & calculate speed**. No vehicle-by-vehicle selection is required. **Moving texture regions · IVP only** keeps the motion workflow entirely classical. A running job can be reopened from Saved runs, and progress resumes after reload.

Current verification: **251 Python tests**, **4 JavaScript tests**, real Indian-video development checks, and browser playback/download checks. A repeated three-minute workload also completes with exact frame timing. These checks do not establish general crowded-traffic accuracy. Default speed is **px/s**; approximate km/h requires one measured road calibration and real-time footage. Full occlusion, clipped objects and very small vehicles remain difficult.

For a concise evidence map and review inventory, start at [the handoff index](docs/AUTOMATIC_TRACKING.md#handoff-at-a-glance). [INSTALL.md](INSTALL.md) covers another computer or missing prerequisites; [PROGRESS.md](PROGRESS.md) retains the chronological record.

## Open the app

Double-click **Start.cmd**. It opens http://127.0.0.1:8511 in your browser. The server runs in the background on this computer only. Double-click **Stop.cmd** to stop the server and request cancellation of active video jobs.

The isolated `H:\CodexStorage\ivp-ai\venv` uses Python 3.11. The system Python installation is unchanged. Dependencies are pinned in `requirements.txt`; `requirements.in` is the editable dependency specification. FFmpeg and ffprobe must be on PATH for video inspection and export.

To rebuild the environment, run `powershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1`. Setup uses uv and may download Python 3.11 and packages. After setup, normal analysis works offline. PyAV is included alongside OpenCV so variable frame presentation timestamps can be retained during encoding.

## Web studio

The default launcher now opens a dedicated HTML/CSS/JavaScript application backed by a Python localhost API. It needs no Node build step, external fonts, CDN, or extra Python dependencies. The earlier Streamlit interface remains available for classroom examples: run `& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m streamlit run app.py --server.port 8512` if needed.

The studio opens in the **IVP laboratory**, with automatic classical processing and a 22-stage visual walkthrough. **AI workspace** contains the wider experimental analysis. The video panel separately labels its optional local vehicle-detector mode; classical IVP processing itself loads no models. Choose **Manual settings** to reveal presets, sliders, undo/redo and settings import/export. A region inspector and searchable results library remain available. The last successfully previewed source, processing mode, settings and video timestamp are restored after reload, provided the saved source still exists. Exported runs remain immutable snapshots.

## Automatic tracking demo

The video panel offers **Vehicles · local detector + IVP** and **Moving texture regions · IVP only**. Click **Load Indian city demo**, then **Track automatically & calculate speed**; no per-vehicle selection is required. Vehicle mode uses the existing local YOLO11s detector, bottom-centre-aware ByteTrack association and conservative short-gap recovery. The second mode is entirely classical and measures foreground texture regions, which may cover fragments or several vehicles. Both export tracks, speed estimates, IVP stages and a timed video. Speed is px/s until the road is calibrated once with measured dimensions; real-time footage is required for physical speed. See [the current demo instructions, real-video checks and limitations](docs/AUTOMATIC_TRACKING.md).

## Workflow

For optional rule review, expand **Incident review · optional** in the video panel. Configure a stop boundary or zone and its applicable condition; add a speed threshold only when you have confirmed road calibration and real-time footage. Automatic tracks produce review candidates, neutral observations or withheld assessments, with thumbnails and JSONL/CSV exports. A zebra crossing alone is neutral. Synthetic tests are explicitly labelled. See [incident setup, measurement guards and limitations](docs/AUTOMATIC_TRACKING.md#optional-incident-review--18-october-2026).

1. Upload JPG/JPEG/PNG or MP4/MOV/AVI, up to 1 GB. The original is stored under `uploads` and never overwritten.
2. For video, select a preview timestamp. The before/after wipe uses the same decoded frame; its actual timestamp is displayed.
3. Leave Automatic IVP selected for conservative settings based on image statistics. For video, settings come from the first decoded frame and stay fixed. Select Manual settings only when you want to tune filters yourself; its Original preset disables colour enhancement and resizing.
4. Explore IVP stages using the thumbnail cards or Previous/Next. Each stage states its input, operation and parameters. Colour comparison, Processed and Features remain available. Inspector metrics refer to the colour output, not the selected edge/binary stage.
5. Save the image/frame to download all 22 stage PNGs with explanations, settings, timestamp and coordinate mapping in `ivp-stages.zip`. Full-video export produces an enhanced colour MP4 and selected sampled masks; it does not produce 22 separate stage videos.
6. Download the outputs, or retrieve earlier exports from Saved runs.

Saved image exports are snapshots: changes to sliders do not alter an existing export. Save again to create another run. Video jobs capture the settings at the time Process entire video is clicked. Changing the preview afterwards does not change the running job.

## Processing stages

### Classical video movement analysis

Choose a video, select **Moving texture regions · IVP only** and **Four IVP stages together**, then click **Track automatically & calculate speed**. A background worker produces a synchronized four-panel MP4, an activity chart and directional region crossings through the amber line. Set its orientation/position before starting; optionally select a road region. The full video is analysed from frame zero. The marking survey remains a secondary, collapsed experimental tool.

Pipeline: static-context camera registration → Gaussian smoothing → MOG2 adaptive background modelling → shadow-label exclusion → opening/closing → connected components → automatic Shi–Tomasi corner discovery and forward/backward Lucas–Kanade texture tracking → trajectories and line-crossing hysteresis. Registration maps observations into the first frame; unsupported camera motion suppresses measurements. Background warm-up, scene resets and widespread foreground are excluded from foreground statistics. Stationary objects can be absorbed into the background.

Exports include timed H.264 video with source audio when present, activity/crossing/trajectory CSVs, raw foreground, shadow mask, estimated background, clean mask, a peak comparison, source-coordinate mapping and raw per-pixel foreground seconds (`motion-seconds.npy`). The evidence ZIP records parameters and source request. Frame processing is incremental; trajectories are bounded and the display timeline uses at most 600 bins. The existing one-job lock, progress and cancellation apply. Motion analysis always uses original colour with a maximum width of 960; enhancement controls do not affect it.

Crossings refer to moving **regions**, not accuracy-validated vehicle counts. Occlusions, shadows, slow traffic, merged/split regions and camera motion remain limitations. Speed uses px/s unless a measured road-plane calibration is supplied; region contact points may not represent vehicle ground contact. No traffic-rule decision or object class is inferred in this mode. See [current validation](docs/AUTOMATIC_TRACKING.md) and [the earlier motion implementation record](docs/MOTION_VALIDATION.md).

### Independent road-marking survey

Choose **Select road area**, drag over a road patch, then **Measure & save survey**. This is a standalone IVP application: original RGB → HSV white/yellow segmentation with a bounded Otsu brightness threshold → morphological opening/closing → connected components → pixel-area, bounding geometry and principal-axis measurements. No AI model is called. Enhancement settings do not influence the measurements. Analysis width is capped at 1280 with source-coordinate mapping retained; video surveys use the selected frame only.

The result shows candidate coverage, connected fragments, ROI-boundary truncation and threshold sensitivity. The evidence ZIP contains the selected patch, raw/clean masks, masks at ±20 brightness threshold, annotated fragments, CSV and JSON. Saved runs retain the survey. Flat selections with insufficient intensity separation withhold segmentation; include both road and paint. Review the masks: shadows, glare, faded paint and bright objects can cause errors. Coverage is not a paint-wear score, physical road area or vehicle occupancy. Lengths are uncalibrated image pixels; orientation can be ambiguous for nearly symmetric fragments. Threshold stability is not accuracy.

The IVP walkthrough includes original colour, grayscale, smoothing, grayscale CLAHE, Sobel X/Y/magnitude, Canny, Otsu and adaptive thresholds, a selected binary mask, opening, closing, connected components, contours, Hough lines, red/amber/green isolation, white markings, road candidates and an FFT spectrum. Preparation is sequential; edges, segmentation, colour and frequency analysis branch separately. Every card records its actual input. Grayscale CLAHE is demonstrated independently of optional CLAHE on the colour export. HSV masks use original prepared colour. These stages use OpenCV and NumPy, without AI inference.

Automatic choices are deterministic heuristics, not a promise of optimal enhancement. The FFT and derivative views are normalized for display. Connected regions, contours, lines and colour masks are visual features; they do not identify vehicles or establish traffic violations.

The colour pipeline is orientation correction → optional downsize preserving aspect ratio → denoising → optional gray-world white balance → exposure scaling → optional percentile contrast stretch → gamma → optional CLAHE on Lab luminance → optional unsharp mask → saturation adjustment. Denoising choices are Gaussian, median, and bilateral. Gamma above 1 brightens, below 1 darkens. Sharpening strength 0 disables sharpening.

Feature extraction branches from the prepared frames. Grayscale, thresholding, edges, contours, and lines use the processed colour frame. HSV and colour masks use the original resized colour frame so enhancement cannot manufacture a signal colour.

New feature views include normalized Sobel gradient magnitude, absolute Laplacian, morphological gradient, top hat and black hat. The accompanying explanation describes each operation and its limitations. Existing feature views include grayscale, Hue, Saturation, Value, configurable circular hue mask, white marking mask, Canny edges, binary threshold, morphology, contours, Hough lines, road candidates, and stripe mask. Hue display is rescaled to 0–255 for viewing; colour controls use OpenCV's hue scale 0–179. Red wraps around the hue boundary. Otsu, adaptive Gaussian, and fixed thresholding are available. Morphology supports off, open, close, and open followed by close.

## What the measurements mean

- Brightness: mean grayscale intensity, 0–255.
- Contrast: grayscale standard deviation.
- Edge detail / possible blur: variance of a grayscale Laplacian.
- Entropy: Shannon entropy of the 256-bin grayscale histogram, in bits. Texture and noise both influence this value.
- Shadow/highlight fractions: pixels at or below 10 / at or above 245.
- Flags: brightness below 55, brightness above 205 or over 35% highlights, contrast below 28, and Laplacian variance below 70.

These fixed thresholds are heuristic starting points. A plain wall may have low edge detail without being out of focus. Noise and sharpening can increase the blur score. Measurements compare frames at the same prepared resolution. Neither brighter output nor a larger score demonstrates improved AI accuracy.

## Video timing, audio, and resource use

The worker decodes and processes one frame at a time. Original frame presentation intervals are preserved at 1/90000-second output precision, normalising the first video frame to time zero. Video is H.264, YUV420p, CRF 18. Odd dimensions receive one replicated edge pixel on the right/bottom as needed; the padding is recorded. Original preset preserves decoded image pixels before encoding, but MP4 export is lossy.

The first audio track is retained as AAC, preserving its offset relative to the first video frame. Negative pre-roll is trimmed; audio beyond the video endpoint is excluded. Additional audio tracks and subtitles are not exported. Missing or non-monotonic frame timestamps produce an actionable error instead of silently changing playback timing.

Colour settings stay fixed over the video; content-dependent operations such as CLAHE, gray-world correction and percentile stretching can still vary with scene content. Disable these adaptive operations if they introduce visible temporal flicker. Possible scene changes are detected with HSV histogram distance and written to a CSV. This is not camera stabilisation, scene recognition, or a guarantee of finding every cut. Lighting changes can trigger candidates, and similarly coloured scenes can be missed.

Selected video feature views are PNG samples, approximately once per second, packaged in a ZIP. All frames receive colour processing and quality measurements. Frame measurements and scene-change records stream to CSV. Downloads and video playback stream from disk via a tokenised localhost file server with HTTP Range support. The web uploader streams compressed bytes to disk in 1 MB chunks. The 1 GB file limit is separate from decoded-frame memory; high-resolution images still need more RAM. The API keeps one processed-frame cache and serializes expensive interactive operations.

One video worker is permitted at a time using an OS file lock. Cancellation is checked between frames and during final audio muxing. Interrupted workers are marked after a 30-second stale-status window when the OS lock is free. Restart the job from its original upload; partial runs are not presented as completed output. Closing the browser alone leaves a worker running; Stop.cmd requests cancellation.

## Road candidates: limitations

Amber rectangles show sufficiently large, elongated, bright stripe shapes in the lower part of the frame. Blue lines show up to 40 long, near-horizontal segments from the white-marking mask, with nearby overlapping segments suppressed. The separate Lines view exposes general Hough lines.

These are geometric proposals, not labelled zebra crossings or stop lines. White vehicles, kerbs, building detail, shadows, worn paint, occlusion, exposure, and camera angle cause false proposals or missed markings. No traffic light or traffic-rule meaning is inferred. See `docs/VALIDATION.md` for the real-image checks.

## Reusable IVP interface

The **AI** inspector offers object detection and an optional local-language-model scene review. Detection processes the uploaded image or entire video with local models and the current IVP settings. Completed jobs offer annotated media, frame decisions, events, coordinate mappings, and scene-feature exports. Green boxes indicate reported violation events; a missing box does not establish that the scene is violation-free. Read the assessment coverage and cannot-assess reasons in the report.

The separate AI runtime on this computer is `H:\CodexStorage\ivp-ai\venv`; its location is recorded in ignored `ai-runtime.json`. For another installation, run `Setup-AI.ps1 -RuntimeHome <directory-with-enough-space>`. First use downloads model weights. Existing cached models run locally. The custom web studio is now the default interface; the Streamlit demo is retained separately.

Sign recognition currently supports a subset of GTSRB meanings and does not automatically establish which road approach a sign controls. Signal-to-approach association, complete prohibited-turn sign coverage, automatic road-plane calibration, and real-traffic validation remain in progress. See `PROGRESS.md` and `docs/SIGN_VALIDATION.md` for current evidence and limitations.

`ivp.process_frame(rgb, settings, timestamp, include_features=True, include_stages=True)` accepts a uint8 RGB array in display orientation. It returns a `FrameResult` containing the colour frame, optional feature/stage arrays, original display dimensions, timestamp in seconds, quality measurements, and a 3×3 mapping back to source pixel centres.

For an output pixel centre `[x, y, 1]`, multiply by `transform_to_source`. Box-edge coordinates instead use the width and height scale factors without the centre offset. Source coordinates refer to the orientation-corrected image, not raw camera storage orientation. No crop or perspective warp is currently performed. The video report includes the transform and encoding padding.

Models can consume `color_rgb` directly. Feature masks are optional side inputs; do not replace the colour image with an edge mask by default. Call with `include_features=False` and `include_stages=False` when only colour frames and measurements are needed.

## Project files

- `web_server.py` and `web/`: default local API and browser application.
- `app.py`: optional legacy Streamlit interface.
- `ivp/`: pipeline, media adapters, job control, video worker, streaming downloads.
- `tests/`: image invariants, video timing/audio, cancellation, job recovery, app controls, and downloads.
- `uploads/`: preserved source uploads.
- `runs/`: separate export directories with settings, reports, masks, media, and logs.
- `temp/`: server logs and development QA material.
- `output/`: final submission deliverables, including the AI explainer PDF.
- `PLAN.md` and `PROGRESS.md`: project scope and continuation record for this task.

Run tests from this directory with `& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m pytest`. Tests generate their own video fixtures using FFmpeg. They do not need Internet access or AI models.

## Troubleshooting

- App will not start: inspect `temp/server.log`; rerun Setup.ps1 if packages are missing.
- Port 8511 is occupied: stop the other service or the existing Traffic Lab process before retrying.
- FFmpeg missing: install FFmpeg, place both ffmpeg and ffprobe on PATH, and restart the app.
- Unsupported codec or bad timestamps: re-export the source as an H.264 MP4 with valid timing.
- Video job failed: inspect the run's worker.log and ffmpeg.log. Start a new run after resolving the reported problem.
- Very large frames are slow: select a maximum width such as 960 or 1280; bilateral filtering is comparatively expensive.
- Files remain on disk: originals and completed runs are retained deliberately. Manage them through the project folder when no jobs are running.

## Indian traffic and speed

Credited Indian city and Delhi clips are available locally, including a crowded junction and close-passing rickshaws. Start with **Load Indian city demo** and automatic vehicle mode; harder clips are in the sample selector. For a standalone IVP demonstration choose **Moving texture regions · IVP only** and **Four IVP stages together**. That mode uses background subtraction, morphology and corner/optical-flow tracking without a detector or LLM. Manual target selection is optional.

Speed is in pixels/second until you enter measured road-plane calibration. Estimated km/h needs suitable road-contact positions and remains unverified against real vehicle reference speeds. Source clips include missed objects and identity changes under occlusion; the documentation reports those failures. See [current automatic-tracking validation](docs/AUTOMATIC_TRACKING.md) and [earlier standalone-IVP validation](docs/INDIAN_TRAFFIC_VALIDATION.md).
