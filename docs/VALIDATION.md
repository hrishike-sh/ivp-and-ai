# IVP validation record

## Automated checks

The suite covers original-pixel preservation, independent output arrays, aspect-ratio resizing and pixel-centre mapping, gamma behaviour, original-colour masks, red hue wraparound, three denoising filters, three threshold methods, synthetic stripe geometry, grayscale/RGBA/EXIF input, quality flags, scene-change signatures, invalid settings/media, Streamlit preset controls, and ranged streaming downloads.

FFmpeg-generated video fixtures exercise H.264 output, preserved audio, presentation timestamps, variable frame rates, final-frame duration, sampled mask ZIPs, original-file integrity, timestamp seeking, cancellation before and during processing, missing FFmpeg, display rotation, odd-dimension padding, delayed audio, nonzero video start time, and failed jobs. Job checks cover an exclusive lock across processes and stale-worker recovery.

Fixtures are generated test patterns and sine waves, not represented as real traffic footage. Real traffic-image checks are recorded separately below. Execute `.venv\Scripts\python.exe -m pytest` from the project root. The latest run summary is in PROGRESS.md.

## Browser checks

Verified through the local browser UI:

- Empty workspace and processing controls render.
- A real street JPG uploads, shows its dimensions, and displays original/processed frames.
- Low light changes the gamma and CLAHE controls and updates the preview.
- Image save creates a processed PNG, selected-mask ZIP, and JSON report with working local download links.
- Quality metrics and luminance histograms render; feature views show candidate overlays and their limitations.
- A five-second 640×360, 24 fps test video with audio uploads and supports timestamp-based preview.
- Process entire video completes in a separate worker and exposes all download links.
- The browser video element loads the processed MP4 with duration 5 seconds, readyState 4, and no media error.

## Real-image examination

Source material is retained in `temp/qa` for development verification, not as final submission material.

| Source | Processing used | Final candidate counts | Observation |
|---|---|---|---|
| Ultralytics bus street image | Maximum width 960; CLAHE 2.0 | 6 stripe-shaped regions; 5 horizontal segments | Some vehicle/kerb/pavement features are still proposed. This is an appearance extractor, not a crossing classifier. |
| Zebra crossing in Kanhangad | Maximum width 960; CLAHE 2.0 | 3 stripe-shaped regions; 14 horizontal segments | Visible crossing boundaries produce candidates, but shadows and pedestrians fragment the markings and some complete stripes are missed. |

The first implementation produced excessive lines from general scene texture. The final road overlay uses white-mask edges, minimum segment length, overlap suppression, a lower-frame prior, a maximum of 40 segments, and size/fill filters for stripe rectangles. The separate general Lines view remains available for IVP inspection.

Candidate counts are descriptive outputs, not accuracy scores. Two images do not establish generalisation. There is no trained road model, ground-truth evaluation set, or AI accuracy comparison in this phase.

### Source attribution

- Bus street image: [Ultralytics repository asset](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/assets/bus.jpg). Retained as an upstream test asset; not bundled as a product graphic.
- Zebra crossing line kanhangad 01.jpg: [Vijayanrajapuram, Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Zebra_crossing_line_kanhangad_01.jpg), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Development derivatives apply orientation correction, resizing, contrast enhancement, and candidate overlays. If those derivatives are redistributed, retain this attribution and the same licence.

The app's test images and outputs are not evidence of detected traffic violations.
