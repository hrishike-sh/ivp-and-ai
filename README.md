# IVP Lab · Semester 5

A local web application for **classical image and video processing**. Upload your footage, inspect intermediate stages, measure moving regions and export the results. OpenCV and NumPy do the processing; no trained model, GPU, account or cloud service is required.

## Workspaces

| Workspace | Operations | Outputs |
|---|---|---|
| **Image laboratory** | Orientation, resize, denoising, gamma, CLAHE, sharpening; grayscale, Sobel/Canny, thresholding, morphology, connected components, contours, Hough lines, HSV masks and FFT inspection | Before/after comparison, histograms, 28 stages, PNG, masks and measurements |
| **Motion & speed** | MOG2 foreground, shadow rejection, morphology, Shi–Tomasi features, Lucas–Kanade flow, camera registration and region association | Annotated MP4, tracks, region crossings, heatmap, activity and speed samples |
| **Road markings** | Original-colour seeds, local contrast, elongated components and darker-flank support | Candidate coverage, fragments, sensitivity masks and CSV/JSON |
| **Saved runs** | Search and reopen your actual processing work | Media playback, downloads and full settings records |

The initial workspace is empty: **no bundled demo videos, prefilled results, model weights or sample statistics**. Tests generate temporary fixtures; those are never displayed as application results.

## Install on Windows

