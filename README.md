# Traffic Lab — IVP and AI

**New installation:** follow the [Windows installation guide](INSTALL.md) for prerequisites, cloning, IVP setup, optional local AI setup, verification and troubleshooting.

The [AI explainer PDF](output/pdf/AI_Traffic_Analyser_Explained.pdf) describes the architecture as of 24 September 2026. See [PROGRESS.md](PROGRESS.md) for subsequent changes.

A local image and video processing application for the combined IVP and AI traffic-camera project. The IVP workflow is implemented; the AI workflow is experimental and under active development. It runs vehicle/person and helmet detection, tracking, scene-feature extraction, and evidence-based rule logic. Full automatic interpretation of all nine traffic-rule categories is not complete or accuracy-validated.

## Open the app

Double-click **Start.cmd**. It opens http://127.0.0.1:8511 in your browser. The server runs in the background on this computer only. Double-click **Stop.cmd** to stop the server and request cancellation of active video jobs.

Overlapping Start actions wait for the current startup and reuse the same server, preserving the server PID used by Stop.cmd.

The isolated `.venv` uses Python 3.11. The system Python installation is unchanged. Dependencies are pinned in `requirements.txt`; `requirements.in` is the editable dependency specification. FFmpeg and ffprobe must be on PATH for video inspection and export.

To rebuild the environment, run `powershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1`. Setup uses uv and may download Python 3.11 and packages. After setup, normal analysis works offline. PyAV is included alongside OpenCV so variable frame presentation timestamps can be retained during encoding.

## Workflow

1. Upload JPG/JPEG/PNG or MP4/MOV/AVI, up to 1 GB. The original is stored under `uploads` and never overwritten.
2. For video, select a preview timestamp. Both comparison panes use the same decoded frame; its actual timestamp is displayed.
3. Pick a preset or adjust the sidebar. Original disables colour enhancement and resizing. Low light uses bilateral denoising, gamma 1.5, and CLAHE. Noisy footage uses median filtering. Road features uses Gaussian filtering and CLAHE.
4. Inspect Before / after, Feature views, Processing stages, and Quality + histograms.
5. Choose feature views to export, then save an image/frame or process the entire video.
6. Download the outputs, or retrieve earlier exports from Saved runs.

Saved image exports are snapshots: changes to sliders do not alter an existing export. Save again to create another run. Video jobs capture the settings at the time Process entire video is clicked. Changing the preview afterwards does not change the running job.

## Processing stages

The colour pipeline is orientation correction → optional downsize preserving aspect ratio → denoising → gamma → optional CLAHE on Lab luminance → optional unsharp mask. Denoising choices are Gaussian, median, and bilateral. Gamma above 1 brightens, below 1 darkens. Sharpening strength 0 disables sharpening.

Video previews and worker frames apply quarter-turn display rotations and horizontal/vertical reflections before processing, so mirrored camera metadata is preserved in the displayed orientation and exported pixels.

Unsigned 16-bit grayscale PNGs are scaled from 0–65535 to 0–255 with rounding before RGB processing. Transparent samples use the same white background as other images.

Feature extraction branches from the prepared frames. Grayscale, thresholding, edges, contours, and lines use the processed colour frame. HSV and colour masks use the original resized colour frame so enhancement cannot manufacture a signal colour.

Feature views include grayscale, Hue, Saturation, Value, configurable circular hue mask, white marking mask, Canny edges, binary threshold, morphology, contours, Hough lines, road candidates, and stripe mask. Hue display is rescaled to 0–255 for viewing; colour controls use OpenCV's hue scale 0–179. Red wraps around the hue boundary. Otsu, adaptive Gaussian, and fixed thresholding are available. Morphology supports off, open, close, and open followed by close.

## What the measurements mean

- Brightness: mean grayscale intensity, 0–255.
- Contrast: grayscale standard deviation.
- Edge detail / possible blur: variance of a grayscale Laplacian.
- Shadow/highlight fractions: pixels at or below 10 / at or above 245.
- Flags: brightness below 55, brightness above 205 or over 35% highlights, contrast below 28, and Laplacian variance below 70.

These fixed thresholds are heuristic starting points. A plain wall may have low edge detail without being out of focus. Noise and sharpening can increase the blur score. Measurements compare frames at the same prepared resolution. Neither brighter output nor a larger score demonstrates improved AI accuracy.

## Video timing, audio, and resource use

The worker decodes and processes one frame at a time. Original frame presentation intervals are preserved at 1/90000-second output precision, normalising the first video frame to time zero. Video is H.264, YUV420p, CRF 18. Odd dimensions receive one replicated edge pixel on the right/bottom as needed; the padding is recorded. Original preset preserves decoded image pixels before encoding, but MP4 export is lossy.

The first audio track is retained as AAC, preserving its offset relative to the first video frame. Negative pre-roll is trimmed; audio beyond the video endpoint is excluded. Additional audio tracks and subtitles are not exported. Missing or non-monotonic frame timestamps produce an actionable error instead of silently changing playback timing.

