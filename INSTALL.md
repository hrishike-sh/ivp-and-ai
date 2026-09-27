# Installation guide (Windows)

Traffic Lab runs in your browser at **http://127.0.0.1:8511**, with processing on your own computer. The supported launchers target Windows. IVP works without the AI runtime; live AI requires the separate setup below. Saved classroom examples can be viewed without downloading AI models.

## 1. Prerequisites

Install these tools and reopen PowerShell so PATH changes take effect:

- [Git for Windows](https://git-scm.com/downloads/win).
- [uv](https://docs.astral.sh/uv/getting-started/installation/), the Python environment/package manager. The setup script lets uv obtain Python 3.11; it does not replace your system Python.
- [FFmpeg](https://ffmpeg.org/download.html): install a Windows build and add its `bin` folder to PATH. Both `ffmpeg.exe` and `ffprobe.exe` are needed for videos and video tests.
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

This creates `.venv` using Python 3.11 and installs the pinned packages in `requirements.txt`. Activation is unnecessary.

Start the app:

```powershell
.\Start.cmd
```

The launcher opens your browser. If it does not, visit http://127.0.0.1:8511 manually. Use `Stop.cmd` to stop the server and request cancellation of active processing jobs. Closing the browser alone does not stop processing.

## 4. Install local AI (optional for IVP, required for live AI)

Default location, inside the project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-AI.ps1
```

Or select another drive, replacing the example with a location on your machine:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-AI.ps1 -RuntimeHome 'D:\TrafficLabAI'
```

The installer creates `<RuntimeHome>\venv`, installs pinned PyTorch/CUDA and AI dependencies, and saves the absolute runtime location in local `ai-runtime.json`. Keep the IVP and AI environments separate: they use different OpenCV distributions. Do not install both requirements files into one environment.

Check the AI installation:

```powershell
$trafficRuntime = (Get-Content .\ai-runtime.json -Raw | ConvertFrom-Json).home
$trafficPython = Join-Path $trafficRuntime 'venv\Scripts\python.exe'
& $trafficPython -c "import torch, ultralytics, transformers; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

Models download on first use and are cached under the chosen runtime folder. This can take several minutes and needs Internet access. Later analyses use available cached models locally. The application does not send footage to a hosted inference API. If you move the runtime, rerun Setup-AI.ps1 with its new path.

## 5. Try an image and a video

1. Open **Workspace** and select **Original street**, or upload a JPG/PNG.
2. Choose **Original** to inspect unchanged colour processing, then compare **Low light** and **Noisy footage** presets on their corresponding samples.
3. For live AI, open **AI analysis** and choose **Analyse image with AI**. Wait for the background job to complete.
4. Inspect detected objects, reported violations, assessment reasons and scene observations. Download the annotated result and JSON report.
5. Use the bundled four-second video to check processing/export. It repeats a photograph and contains test audio; it is not evidence of real driving behaviour.

Cyan boxes indicate object detections. Green boxes indicate experimental reported violations. Missing boxes do not prove compliance. Several rules need video, stable geometry and a reliably associated signal/sign. Full automatic validation of all nine rule categories is unfinished.

The Classroom demo includes prepared examples. Two locally supplied Indian photos are excluded from Git; upload your own images to try those conditions. Missing optional samples are hidden automatically. `prepare_demo.py` is a development reconstruction script requiring local QA files and historical runs; it is not an installation step.

## 6. Verify the code

With FFmpeg/ffprobe available:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
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
