# Automatic tracking and speed

The video workflow discovers tracks automatically. No vehicle boxes or per-vehicle points are supplied by the user. The optional single-patch tracker remains collapsed for IVP experiments; it is not required by either automatic mode.

## Optional incident review — 18 October 2026

The video panel now has **Incident review · optional**, disabled by default. It uses the existing automatic vehicle tracks and classical geometry/time measurements. Configure a finite stop boundary using the counting-line orientation/position and its start/end percentages. Optionally enter a rectangular crossing zone and an approach rectangle. Geometry refers to the first frame. No vehicle is selected manually.

Choose observe, green, red, stop-required or unknown. A timeline can supply `start seconds, end seconds, condition` per line; uncovered time is unknown. These are explicit user inputs, not signal recognition. Observe/green crossings are neutral. Unknown conditions and transitions within a crossing bracket are withheld. A crossing zone is neutral unless explicitly marked restricted under the supplied red condition; a zebra marking alone never creates an offence candidate.

Speeding review requires an explicit threshold, a valid source-bound road calibration, confirmation of dimensions and confirmation that playback represents real time. At least three reliable samples must stay above the threshold **plus max(2 km/h, 5% of the threshold)** for 0.5 seconds. Borderline estimates are withheld. This is a conservative review policy guard, not a validated measurement-accuracy bound, confidence interval or legal tolerance. Synthetic fixtures use declared virtual dimensions and carry synthetic labels in video, events and the speed summary.

Missed-stop candidates require an observed entry into the configured approach and uninterrupted calibrated measurements. A completed stop needs one second at or below 2 km/h. Missing history, occlusion, weak/ambiguous/clipped detections and unsupported registration suppress conclusions. Even one missing observation resets crossing evidence; a camera/scene change invalidates configured geometry for the rest of the run. Temporal speed smoothing can prevent a short stop from being positively confirmed, so such cases remain withheld.

The implementation reuses `traffic_ai.geometry` for finite crossings and signed distances. `ivp/incidents.py` consumes observed tracks, `ivp/incident_export.py` streams evidence, and `ivp/motion_worker.py` integrates them without changing detector inputs. The API accepts optional `incidents` with `enabled`, `line`, `direction`, `zone`, `zone_role`, `approach_zone`, `condition`, `condition_intervals`, `speed_limit_kmh`, `calibration_confirmed`, `real_time_confirmed` and `synthetic`. Coordinates are normalized; rectangles use left/top/right/bottom. A left-to-right line's positive side is downward; a top-to-bottom line's positive side is leftward. Enabled incidents require vehicle mode.

Each assessment is a `candidate`, `observation` or `withheld`, with timestamp, track ID, reason, detector score/quality, measured values, settings, calibration and coordinate mapping. Detector confidence is not an incident probability. Crossing timestamps are interpolated between observed sides; the evidence thumbnail/anchor belongs to the later confirming frame, recorded separately. JSONL and CSV retain all events. The report indexes the first 100 assessments; thumbnails are limited to the first 40. Track state expires and is capped at 512. Downloads and thumbnails are exposed only after successful completion. The evidence ZIP includes the incident stream, configuration and images.

Synthetic regression inputs live outside the repository at `C:/Users/rushi/Documents/Codex/2026-10-18/task/synthetic_traffic_fixtures_v1`. `scripts/validate_incident_fixtures.py` uploads videos and calls the real API/YOLO/tracking worker; it never opens evaluation ground truth. `scripts/evaluate_incident_fixtures.py` compares saved outputs afterward. The fixtures are unchanged. They test one synthetic car and declared scale, not Indian traffic accuracy or real-world speed calibration. The earlier real Indian tracking checks below remain separate evidence.

The initial full fixture evaluation is retained at `runs/incident-fixtures-20261017-202920-evaluation.json`: 12/13 scenarios met their acceptance checks. Exact-threshold footage falsely produced a candidate at 30.32 km/h against 30; this motivated the explicit measurement guard. The completed-stop case produced a withheld assessment, not a confirmed stop. Neither result is concealed or treated as proof of real-world reliability.

The rerun, `runs/incident-fixtures-20261017-203454-evaluation.json`, meets **13/13 scenario acceptance checks**: twelve actual detector/tracker/video exports and one rejected invalid calibration. Every exported clip retains all 180 frame timestamps and a valid evidence ZIP. The corrected 30 km/h boundary produces no speeding candidate; 36 km/h produces one after stable observations. Red and missed-stop crossings are within the fixture's two-frame tolerance; hidden crossings are not inferred. This pass also checks that visible crossings were actually assessed, so negative cases cannot pass merely because no vehicle was detected.

