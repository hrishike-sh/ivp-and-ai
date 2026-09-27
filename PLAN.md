# IVP + AI traffic analyser — accepted direction

This task is the single project conversation. Keep decisions and progress here in the project as implementation evolves.

## Overall project

The eventual local web application accepts traffic images/videos, understands the scene, detects and tracks road users, evaluates traffic rules, and draws green boxes around detected rule breakers. The intended broad checks include helmet absence, triple riding, red-light crossing, stop-line encroachment, zebra-crossing obstruction during red, wrong-way movement, footpath riding, restricted entry, and prohibited turns. Input should require no manual road-zone drawing. Pretrained models come first, with targeted fine-tuning if needed. Missing context must be reported as cannot assess.

## Completed foundation: IVP

Build a local Streamlit application for upload and preview, orientation and aspect-ratio handling, brightness/contrast/blur indicators, gamma, luminance CLAHE, Gaussian/median/bilateral denoising, optional unsharp masking, grayscale/HSV views, colour masks, thresholds, morphology, edges, contours, lines, and experimental road-marking candidates.

Provide before/after comparisons, stage views, histograms, presets, timestamped video previews, incremental background video processing, progress, cancellation, scene-change candidates, saved runs, processed image/video downloads, mask exports, and JSON settings/results. Preserve original uploads, presentation timing, and source audio. Separate reusable IVP functions from the interface and leave AI integration types ready.

The selected stack is Python 3.11, Streamlit, OpenCV, NumPy, Pillow, and FFmpeg, with PyAV added to retain video presentation timestamps. Use a project virtual environment and Windows launchers. Keep the app on localhost. Working results belong in runs; output is for final submission deliverables.

## Implementation sequence

1. Isolated environment, upload, metadata, orientation, and image preview.
2. Colour processing and feature extraction.
3. Controls, comparisons, stage views, and image export.
4. Video worker, timing/audio, progress, cancellation, and exports.
5. Launcher, failure handling, automated checks, browser verification, and documentation.

## Acceptance

Verify unchanged decoded RGB with all enhancement disabled; colour conventions and coordinate mappings; grayscale/RGBA/EXIF inputs; dark/noisy footage; fixed and variable frame timing; audio and rotations; cancellation and interrupted workers; invalid media; and successful reopened exports. Evaluate road candidates on real scenes, document their limitations, and make no claims of improved AI accuracy until models are tested.

## Authorised AI phase

Implement every rule in the overall project scope using local pretrained perception, tracking, and automatic scene understanding. Require no manual road-zone drawing. Preserve source coordinates, timestamps, audio, cancellation, originals, and separate run exports. Render green boxes only for supported violation decisions and export the evidence and assessment coverage.

Use explicit cannot-assess states for missing context; do not treat helmet nondetection as a bare head, an unassociated red light as the controlling signal, or majority motion as legal direction. Movement rules require video. Reset track history at scene changes.

Complete model integration and real image/video evaluation before claiming success. Synthetic rule tests cannot establish model accuracy. The later frontend redesign remains a separate deferred change. No cloud deployment or automatic enforcement is requested.
