# Installation guide (Windows)

Traffic Lab runs in your browser at **http://127.0.0.1:8511**, with processing on your own computer. The supported launchers target Windows. IVP works without the AI runtime; live AI requires the separate setup below. Bundled IVP samples work without AI models. Saved classroom examples are retained in the optional legacy Streamlit demo.

## 1. Prerequisites

The default workspace is now the IVP laboratory: automatic processing, 22 inspectable stages and stage downloads. Manual filters are available through **How to process → Manual settings**. The separate AI workspace is optional; no AI installation is needed for the IVP walkthrough.

Install these tools and reopen PowerShell so PATH changes take effect:

- [Git for Windows](https://git-scm.com/downloads/win).
- [uv](https://docs.astral.sh/uv/getting-started/installation/), the Python environment/package manager. The setup script lets uv obtain Python 3.11; it does not replace your system Python.
- [FFmpeg](https://ffmpeg.org/download.html): keep the Windows build on H: and add its `bin` folder to PATH. Both `ffmpeg.exe` and `ffprobe.exe` are needed for videos and video tests.
- For accelerated AI, an NVIDIA GPU and an up-to-date NVIDIA driver supporting the pinned CUDA 12.8 PyTorch build. CPU inference is supported by the application but can be substantially slower. The supplied AI installer uses CUDA-enabled packages, even when inference falls back to CPU.

Check the tools:

```powershell
git --version
uv --version
ffmpeg -version
ffprobe -version
```

Allow several GB for Python environments and downloaded models, plus space for your uploads and generated videos. The development machine uses an RTX 4050 with 6 GB VRAM; this is tested hardware, not a guaranteed minimum. Put the AI runtime on a drive with ample free space.

## 2. Clone the private repository

Your GitHub account must have access. Authenticate using Git Credential Manager when prompted, or use `gh auth login` if you have GitHub CLI installed.

```powershell
git clone https://github.com/hrishike-sh/ivp-and-ai.git
Set-Location ivp-and-ai
```

Run the remaining commands from this folder.

## 3. Install the IVP app

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
```

This creates `H:\CodexStorage\ivp-ai\venv` using Python 3.11 and installs the pinned packages in `requirements.txt`. uv caches and downloaded Python builds also stay under that H-drive folder. Activation is unnecessary. To use a different drive on another computer, pass the same `-RuntimeRoot` folder to both `Setup.ps1` and `Start.ps1`. The current development runtime is already installed; no new installation was needed for motion or speed analysis.

Start the app:

```powershell
.\Start.cmd
```

The launcher opens your browser. If it does not, visit http://127.0.0.1:8511 manually. Use `Stop.cmd` to stop the server and request cancellation of active processing jobs. Closing the browser alone does not stop processing.

## 4. Install local AI (optional for IVP, required for live AI)

Existing installations reuse the location saved in `ai-runtime.json`. A fresh AI setup defaults to `H:\CodexStorage\ivp-ai\ai-runtime`, separate from the base IVP environment:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-AI.ps1
```

Or select another drive, replacing the example with a location on your machine:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-AI.ps1 -RuntimeHome 'H:\TrafficLabAI'
```

The installer creates `<RuntimeHome>\venv`, keeps uv caches and downloaded Python builds below that runtime folder, installs pinned PyTorch/CUDA and AI dependencies, and saves the absolute runtime location in local `ai-runtime.json`. An unavailable runtime drive produces an error; there is no fallback to C:. Keep the IVP and AI environments separate: they use different OpenCV distributions. Do not install both requirements files into one environment.

Check the AI installation:

```powershell
$trafficRuntime = (Get-Content .\ai-runtime.json -Raw | ConvertFrom-Json).home
$trafficPython = Join-Path $trafficRuntime 'venv\Scripts\python.exe'
& $trafficPython -c "import torch, ultralytics, transformers; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

Models download on first use and are cached under the chosen runtime folder. This can take several minutes and needs Internet access. Later analyses use available cached models locally. The application does not send footage to a hosted inference API. If you move the runtime, rerun Setup-AI.ps1 with its new path.

## 5. Try an image and a video

1. Open the **IVP laboratory** and upload an image, or choose an available sample.
2. Leave **Automatic IVP** selected. Inspect **IVP stages**, using Previous/Next to follow grayscale, smoothing, contrast, edges, thresholds and morphology. **Manual settings** exposes optional controls.
3. Upload a video to preview timestamps and export enhanced colour video. The bundled four-second still-image/audio clip checks export and audio; it does not demonstrate real traffic movement.
4. For motion, use **Automatic tracking & speed**. Select **Moving texture regions · IVP only** for classical analysis. **Vehicles · local detector + IVP** needs the optional detector setup described below.
5. The separate **AI workspace** supports the experimental image/violation workflow. Inspect its detections and reasons; missing boxes do not establish compliance.

Cyan boxes indicate object detections. Green boxes indicate experimental reported violations. Missing boxes do not prove compliance. Several rules need video, stable geometry and a reliably associated signal/sign. Full automatic validation of all nine rule categories is unfinished.

The Classroom demo includes prepared examples. Two locally supplied Indian photos are excluded from Git; upload your own images to try those conditions. Missing optional samples are hidden automatically. `prepare_demo.py` is a development reconstruction script requiring local QA files and historical runs; it is not an installation step.

## 6. Verify the code

With FFmpeg/ffprobe available:

```powershell
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m pytest -q
```

Tests use synthetic fixtures and recorded detection data; they do not download neural-network weights. For a real model smoke test after AI setup:

```powershell
$trafficRuntime = (Get-Content .\ai-runtime.json -Raw | ConvertFrom-Json).home
$trafficPython = Join-Path $trafficRuntime 'venv\Scripts\python.exe'
& $trafficPython -m traffic_ai.smoke .\demo\street.jpg --output .\temp\qa\perception.json
```

A passing smoke test verifies model inference, not traffic-violation accuracy. Validation notes in `docs` describe what was actually tested; some reference local runs and QA images intentionally excluded from Git.

## Files and updates

- `uploads/`: original inputs; preserved locally.
- `runs/`: settings, processed media, evidence and reports for each job.
- `temp/`: logs and local QA material.
- `demo/`: prepared classroom samples and saved illustrative outputs.
- `output/pdf/`: the AI explanation document.
- `.venv/`, `.ai-runtime/`, model weights and `ai-runtime.json`: local dependencies/configuration, excluded from Git.

Stop the app before updating. Run `git pull`, then rerun Setup.ps1 and, if AI dependencies changed, Setup-AI.ps1. Preserve your local uploads and runs. Never commit credentials or Streamlit secrets.

## Troubleshooting

| Problem | What to do |
|---|---|
| `uv` is not recognised | Install uv and open a new PowerShell window. |
| Script execution is disabled | Use the documented `powershell -NoProfile -ExecutionPolicy Bypass -File ...` command; no machine-wide policy change is required. |
| FFmpeg/ffprobe missing | Add the FFmpeg build's `bin` directory to PATH, reopen PowerShell and restart the app. |
| Port 8511 is occupied | Use Stop.cmd for this app, or stop the other application using that port. |
| AI runtime missing | Complete Setup-AI.ps1 and check that ai-runtime.json points to the installed environment. |
| CUDA unavailable | Update the NVIDIA driver, verify the GPU is supported and rerun the check above. CPU inference remains slower. |
| First AI run is slow | Allow model downloads to finish. Subsequent cached runs avoid those downloads. |
| Model download fails | Check Internet access and free space, then retry. See the run's worker.log for the specific failure. |
| Unsupported/corrupt video | Re-export a valid H.264 MP4 and retry. The original upload is not overwritten. |
| App/processing fails | Check temp/server.log or runs/<run>/worker.log. Resolve the error and start a new job. |

## Optional local vision-language model (H: installation)

For experimental scene descriptions and visible-sign interpretation, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Ollama.ps1
```

The script first checks the H-drive Python environment created by Setup.ps1 (pass the same `-RuntimeRoot` if customized), then installs a pinned portable Ollama runtime and downloads `qwen3-vl:4b`. The machine must have an H: drive: runtime, model weights, downloads, profile, application data, temporary files, CUDA cache and review JSON files are placed under `H:\CodexStorage\ivp-ai\ollama`. No system-wide PATH or environment-variable changes are made. The server binds to `127.0.0.1:11435`, disables cloud features and unloads the model after a review. The initial downloads are several GB; allow them to finish before using the feature.

`-RuntimeRoot` selects the Python environment used by this setup script. Ollama's portable runtime, model weights and other state intentionally stay at `H:\CodexStorage\ivp-ai\ollama`, matching `traffic_ai/ollama_runtime.py` and `Stop-Ollama.ps1`. This separate model root is fixed by the current implementation.

Open **Workspace > AI analysis > Local vision scene review**, then click **Review this frame with local vision**. It reviews the original image (or currently selected video frame) at up to 1280 pixels per side. The model gives a short scene description, with a downloadable JSON record containing the description, model digest, image hash, frame timestamp and limitations. Descriptions are generated by a language model and can be wrong; they do not independently create violation events, calibration transforms or green boxes. This is an additional experimental capability, not completion of all traffic-rule interpretation.

Only one model request runs at a time, and the app's processing lock prevents starting a review alongside a video worker. On a 6 GB GPU, loading or CPU offload can be slow. A review has a four-minute HTTP timeout; if it fails, check `H:\CodexStorage\ivp-ai\ollama\server.log`. Use the command below to stop this project's server:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Ollama.ps1
```

The review button restarts the installed server when needed. The regular Stop.cmd controls the Traffic Lab web server, not this separate Ollama server. Use Stop-Ollama.ps1 too if you want both stopped. Model weights remain local and are excluded from Git by their H: location.


## Dedicated web studio (9 October 2026)

`Start.cmd` now starts `web_server.py`, serving the custom browser application from `web/` at the same localhost address. Reload any already-open Streamlit tab after upgrading. No npm install or new package is required. Stop the previous instance with `Stop.cmd` before restarting after backend updates.

Use the source selector or **Open footage**, pick a preset, and compare the image with the before/after divider. **Features** contains the IVP masks and gradient views; **Stages** shows the pipeline. **Select region** lets you draw an inspection rectangle. Quality, Region and AI live in the inspector. In narrow browser panels, the **Adjustments** and **Inspector** buttons jump to those sections.

**Export image/frame** saves a PNG, chosen feature masks and a settings/measurements report. **Process full video** starts the existing incremental worker. **Saved runs** reopens completed outputs, shows AI assessment coverage and lets you reuse settings. Source images and settings can resume after a refresh; if the original was moved or removed, upload it again. Local AI setup remains optional and unchanged.

To open the earlier classroom demo separately:

```powershell
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m streamlit run app.py --server.address 127.0.0.1 --server.port 8512
```

The dedicated API binds only to loopback, checks the Host and Origin on requests, and requires a page-session token for mutations. It is intended for local use, not internet hosting.

## Automatic tracking demo

After launching, click **Load Indian city demo** and **Track automatically & calculate speed**. Local sample files are intentionally excluded from Git; source URLs and hashes are in `demo/motion-sources.json`. A fresh base-only setup uses **Moving texture regions · IVP only**. **Vehicles · local detector + IVP** requires the optional AI runtime and `yolo11s.pt` in that runtime's `models` folder. Setup-AI.ps1 installs dependencies; it does not download this tracking checkpoint. No LLM is used for tracking. See `docs/AUTOMATIC_TRACKING.md` for calibration, outputs and reproducible validation.

For a fresh vehicle-tracking installation, run this explicitly after Setup-AI.ps1 from the project folder. It requests the checkpoint through the installed Ultralytics package and saves it under the configured runtime, rather than the project directory. This development machine already has the checkpoint; no download was performed during the reliability checks.

```powershell
$trafficRuntime = (Get-Content .\ai-runtime.json -Raw | ConvertFrom-Json).home
$trafficPython = Join-Path $trafficRuntime 'venv\Scripts\python.exe'
& $trafficPython -c "from traffic_ai.runtime import configure_cache; home = configure_cache(); (home / 'models').mkdir(exist_ok=True); from ultralytics import YOLO; YOLO(str(home / 'models' / 'yolo11s.pt'))"
```

The pretrained detector has no auto-rickshaw class; the tracker reports generic vehicle candidates. Source-video speed is px/s until a measured road patch supplies physical calibration. Fresh-install scripts received syntax and missing-prerequisite checks in this pass; a clean machine installation and model download were not rerun.