Colour settings stay fixed over the video; content-dependent operations such as CLAHE can still vary with scene content. Possible scene changes are detected with HSV histogram distance and written to a CSV. This is not camera stabilisation, scene recognition, or a guarantee of finding every cut. Lighting changes can trigger candidates, and similarly coloured scenes can be missed.

Selected video feature views are PNG samples, approximately once per second, packaged in a ZIP. All frames receive colour processing and quality measurements. Frame measurements and scene-change records stream to CSV. Downloads and video playback stream from disk via a tokenised localhost file server with HTTP Range support. The Streamlit uploader buffers the compressed upload, so the 1 GB upload limit is distinct from the worker's bounded frame memory. Preview caches are capped.

One video worker is permitted at a time using an OS file lock. Cancellation is checked between frames, during final audio muxing, between AI archive entries and before publishing completed results. Interrupted workers are marked after a 30-second stale-status window when the OS lock is free. Restart the job from its original upload; partial runs are not presented as completed output. Closing the browser alone leaves a worker running; Stop.cmd requests cancellation.

## Road candidates: limitations

Amber rectangles show sufficiently large, elongated, bright stripe shapes in the lower part of the frame. Blue lines show up to 40 long, near-horizontal segments from the white-marking mask, with nearby overlapping segments suppressed. The separate Lines view exposes general Hough lines.

These are geometric proposals, not labelled zebra crossings or stop lines. White vehicles, kerbs, building detail, shadows, worn paint, occlusion, exposure, and camera angle cause false proposals or missed markings. No traffic light or traffic-rule meaning is inferred. See `docs/VALIDATION.md` for the real-image checks.

## Reusable IVP interface

The **AI analysis** tab processes the uploaded image or entire video with local models and the current IVP settings. Completed jobs offer annotated media, frame decisions, events, coordinate mappings, and scene-feature exports. Green boxes indicate reported violation events; a missing box does not establish that the scene is violation-free. Read the assessment coverage and cannot-assess reasons in the report.

The separate AI runtime on this computer is `H:\CodexStorage\ivp-ai\venv`; its location is recorded in ignored `ai-runtime.json`. For another installation, run `Setup-AI.ps1 -RuntimeHome <directory-with-enough-space>`. First use downloads model weights. Existing cached models run locally. The visual redesign remains deferred.

Sign recognition currently supports a subset of GTSRB meanings and does not automatically establish which road approach a sign controls. Signal-to-approach association, complete prohibited-turn sign coverage, automatic road-plane calibration, and real-traffic validation remain in progress. See `PROGRESS.md` and `docs/SIGN_VALIDATION.md` for current evidence and limitations.

`ivp.process_frame(rgb, settings, timestamp, include_features=True, include_stages=True)` accepts a uint8 RGB array in display orientation. It returns a `FrameResult` containing the colour frame, optional feature/stage arrays, original display dimensions, timestamp in seconds, quality measurements, and a 3×3 mapping back to source pixel centres.

For an output pixel centre `[x, y, 1]`, multiply by `transform_to_source`. Box-edge coordinates instead use the width and height scale factors without the centre offset. Source coordinates refer to the orientation-corrected image, not raw camera storage orientation. No crop or perspective warp is currently performed. The video report includes the transform and encoding padding.

Models can consume `color_rgb` directly. Feature masks are optional side inputs; do not replace the colour image with an edge mask by default. Call with `include_features=False` and `include_stages=False` when only colour frames and measurements are needed.

## Project files

- `app.py`: Streamlit interface.
- `ivp/`: pipeline, media adapters, job control, video worker, streaming downloads.
- `tests/`: image invariants, video timing/audio, cancellation, job recovery, app controls, and downloads.
- `uploads/`: preserved source uploads.
- `runs/`: separate export directories with settings, reports, masks, media, and logs.
- `temp/`: server logs and development QA material.
- `output/`: final submission deliverables, including the AI explainer PDF.
- `PLAN.md` and `PROGRESS.md`: project scope and continuation record for this task.

Run tests from this directory with `.venv\Scripts\python.exe -m pytest`. Tests generate their own video fixtures using FFmpeg. They do not need Internet access or AI models.

## Troubleshooting

- App will not start: inspect `temp/server.log`; rerun Setup.ps1 if packages are missing.
- Port 8511 is occupied: stop the other service or the existing Traffic Lab process before retrying.
- FFmpeg missing: install FFmpeg, place both ffmpeg and ffprobe on PATH, and restart the app.
- Unsupported codec or bad timestamps: re-export the source as an H.264 MP4 with valid timing.
- Video job failed: inspect the run's worker.log and ffmpeg.log. Start a new run after resolving the reported problem.
- Very large frames are slow: select a maximum width such as 960 or 1280; bilateral filtering is comparatively expensive.
- Files remain on disk: originals and completed runs are retained deliberately. Manage them through the project folder when no jobs are running.
