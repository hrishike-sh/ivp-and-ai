# Classical motion analysis — 17 October 2026

Update: see [Automatic tracking and speed](AUTOMATIC_TRACKING.md) for the newer no-selection workflow, the optional local vehicle detector, and current validation. The historical results below describe the earlier IVP-only implementation.

## What is demonstrated

A standalone IVP video pipeline isolates foreground, suppresses the background subtractor's shadow label, cleans binary regions, associates them over time, measures crossings through an image-space line and accumulates a movement heatmap. It needs no YOLO, LLM, model download or cloud service. The output is a synchronized original/tracks/mask/heatmap MP4, numerical records and inspectable intermediate results.

## Evidence

- Fixed-camera highway: 15 seconds, 450 frames, 960×540. Run `20261017-150222-5396bace` completed through the browser. It reported 11 downward and 3 upward moving-region crossings, peak foreground coverage 4.70%, 14.30 measured seconds and 21 warm-up frames. No large merged region exclusions occurred. These are algorithm outputs, not a manually labelled accuracy benchmark.
- The original Indian upload was tested as a 3-second crowded sequence. Some foreground regions merged across multiple objects and fragmented around shadows. The tracker now excludes very large bounding regions from counting; the mask still contributes to activity. This clip is exposed as a stress test, not an accurate vehicle-counting demonstration.
- OpenCV's street sample shows pedestrian tracks and trajectories. It is explicitly labelled pedestrian movement.
- Browser confirmed a decoded H.264 result with 15-second duration, 960×540 dimensions, readyState 4 and no media error.

The final full Python suite passed **152 tests**. New tests cover directional hysteresis without duplicate counts, reverse direction, track expiry, stationary imagery, known moving shapes with a known crossing, coherent camera translation, scene reset, invalid settings, original timestamp/audio preservation and cancellation without publishing a completed video. JavaScript syntax checks pass. Browser requests are serialized to avoid overlapping startup-preview/sample API operations.

## Reproduce

1. Start Traffic Lab and choose **Load moving traffic demo**.
2. Leave a horizontal line at 65%, full frame, then choose **Analyse movement · no AI**.
3. Play the generated video, inspect the activity chart and expand the intermediate motion stages.
4. Download the evidence ZIP. It contains CSVs, foreground seconds as a NumPy array, stage PNGs, configuration and source mapping. The analysis operates at a maximum width of 960, independently of enhancement sliders.
5. Try the Indian crowded stress test and compare the failure modes. Do not equate a connected region with a vehicle.

## Sources and limits

The highway clip is a 15-second local excerpt of [highway_01.mp4 in rpi-urban-mobility-tracker](https://github.com/nathanrooy/rpi-urban-mobility-tracker/blob/master/data/videos/highway_01.mp4). The pedestrian sample is [OpenCV extra test data](https://github.com/opencv/opencv_extra/blob/4.x/testdata/cv/video/768x576.avi). Local source records and hashes are in `demo/motion-sources.json`. Downloaded clips and the copied user upload are ignored by Git; no media was published.

The fixed-camera method does not handle all Indian traffic. Slow/stopped objects can become background; occlusion can merge identities; shadows and reflections can split them. Warm-up, coherent camera shifts, scene changes and widespread foreground suppress measurements, but that guard is itself heuristic. Line crossings are region-track events rather than validated vehicle counts. The heatmap measures foreground duration at image pixels, not road occupancy, calibrated speed or traffic violations. Human-labelled multi-scene evaluation remains necessary before claiming count accuracy.