Requirements: Windows 10/11, Git, [uv](https://docs.astral.sh/uv/getting-started/installation/) and [FFmpeg](https://ffmpeg.org/download.html). Add the directory containing **both ffmpeg.exe and ffprobe.exe** to PATH for video support.

```powershell
git clone https://github.com/hrishike-sh/ivp-sem5.git
cd ivp-sem5
powershell -ExecutionPolicy Bypass -File .\Setup.ps1
.\Start.cmd
```

Open **http://127.0.0.1:8511/**. Start.cmd opens the browser and reuses a healthy existing instance. Stop.cmd stops this project's server and requests cancellation of its workers. Closing the browser alone does not stop a job.

Python 3.11, the environment, package cache and installation temporary files default to **H:\CodexStorage\ivp-sem5-runtime**. System Python is unchanged. Choose a different drive with:

```powershell
powershell -ExecutionPolicy Bypass -File .\Setup.ps1 -RuntimeRoot 'D:\IVP-Runtime'
```

Setup records the path in ignored runtime.json and reuses an existing Python 3.11 environment. Stop the app before changing installed dependencies. Keep the checkout on the drive where you want uploads/results stored. Processing needs no network access after installation.

### macOS / Linux

Install Python 3.11 and FFmpeg, then:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python launch.py
```

The core is cross-platform; the click-to-start scripts target Windows. This release is verified on Windows; other platforms need their own native smoke test.

## Workflow

1. **Open footage.** JPG, JPEG, PNG, MP4, MOV and AVI are accepted, up to 1 GB compressed. Codec support depends on FFmpeg. The accepted upload is preserved as an original copy.
2. **Inspect the image.** Automatic IVP chooses conservative settings from image statistics. Select Manual settings for individual controls, then Update preview. A video uses fixed settings selected from its first frame.
3. **Explore stages.** Select a branch and operation. Each stage explains its input. Feature branches remain separate from the colour export. Select optional masks before saving a frame or processing a video.
4. **Track motion.** Select a road region, put the counting line inside it and choose tracks or four motion stages. Start one job; progress and cancellation stay visible across workspaces.
5. **Survey markings.** Draw a road patch. Inspect candidate coverage, fragments and sensitivity masks together.
6. **Save and revisit.** Each export has its own run folder. Saved runs exposes outputs and settings. Failed/cancelled jobs do not expose completed-media download links.

**Preview position** means seconds into the video, not time of day. Still images have no motion history and cannot supply speed.

## Meaning and limitations

- Brightness is mean grayscale intensity (0–255); contrast is grayscale standard deviation.
- Edge detail is Laplacian variance. Noise, texture and sharpening affect it; it is not an absolute focus score.
- Region tracks follow foreground texture. Vehicles can split into multiple tracks and touching objects can merge. These are not verified vehicle counts or classes.
- **Speed defaults to px/s.** For estimated km/h, mark four corners of a flat road rectangle on the first frame, supply measured dimensions and confirm real-time playback. The first marked edge is width; the adjacent edge is length. Unsupported observations and points outside the patch are withheld.
- Calibration does not establish real-road accuracy. Occlusion, perspective, parallax, slope and shifting region boundaries can bias speed. This is not an enforcement instrument.
- Marking coverage is supported bright-band pixels divided by selected-patch pixels. Roofs, glare and pavement can pass; faint paint can be missed. Appearance does not define crossings, stop lines or violations.

Relevant course topics appear below each workspace. Optical flow, homography and the measurement workflow are project extensions, not implementations of every algorithm in the syllabus.

## Processing and exports

Colour processing follows orientation → resize → denoising → brightness/colour adjustments → optional sharpening. Original colour feeds HSV and marking analysis so enhancement cannot manufacture source colour evidence.

Video processing is incremental. Actual presentation timestamps preserve playback intervals, with the first frame normalized to zero. H.264/YUV420p export is lossy; odd dimensions receive documented edge padding. The first audio stream is retained as AAC with its offset. Additional audio streams and subtitles are not exported.

One worker owns the processing lock. Cancellation is checked during processing and finalization. OpenCV uses available logical CPU processors as its thread budget; this does not guarantee full utilization. Temporal tracking is sequential. This build does not use CUDA.

Source-revision checks reject stale cached footage and changed inputs before publishing complete output. Revisions use path, size and modification time; they are not continuous cryptographic authenticity guarantees.

Exports vary by operation: processed.png / processed.mp4, report.json, coordinates.json, ivp-stages.zip, masks.zip, measurements.csv, motion-tracks.csv, motion-activity.csv and survey-evidence.zip. Missing speed means unavailable, not zero. Accepted and withheld observations remain distinct.

## Files

```text
web/                 Browser UI; no frontend build step
web_server.py        Local API, source binding, previews and exports
ivp/                 Processing, media, tracking and worker modules
tests/               Offline numerical, media, API and UI regressions
launch.py            Single-instance launcher
Setup.ps1            Isolated Python environment setup
uploads/             Original uploaded copies (Git-ignored)
runs/                Separate outputs and reports (Git-ignored)
temp/                Server state, previews and logs (Git-ignored)
```

The old AI modules, model installers, Streamlit interface, demo archives and historical development reports are excluded. Do not commit footage, generated runs, credentials or runtime configuration.

## Development

```powershell
powershell -ExecutionPolicy Bypass -File .\Setup.ps1 -Dev
& 'H:\CodexStorage\ivp-sem5-runtime\venv\Scripts\python.exe' -m pytest
# Optional frontend checks, Node.js 18+
node --test tests/web_app.test.cjs
```

Tests cover disabled-enhancement identity, colour/alpha handling, geometry, marking protections, tracking, speed withholding, source changes, upload boundaries, cancellation, audio/timestamps and worker recovery. Fixtures establish implementation behavior, not Indian-traffic or physical speed accuracy.

The reusable entry point is `ivp.process_frame(rgb, settings, timestamp, include_features=True, include_stages=True)`. It accepts display-oriented uint8 RGB and returns colour pixels, features, measurements, timestamp and a 3×3 transform to source pixel centres. Temporal analysis lives in `ivp.motion.MotionAnalyzer`; `ivp.worker` handles timed video export.

## Troubleshooting

| Problem | Action |
|---|---|
| App does not start | Read temp/server.log; rerun setup if dependencies are missing. |
| Port 8511 occupied | Stop the previous instance rather than starting duplicate servers. |
| FFmpeg missing | Add its bin folder to PATH and restart. |
| Source changed | Reopen the original and reselect regions/calibration. |
| Codec / timing error | Re-export the input with valid timestamps and a supported codec. |
| Unstable tracking | Use a near-fixed camera, texture and a suitable road region. Occlusion or large camera motion can withhold results. |
| Slow processing | Reduce maximum width. Bilateral filtering and large images are expensive; threads cannot remove sequential dependencies. |
| Disk fills up | Stop workers, then remove unneeded runs/temp files. Retain originals and evidence you need. |

## Team

Hrishikesh Salokhe (N088), Devraj Murari (N066), Sinan Mutalik (N067), Rohit Patil (N078).

Semester 5 Image and Video Processing project, MPSTME, SVKM's NMIMS, Mumbai.
