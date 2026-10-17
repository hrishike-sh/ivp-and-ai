# Indian traffic and speed validation - 17 October 2026

Update: see [Automatic tracking and speed](AUTOMATIC_TRACKING.md) for the newer no-selection workflow, the optional local vehicle detector, and current validation. The historical results below describe the earlier IVP-only implementation.

## What was actually tested

Three real daytime Indian street videos by **md Jahangir alam**, sourced from Pexels. Visible Delhi road signs corroborate the location. These include mixed autos, e-rickshaws, buses, motorcycles, pedestrians, close occlusion and camera movement. They are short street recordings, not calibrated CCTV benchmarks. They do not establish performance throughout India, at night or in rain.

| Local sample | Original source | Duration | Frames | Completed run |
|---|---|---:|---:|---|
| india-delhi-overhead.mp4 | [Delhi junction](https://www.pexels.com/video/bustling-delhi-traffic-jam-at-busy-intersection-35262193/) | 11.167 s | 335 | 20261017-162504-515ba7ae |
| india-intersection.mp4 | [Delhi street intersection](https://www.pexels.com/video/busy-urban-traffic-at-indian-road-intersection-35532716/) | 13.033 s | 391 | 20261017-162600-f927df35 |
| india-rickshaws.mp4 | [Autos and e-rickshaws](https://www.pexels.com/video/bustling-indian-street-with-auto-rickshaws-and-e-rickshaws-35532797/) | 12.167 s | 365 | 20261017-162707-e3733bb7 |

All **1,091 frames** decoded and exported as H.264. Comparing every decoded presentation timestamp gave **0 seconds difference** for all three exports. The clips have no audio; separate automated tests cover audio preservation. These runs took 56.52, 66.72 and 64.89 seconds respectively, including output reopening and timestamp verification, on the development computer during concurrent development activity. This is not a real-time performance claim.

Files remain local and are ignored by Git. Source URLs, direct media URLs, creator, license link, transformation notes and SHA-256 hashes are in `demo/motion-sources.json`. The Pexels license is at https://www.pexels.com/license/. No original recording was modified or artificially looped.

## Changes driven by these tests

- Camera motion was generating foreground ghosts. Registration now matches background texture outside the selected road ROI to the first frame using forward/backward Lucas-Kanade checks and RANSAC affine fitting. Empty warped borders are excluded from measurement. Unknown registration suppresses results instead of silently measuring the moving camera.
- Touching regions were stealing identities. The tracker rejects merged associations, checks area consistency and requires 0.3 seconds of track age. Speed history is discarded across merges, gaps and abrupt size changes.
- Local optical-flow arrows expose motion even when regions merge. These measure texture movement in analysis pixels/second; they are not independently detected vehicles.
- A separate **user-selected target tracker** uses Shi-Tomasi features, forward/backward Lucas-Kanade and RANSAC. It works independently of the MOG2 blobs and never invokes YOLO or an LLM. The Delhi sample has a preset selecting texture on the rear of the blue bus. Visual spot checks at 0, 3 and 6 seconds showed the patch remaining on the bus. It stops when tracking or camera registration becomes unreliable; it does not automatically reacquire another object.

## Findings and remaining limitations

| Sample | Frames excluded | Accepted automatic-region speed samples | Automatic region crossings |
|---|---:|---:|---:|
| Elevated Delhi | 130 / 335 | 235 | 1 |
| Street intersection | 56 / 391 | 46 | 2 |
| Rickshaw street | 52 / 365 | 14 | 4 |

These are algorithm diagnostics, **not count accuracy or vehicle-speed ground truth**. Camera movement, shadows, touching vehicles and partial occlusion still make the automatic region counter unreliable on these clips. A lower count is not evidence of improved recall or precision. The first sample has substantial rejected camera registration near its end. Its selected-target demonstration is more useful for explaining tracking than its automatic crossing count.

The foreground heatmap measures time spent classified as moving foreground. It cannot measure the full occupancy of stationary traffic. Vehicles can be absorbed by the adaptive background model. The selected tracker can follow the wrong texture if its initial box includes background or another road user; choose a tight textured patch and inspect the result.

## Speed calculation

Without calibration, values are **analysis pixels/second**. The preview and CSV state the unit explicitly. The selected-target result is shown separately from automatic-region statistics; averages are over accepted track samples, not per-vehicle journey averages.

For estimated km/h, click four corners of an actual rectangular patch on a flat road in frame zero, in perimeter order: far-left, far-right, near-right, near-left. Enter its **measured** width and length in metres. A homography maps image coordinates to the measured plane. A least-squares trajectory fit over 0.5-1.2 seconds gives metres/second, multiplied by 3.6. Irregular presentation timestamps are used directly.

The tracked box's bottom centre approximates road contact. A roof patch or a box around only the upper body is not a road-contact point and can bias physical speed; the sample bus rear preset is an uncalibrated texture-motion demonstration. Perspective, road slope, segmentation jitter and feature drift remain error sources. Measurements outside the calibration polygon, short/gapped/jittery tracks and implausible physical estimates are withheld. Camera/scene changes invalidate calibration. None of the downloaded clips provides measured road geometry or reference speeds, so **no real-world km/h accuracy is claimed**.

Automated checks verify a known **36 km/h** trajectory through a perspective transform at three image resolutions with irregular timestamps, a known **60 px/s** textured target, gap/size-jump rejection, invalid calibration, camera-shake correction, merged identities, occlusion loss, stationary frames, cancellation, audio/timing preservation and export reopening.

## Reproduce in the browser

1. Start the app with `Start.cmd`, then choose **Load Delhi intersection**. The sample loads a road region and counting line.
2. Choose **Follow the sample bus rear**, then **Analyse movement - no AI**. Play the result and inspect SELECTED in the trajectories CSV.
3. For your own footage, choose **Select vehicle on first frame**, then drag a tight target box. The road ROI and target box serve separate purposes.
4. To use km/h, expand **Speed measurement - calibrate for km/h**, mark four road corners and enter measured dimensions. Leave it off for these uncalibrated samples.
5. Inspect stage PNGs, motion activity, per-frame camera transforms, track speeds and the evidence ZIP.

Command-line reproduction of the three automatic analyses (exact diagnostics can change as registration guards are improved):

```powershell
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m scripts.validate_indian_motion
```

The script stores run IDs and frame/timestamp verification in `runs/indian-validation.json`. No new dependency or model is needed. The Windows launcher uses the existing H-drive runtime; setup defaults, Python downloads and uv caches also target H:.

## Final browser demonstration

Run `20261017-163309-d2a43c3a` was started through the web app using the bus-rear preset. It followed the selected texture for **238 frames / 7.93 seconds**, then stopped when camera registration became uncertain. It produced **223 accepted speed samples**, averaging **29.98 analysis px/s**; this is not km/h. The output contains all 335 source frames and reopens successfully as an 11.167-second H.264 video. The browser reported readyState 4 with no media error. The evidence ZIP passed its integrity check and includes 16 files.

The final camera guard gives verified background registration precedence over coherent foreground motion, avoiding a false camera-change alarm when many vehicles move together. The final complete Python suite passes **172 tests**, and JavaScript syntax validation passes. Browser checks also covered four-point corner selection, rejecting missing measured distances, clearing calibration, loading the Indian sample and starting/completing the selected-target job. Browser screenshot capture returned blank/clipped images; output PNGs and decoded video frames were inspected directly instead.