The final current-code Python suite passes **299 tests**, including the zone-condition-transition guard. Six JavaScript tests and syntax checking also pass. `runs/incident-final-checkpoint-20261018.json` records the final source/test-log hashes and links the earlier scoped acceptance record. Constant-condition fixture coverage is separate from the transition regressions; the historical failed evaluation remains intact. Browser-driven run `20261018-020955-9954d76a` uploaded the fixture, configured red line and explicitly restricted zone review, and produced two review candidates without selecting a vehicle. All twelve seconds played successfully; browser-downloaded incident CSV/evidence ZIP match disk hashes. Saved calibrated red result `20261018-020547-5dfa82af` shows the synthetic scale clearly. The screenshot of its modal is saved; a separate blank capture is explicitly recorded as failed evidence. No dependencies were installed, fixtures modified, or changes published.

## Handoff at a glance

Use [README's current handoff](../README.md#current-handoff--18-october-2026) for the existing H-drive installation, Start.cmd, ready result and automatic processing steps. The app is at [localhost:8511](http://127.0.0.1:8511/). Its launcher reused the healthy server without a restart; Saved runs search reopened the ready city result successfully.

| Review | Evidence and scope |
| --- | --- |
| Current-code checks | **251 Python tests** on the consolidated backend; **4 JavaScript tests** after the Saved runs fix. [Acceptance index](../runs/handoff-20261018/acceptance-index.json) records source hashes and historical-versus-current matches. |
| Indian tracking | [Development checks below](#current-verified-state--october-18-overnight-continuation): city 12/12, Delhi 16/16, street intersection 6/7, rickshaws 4/5. Retained misses and episode boundaries matter; these are sparse development observations. |
| Variable-rate timing | [VFR browser evidence](../runs/20261018-001932-9d5ffbc5/browser-validation.json): 401 frames, exact 20-second playback/chart and matching downloads. Derived cadence check. |
| Longer processing | [Sustained validation](../runs/20261018-004957-746f11b6/sustained-validation.json) and [browser acceptance](../runs/20261018-004957-746f11b6/browser-validation.json): 1,800 frames, 180 seconds, full playback, downloads and corrected worker-memory sampling. Repeated footage only. |
| Failures and retries | [Upload/retry](../runs/upload-retry-validation-20261018.json), [status race](../runs/status-race-validation-20261018.json), [owned-worker termination](../runs/worker-termination-validation-20261018.json). Failure injection used isolated files/test servers. The termination test simulates only the grace clock. |
| Review changes | [Working-tree inventory](../runs/handoff-20261018/change-inventory.json) lists tracked and untracked files with hashes and qualified provenance; [tracked-file diff](../runs/handoff-20261018/tracked-changes.patch) is the local diff against HEAD. Untracked source files are linked in the inventory and are not included in that patch. |

Evidence under `runs` is local and Git-ignored. Older records keep the hashes of the code they actually checked; the index identifies mismatches rather than silently rewriting historical evidence. The tree already contained substantial uncommitted work, so the complete diff is not attributed solely to this iteration. Nothing was committed or published.

Remaining limits: no measured real-traffic km/h ground truth; one road calibration is required for physical units. Occlusion can still lose identities, and confirmation delays miss some clipped entrants. IVP-only regions are not whole vehicles (the city whole-vehicle check was 0/12). Repeated/derived clips are timing and workload checks. Memory sampling starts after warmup and covers three minutes, not indefinitely long recordings. Clean-machine installation was inspected but not executed; the existing FFmpeg PATH location on this computer was preserved.

## Current verified state — October 18, overnight continuation

The default vehicle mode uses the existing local detector with bottom-centre-aware ByteTrack association and conservative short-gap recovery. It needs no manually selected vehicles. Standalone IVP remains a separate foreground/texture analysis mode. Recent improvements cover low-frame-rate recordings, speed outliers, processing cost, and job recovery after browser refresh.

| Check | Latest evidence | Scope |
| --- | --- | --- |
| Crowded Delhi | `runs/20261017-233711-e6defc9c`: **16/16** checked observations, no checked ID changes; 335 frames with exact source timing | The distant bus now matches at ten seconds after recovery through newly observed boxes. These are development spot checks, not full-scene accuracy. |
| Indian city | `runs/20261018-000645-35608fe8`: 12/12 checked observations, no checked ID changes; 600 frames with exact timing | Four manually annotated evaluation vehicles; annotations are never tracker inputs. |
| Separate street intersection | `runs/20261017-233814-3acd46b1`: 6/7 observations, no checked episode ID changes; 391 frames with exact timing | Truck at seven seconds still unconfirmed. Full occlusion separates taxi episodes; identity continuity across that gap is not claimed. |
| Five-fps city derivative | `runs/20261017-233919-e5c8480a`: 12/12, 100 frames, exact 20-second timing, 894 accepted px/s samples | Every sixth source frame; a cadence regression, not independent new traffic footage. |
| Rickshaws before observed-history recovery | `runs/20261017-234503-6fb5acfa`: **4/5 observations, one object changes ID**; 365 frames with exact timing | Large clipped foreground rickshaw is unconfirmed at one second, then appears at 1.167 s. Background rickshaw changes from ID4 to ID34 after partial occlusion moves the predicted bottom edge away from the vehicle. These unfavorable checks remain included. |
| Rickshaws with observed-history recovery | `runs/20261018-000520-7cbdea51`: **4/5 observations, no checked ID changes**; 365 frames with exact timing | The same clipped foreground miss remains. A background rickshaw now keeps its ID after partial occlusion corrupts the normal box prediction. |
| Variable-rate city derivative | `runs/20261018-001932-9d5ffbc5`: 12/12, no checked ID changes; 401 frames, exact source timestamps | Frame intervals alternate between 1/30 and 1/10 s. Decoded footage, export and activity chart all span 20 s, despite source metadata claiming 19.9 s. This is a cadence regression using the city sample. |
| Pure-IVP city four-stage export | `runs/20261017-230227-4c1d83da`: 600 frames; **0/12 whole-vehicle box matches** | Texture regions are not whole vehicles. Its 149 region IDs and 12,321 motion-speed samples do not establish vehicle-count or vehicle-speed accuracy. |

### Sustained workload: three minutes

`runs/20261018-004957-746f11b6` processes a clearly named 180-second workload: nine repeats of the existing city clip, resized to 960×540 and sampled at 10 fps. No longer local traffic source was available. Free space was checked first (about 33 GB on C: and 70 GB on H:); the derivative uses 44.2 MB on H:, and the complete run uses about 80.5 MB. Originals are unchanged. This is workload/timing evidence, not independent vehicle-tracking accuracy or real-world speed validation.

The job completed in 372.5 seconds. All 1,800 exported frames match source presentation timestamps exactly; all frames appear in the 600-bin activity chart, which ends at 180 seconds. The evidence ZIP passes CRC validation. UI-downloaded MP4 (63.2 MB) and evidence ZIP match their saved SHA-256 hashes. Browser progress advanced, reopening Saved runs and reload restored polling, and the earlier short demo remained playable while processing. Full normal-speed browser playback subsequently reached 180 seconds with no media or console errors; see `browser-validation.json`.

The longer run exposed a client bug: opening an unfinished motion run tried to render its request settings as completed measurements. The UI now renders measurements only for completed runs and restores live polling for active runs. A regression covers queued, running, encoding, unknown, cancelled, failed, interrupted and completed states; all **4 JavaScript tests** and syntax checking pass. Python processing code is unchanged from the **251-test** full-suite checkpoint. No server restart was required.

Correct memory sampling began at frame 864 and follows the real child Python worker. It recorded 98 process-tree samples through completion: observed peak worker RSS was 1,766,809,600 bytes (about 1.77 GB), and the median changed by 5,531,648 bytes across sampled loops 5–9. This short workload does not establish a bound for arbitrarily long recordings, and initialization peak was not captured. The initial single-PID sampler measured only the Windows virtual-environment launcher; that misleading measurement is explicitly separated and retained for traceability. See `sustained-validation.json`, `worker-memory-validation.json` and `workload-process-tree.jsonl` in the run.

### Recovery from actual observations

An established, recently lost ID may recover through two consecutive weak detections when both boxes agree, their bottom contact stays near the prediction, and no competing track or detection has a similar match. A weak detection cannot create a new ID. Detector scores are preserved. Missing frames receive no invented coordinates. Recovery always clears speed history and crossing state, even for very short gaps.

Recorded-detection replays exactly reproduce the existing ground-anchor baseline on all three clips. Recovery changes the Delhi check from 15/16 to 16/16 while retaining the other checks. The full exported worker confirms that result. All 12 recovery events across those clips were inspected as paired source crops in the H-drive `association-trace-20261017-224234`, `223959` and `224559` experiment folders; their `recovery-observations.json` files identify timestamps and boxes. This is a small visual audit, not an exhaustive correctness claim. The final Delhi export contains six recovery rows, all with blank speed and original detector confidences between 0.207 and 0.298. Its speed replay matches all exported values exactly.

Adverse tests reject single or nonconsecutive weak observations, competing nearby identities, stale IDs, newborn tracks, distant proposals and insufficient confidence. Reset clears pending matches. Per-frame diagnostics and pending state remain bounded in production. Current evidence for the four complete exports is in `runs/recovery-validation-20261017.json`.

### Recovery after a partially hidden box changes shape

The current default adds a conservative fallback using recent **observed** boxes when the normal Kalman prediction drifts after an occlusion. Median bottom-centre and box-size trends use actual presentation timestamps. The fallback requires eight recent observations, an established ID, a sustained short gap, two consecutive new detections, and a clear margin over competing identities. Merged proposals and boxes touching the frame edge cannot use this extra fallback. It does not emit positions while a vehicle is invisible.

An initial trial accepted a proposal covering two vehicles. That trial was rejected; its crops and measurements remain preserved on H:. Additional border, grouped-proposal and competition checks were added before promotion. The final rickshaw export changes the checked background vehicle from two IDs to one, without relaxing the new-track confirmation requirement. The large foreground rickshaw still fails the one-second check and first appears at 1.167 seconds. These are development observations, not held-out accuracy estimates.

The city export still matches 12/12 observations. Its extra robust recovery is outside the analysis region, so it does not establish a published-trajectory improvement. Recovery diagnostics explicitly count the full frame. Switching recovery geometry from frame indices to actual timestamps leaves every replayed association output unchanged across four fixed-rate traces (600, 335, 390 and 365 frames). A dedicated irregular-cadence regression verifies why the timestamp clock is necessary.

The variable-rate export additionally exposed incorrect activity-chart duration when container metadata understated decoded duration. The chart now derives its endpoint from recorded frame timestamps and durations, and streams measurements into at most 600 bins. Video encoding already preserved those timestamps. Evidence is in the run's `automatic-validation.json`; robust-recovery exports are recorded in `runs/robust-recovery-validation-20261018.json`.

### Speed observation safeguards

Actual presentation timestamps determine velocity. Gap limits now account for nominal frame interval, so ordinary 5 fps footage no longer resets on every frame. At least eight observed positions and half a second are still required; the maximum history grows from 1.2 to 1.6 seconds at 5 fps. Missing observations, ambiguous overlaps, camera failures and invalid calibration still withhold speed.

A local quadratic prediction checks the latest bottom-centre position against earlier observations. A sudden position change clears the speed window without changing the track ID. The tolerance accounts for position noise and expected frame displacement. This is a conservative heuristic, not proof that an identity was wrong. Smooth acceleration, turns and small box noise pass synthetic tests at 5, 10 and 30 fps; calibrated and pixel-space jumps are rejected and recover after a fresh window.

The first replay against an older 30 fps export differed in 3,231 baseline samples because the cadence change admits boundary observations within a 1e-6-second window tolerance. That comparison was not used as an isolated speed-guard result. A fresh export (`232010-9343114a`) reproduces exactly with the guard disabled: 7,232 accepted samples and zero differences. Enabling only the guard gives 7,166 accepted samples and 211 changed readings (including fresh-window values). The guard-only Delhi export (`232327-30d7d6df`) has 21 speed-window resets and 3,045 accepted samples; replay reproduces it exactly, and its observed IDs, timestamps and boxes match the previous Delhi geometry. With subsequent short-gap recovery enabled, the final Delhi run has 3,064 accepted speed samples and the same 21 position resets. No measured real-world speed truth is available.

Calibration also assumes real-time footage. Playback timestamps from slow-motion or time-lapse video cannot establish actual km/h without a known time scale. The UI and exported report state this.

### Processing and browser reliability

Stage mosaics and heatmap visualizations are now built only when displayed or when a new peak frame is saved. Foreground measurements still run on every frame. Unchanged enhancement output reuses its quality measurements. A paired profiled city run fell from 104.27 to 79.86 seconds (23.4% in that pair); all core trajectory/activity/measurement CSVs and final heatmap/track images were byte-identical. This is one measured pair, not a general speed guarantee. See `runs/20261017-225441-ea39e52a/performance-validation.json`.

Browser refresh restores active video progress and cancellation controls. Saving a frame has its own result card and no longer replaces the active video job. Live checks exercised concurrent frame export and mid-job reload; the IVP stage run restored from 149/600 to 212/600 processed frames. Progress reports actual processed frames and measured processing rate. The latest Delhi video opens with ready state 4 and duration 11.166667 seconds; its report shows the 21 speed resets and explicit px/s units.

At the earlier status-race checkpoint: **249 Python tests and 3 JavaScript tests passed**, plus JavaScript syntax checking. The healthy app remains available at localhost:8511. After all workers finished, the local server was restarted under the job lock to apply the HTTP early-rejection fix. Forty live rejected requests returned the expected JSON errors with no Windows socket reset; health and browser reconnection succeeded. The latest city video played through all 20 seconds with no browser console errors. No packages, models, schedules or Git publication were added.

The newest variable-rate run was also accepted through the browser at 2026-10-17 19:00 UTC: playback reached 20 seconds with no media or console errors, all 80 activity-chart bins rendered, and the final bin read 19.75–20.00 seconds. UI-downloaded trajectory CSV and evidence ZIP matched the run files by SHA-256; the ZIP passed CRC validation. Its `browser-validation.json` identifies current source hashes and the exact scope of these checks. Screenshot capture was unavailable; no screenshot proof is claimed.

A subsequent interrupted-job check reproduced a status race in four terminal/fresh-state cases: polling could read an old running status, acquire the released worker lock, then overwrite a newer result as interrupted. Recovery now rereads status and its age while holding the lock. A truly stopped stale worker is still marked interrupted, preserving diagnostic files. All 249 Python tests pass. The idle server was restarted once under the worker lock to load this server-side change; health returned successfully. Evidence: `runs/status-race-validation-20261018.json`.

A later isolated upload/retry test found and fixed rejected-copy leakage. Interrupted transfers and corrupt MP4/MOV/AVI inputs now leave no accepted registry entry or rejected file copy. A subsequent legitimate upload, preview, frame export and full video export succeeded on the same test server; audio and timestamps were retained. All 28 affected server/status/video tests passed after that change. The earlier full-suite count above belongs to the status-race checkpoint. Launcher syntax and missing-runtime guidance were checked without installation; fresh AI/Ollama paths and the current UI instructions are corrected in INSTALL.md. See `runs/upload-retry-validation-20261018.json` for exact scope and source hashes.

Consolidated current-code verification subsequently passed **251 Python tests**. A real owned worker process was terminated during processing in an isolated directory/server. Its OS lock released; after an explicitly simulated 40-second grace-clock advance, the API marked it interrupted and exposed no completed preview or download. Existing diagnostics stayed byte-identical. A new worker completed the retry, whose served MP4 matched saved bytes, retained audio and decoded with the source timestamps. The live demo was not restarted. This verifies process recovery, not vehicle or real-world speed accuracy. `runs/worker-termination-validation-20261018.json` records exact scope, hashes, and the initial corrected test-harness assumption.

The sections below retain implementation context and earlier verification checkpoints; older counts and limitations are historical.

## Classroom demo

1. Double-click `Start.cmd`, then open `http://127.0.0.1:8511/`.
2. In the IVP laboratory, click **Load Indian city demo**.
3. Leave **Vehicles · local detector + IVP** and **Full-size tracks & speed** selected.
4. Click **Track automatically & calculate speed**. The progress indicator supports cancellation.
5. Play the result. Each observed track has a persistent coloured ID, a trajectory, and a speed when its recent positions are usable.
6. Expand the processing stages to explain background estimation, shadow rejection, morphology, optical flow and accumulated movement. Download the MP4, trajectory CSV, or evidence ZIP.

The existing local RTX 4050 / H-drive runtime is used. This change installs no packages and downloads no model. Processing is slower than playback; the 20-second development clip took roughly 1.5 minutes including encoding on this machine. Wait for the progress bar rather than opening multiple jobs.

The default demo is an elevated Indian city intersection credited to [aksinfo7 universe on Pexels](https://www.pexels.com/video/busy-city-intersection-traffic-in-india-30169851/). Its exact city has not been verified. It contains cars, taxis, motorcycles and buses. The crowded Delhi sample remains selectable as a harder test. Source links, transformations and file hashes are recorded in `demo/motion-sources.json`; downloaded videos are excluded from Git.

## Two explicit methods

| Method | Discovery and identities | IVP contribution | Main limitation |
| --- | --- | --- | --- |
| Vehicles · local detector + IVP | Existing local YOLO11s boxes; ByteTrack Kalman prediction and two-stage association, including weak detections that support existing IDs | Camera registration, foreground/shadow separation, morphology, optical flow, trajectories, line crossing and calibrated speed | Misses and identity switches remain possible. COCO has no auto-rickshaw class, so the interface says vehicle rather than showing misleading vehicle-type labels. |
| Moving texture regions · IVP only | MOG2 components seed Shi-Tomasi corners automatically; forward/backward Lucas–Kanade follows each object's texture independently of later blob merges | Entire workflow uses classical IVP; geometric and colour checks permit conservative recovery after brief occlusion | A region may represent a pedestrian, part of a vehicle, or several touching vehicles. It cannot guarantee whole-vehicle identities. |

The vehicle mode is explicitly labelled as using AI; the report records `uses_ai: true`, the checkpoint hash and processing device. The pure-IVP mode loads no detector or LLM. Both preserve the separate 22-stage image walkthrough. The detector does not calculate speed or replace those IVP stages. ByteTrack implementation reference: [Ultralytics tracking documentation](https://docs.ultralytics.com/modes/track/).

Camera correction uses stationary texture outside the selected road region. Short-range LK keyframes retain transforms into the first frame; ORB matching can recover the reference when LK fails. RANSAC, transform-size checks and a minimum 60% frame overlap reject unsupported transforms. Black warped borders contain no invented image content. The raw-to-analysis affine matrix for every frame is exported.

## Speed: automatic per track, calibrated once per scene

Without road calibration, the app reports **analysis pixels/second**. A model cannot obtain reliable metres from arbitrary uncalibrated footage. The supplied Indian samples have no measured road dimensions or speed ground truth, so their results do not display invented km/h values.

To obtain approximate km/h, enable **Speed measurement**, mark four corners of one measured rectangular road patch in the first frame, and enter its real width and length. This is one scene calibration for all tracks, not a box around each vehicle. A homography converts bottom-centre observations into metres. Least-squares velocity uses real presentation timestamps over a 0.5–1.2 second window.

Speed is withheld outside the calibrated patch, after an observation gap, during uncertain camera registration, for clipped/weak vehicle detections, and for unstable trajectories. A detected scene change invalidates physical calibration. Curves, vehicle height, perspective, bounding-box jitter, non-flat roads and mistaken identities can still bias measurements. These are project estimates, not enforcement measurements.

## Verification and evidence

The reproducible source-frame spot check in `demo/city-tracking-check.json` marks four real vehicles at 2, 4 and 6 seconds. These 12 annotations are used only to evaluate output; they never initialize the tracker. The check transforms result boxes back to the source frame before matching at IoU >= 0.5. All 12 observations matched and each of the four vehicles kept one ID in the tested run. This is a small development check, not an exhaustive or independent accuracy benchmark.

Completed runs include `automatic-validation.json`. The Indian city export reopens as 600 frames / 20 seconds; the crowded Delhi export as 335 frames / 11.167 seconds. Both retain exact source presentation timestamps and their evidence ZIPs pass integrity checks. The latest Delhi registration change eliminated the previous camera-registration rejections on this clip; that does not prove all vehicle identities are correct.

Browser verification exercised the default demo with no manual target, started a worker, displayed the completed video and downloads, played the video from time 0 through time 20, switched to the explicitly model-free mode, and confirmed that enabling km/h without four road points produces an actionable error. Synthetic tests check known 36 km/h projective motion at multiple resolutions, irregular timestamps, occlusions, foreground merges, static ghosts, identity reset across scene/gap changes, camera pan, clipped borders, audio preservation, cancellation and corrupt inputs.

```powershell
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m pytest -q
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m scripts.validate_tracking --source india-city.mp4 --mode vehicles
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m scripts.validate_tracking --source india-delhi-overhead.mp4 --mode vehicles
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m scripts.validate_tracking --source highway-motion.mp4 --mode ivp
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m scripts.validate_tracking --run runs/<completed-run>
```

Run from the project folder. The first three validation commands create new runs under the same one-worker lock. Verification decodes both complete videos, compares timestamps, checks the ZIP and counts exported observations. Those diagnostic counts are not vehicle-count accuracy. The highway sample is non-Indian and is used only as a simpler pure-IVP regression example.

On a fresh base-only installation, the app defaults to IVP-only tracking. Vehicle mode needs the existing optional `Setup-AI.ps1` environment/model; missing runtime files produce a setup message. No cloud service is used. Dense occlusions, very small motorcycles, merges in pure IVP, poorly positioned cameras and unconstrained camera movement remain failure cases.

## Recorded local runs, 17 October 2026

| Run | Mode / source | Reopened frames | Timestamp error | Camera registration rejections |
| --- | --- | --- | --- | --- |
| `20261017-172240-624244cd` | Vehicles + IVP / Indian city | 600 | 0 s | 0 |
| `20261017-171953-917afbf1` | Vehicles + IVP / crowded Delhi | 335 | 0 s | 0 |
| `20261017-172059-b8b98673` | IVP-only / non-Indian highway | 450 | 0 s | 0 |

The city run contains 7,237 accepted speed observations across time, in px/s; this is not 7,237 vehicles. Its 12/12 identity spot-check result is in `identity-spot-check.json`. Browser/download evidence is in `browser-validation.json`: the video range request returned 206; CSV and ZIP downloads returned 200 and matched the saved bytes. Each evidence ZIP contained 16 files and passed integrity checking. All **185 automated tests passed**, and JavaScript syntax checking passed. Earlier diagnostic runs are retained separately and may have different parameters/results.

## Crowded-scene follow-up: identity and geometry, not just successful export

The latest source-frame Delhi check marks a blue bus, black e-rickshaw, blue-back auto and white hatchback at 2, 5, 8 and 10 seconds. The hatchback is partly occluded late in the clip. Source annotations and hashes are in `demo/delhi-tracking-check.json`; they are never supplied to inference. Results: **15/16 visible-box observations matched, with one identity change**. The distant blue bus is missed at 10 seconds. The blue-back auto changes from ID15 to ID52; the detector sometimes provides one large box spanning that auto and the one ahead of it. This is an unresolved failure, not reliable continuous identity recovery.

Four stationary landmarks were also checked independently of the estimated camera transform. Small reference patches were matched only inside manually identified source-frame windows. Of 16 checks, 13 exceeded the 0.8 correlation threshold. Median registration residual was **0.949 analysis pixels**, maximum **3.449 pixels**. The three rejected patch matches are recorded, not treated as successful measurements. These background checks support local registration quality; they do not validate road-plane geometry, parallax or physical speed.

Two experimental proposal filters did not improve the identity check and were removed. A BoT-SORT trial with the existing YOLO model's native appearance features also gave 15/16 matches and one ID change. It remains outside the app default; no extra model was downloaded. Its reproducible script is `scripts/experiment_native_reid.py`, with results under `H:/CodexStorage/ivp-ai/experiments/native-reid-20261017-174702`.

A focused reliability guard is retained: nested tracked boxes sharing approximately the same bottom contact point are marked **?**. Speed and crossing events are withheld for those hypotheses, and speed must gather a fresh stable window afterwards. IDs are not silently merged. Ordinary overlapping boxes with distinct bottom contact points remain usable. The CSV now exports `tracking_state`, and the UI reports frames affected by this ambiguity.

| Final run | Source | Identity check | Ambiguous exported observations | Result |
| --- | --- | --- | --- | --- |
| `20261017-175009-ee8cdcb1` | Crowded Delhi | 15/16; one object changes ID | 18 across 11 affected frames | All ambiguous speeds blank; no crossing events from those observations |
| `20261017-175112-353b8a6d` | Indian city | 12/12; no checked ID changes | 97 across 74 affected frames | All ambiguous speeds blank; no crossing events from those observations |

Both final videos reopened completely (335 and 600 frames), with zero presentation-timestamp error and intact evidence ZIPs. The city demo remains available in Saved runs and the main workspace. All **188 tests passed** after the guard; JavaScript syntax checking passed. The final saved city result was opened through the browser and reported its ambiguity notice and a 20-second, ready-to-play video.

### Exact speed-test evidence

`tests/test_speed.py` passes 16 cases. These are synthetic correctness checks, not speed truth for either Indian video:

- A 10 m/s trajectory projects through a known trapezoidal homography at 1000x1000, 500x500 and 1280x720 resolutions with irregular timestamps. Each recovered estimate is 36 km/h within 0.01 km/h.
- A new calibrated recovery test creates a 0.4-second observation gap. Speed becomes unavailable, remains unavailable through the first 0.4 seconds after reappearance, then returns to 36 km/h only after a sufficient fresh window. Moving the observation outside the calibrated road immediately withholds speed again.
- Missing calibration fields, crossed/non-convex corners, NaN length, zero width and a tiny degenerate patch raise validation errors. The browser separately rejects enabling km/h without all four road corners.
- Size jumps, outside-road observations and camera/scene invalidation withhold speed. Vehicle tests cover weak/clipped observations, camera-warp borders, short recovery, scene-reset identity namespaces and ambiguous overlapping hypotheses.

To repeat the crowded source-frame and landmark check:

```powershell
& 'H:\CodexStorage\ivp-ai\venv\Scripts\python.exe' -m scripts.check_delhi_tracking runs/20261017-175009-ee8cdcb1
```

Launch was verified from `C:\Users\rushi\Desktop\s5\Projects\IVP and AI` using `& 'H:/CodexStorage/ivp-ai/venv/Scripts/python.exe' launch.py --no-browser`; `Start.cmd` remains the shortcut. This pass created no temporary schedule, installed no dependencies, downloaded no models, and published no changes. The audit is saved in `runs/iteration-audit-20261017.json`.


### Calibration and cancellation acceptance pass — October 17 evening

Road calibration now carries the source media ID, local file revision and reference-frame index into the request and speed report. The API rejects calibration for another source or a file changed after preview; the worker checks the file revision again before decoding. This revision uses path, size and modification time, not a cryptographic content-integrity claim. Existing offline fixtures can still supply a calibration directly to the reusable pipeline.

Opening or restoring footage clears the marked corners, enable checkbox and measured dimension fields. Calibration is deliberately not restored from a different saved run. Reusing saved enhancement adjustments does not import its road calibration. Normalized corners remain usable when changing analysis resolution, ROI or tracking method within the same source; the measured rectangle still applies only to its road patch. Marking starts on the original-colour first frame, and clicks are ignored while the preview is pending or its image has not loaded.

Cancellation is checked again after result packaging. A cancelled run exposes no completed downloads; its partial trajectory diagnostics remain local. A fresh run gets its own directory and independent cancellation marker. Tests cover cancellation before decoding, after three decoded frames, and during packaging, followed by successful retry. Calibrated export tests verify source revision, mode, road geometry and km/h metadata in the report and evidence ZIP; the synthetic test dimensions are not measurements of the Indian samples.


The browser acceptance run `20261017-222216-1995765e` completed 600 frames in 20 seconds of source time with no timestamp error. Its source-frame identity check remains 12/12 with zero checked ID changes; 7,164 speed observations use px/s. The browser downloaded the CSV and ZIP with byte-for-byte matches to the saved artifacts, and the video played to an observed 9.82 seconds with no console errors. A real cancellation and fresh retry were exercised. See that run's `automatic-validation.json` and `browser-validation.json`.

A transient status-file read exposed a polling bug: `unknown` had been treated as terminal, so the UI could miss completion. Status reads now retry briefly, and the browser keeps polling through unknown states. A JavaScript regression test covers running → unknown → encoding → complete and terminal cancellation/failure states.

Final validation: **194 Python tests passed**, plus **1 JavaScript lifecycle test** and JavaScript syntax checking. Earlier full-suite attempts intermittently hit Windows socket error 10053 in the request-boundary test; the focused test and final full rerun passed. The socket-error cause is not established or claimed fixed. It did not occur during the verified browser export/download path. No changes were published or installed.


### Overnight continuation — bottom-centre association

The default optional vehicle tracker now combines predicted-box overlap with normalized bottom-centre distance for high-score matching, retaining ByteTrack's Kalman lifecycle, confidence fusion, IoU-only low-score stage and 0.8-second lost buffer. Pairs with less than 10% overlap do not gain an anchor-based match. This uses geometry, not new model weights or manually supplied vehicle seeds. `traffic_ai/association.py` contains the implementation.

A recorded-detection replay reproduced the previous ByteTrack outputs exactly. It localized the rickshaw failure to alternating individual and two-vehicle boxes. A candidate filter that removed larger grouped proposals worsened Delhi coverage to 14/16 and was rejected. The anchor-cost candidate retained 15/16 while eliminating the checked rickshaw ID change. Its full exported run reproduced that improvement.

| Full exported check | Previous | Updated association | Evidence |
| --- | --- | --- | --- |
| Indian city | 12/12, no checked ID changes | 12/12, no checked ID changes | H-drive experiment `association-trace-20261017-223959` |
| Crowded Delhi | 15/16, one checked ID change | 15/16, no checked ID changes | App run `20261017-224901-37a58e31` |
| Separate street intersection | 5/7 | 6/7, no checked episode ID changes | H-drive experiment `association-trace-20261017-224559` |

The extra street-intersection annotations were chosen on source frames before evaluating the candidate on that clip. The taxi is treated as separate episodes across prolonged total occlusion; no identity recovery across that gap is claimed. The truck at seven seconds is still missing from confirmed output. These remain small development checks, not exhaustive or held-out benchmarks. Source hashes and annotations are in `demo/intersection-tracking-check.json`.

The crowded Delhi bus is still missed at ten seconds: its low-confidence detection temporarily cannot reactivate the lost track, which returns at about 10.17 seconds. No invented coordinates or speed fill that gap. Independent landmark registration remains 0.949 px median / 3.449 px maximum over 13 accepted checks. The updated runs retain speed suppression for ambiguous overlaps, missing/clipped observations and invalid calibration. The app's completed Delhi video plays and preserves all 335 source timestamps.

Five new synthetic association tests cover close opposing traffic, reversed detection order, brief occlusion, changing top extent, distant nonmatching vehicles and scene resets. Full validation: 201 Python tests pass. The earlier Windows socket failure was reproduced on eight of 120 early rejected requests; small rejected bodies are now drained with a bounded 0.25-second wait and 64 KiB cap before the JSON error is sent. Access checks are unchanged. The live healthy server has not been restarted for this backend change; it takes effect on the next server launch. Vehicle workers already load the new association on each run.
