import json
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from ivp.downloads import FileServer
from ivp.jobs import ROOT, cancel_job, history, new_run, now, refreshed_status, start_video
from ivp.media import MediaError, load_image, png_bytes, preview_frame, probe_video, save_upload, write_json
from ivp.pipeline import PRESETS, Settings, histogram, process_frame
from classroom import SAMPLES, render_demo


st.set_page_config(page_title="Traffic Lab · IVP + AI", page_icon="◈", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 4rem; max-width: 1540px;}
h1 {letter-spacing: -.045em; font-weight: 750 !important;}
[data-testid="stMetric"] {background: #141f32; padding: 14px 18px; border: 1px solid #26354c; border-radius: 10px;}
[data-testid="stMetricLabel"] {color: #a9bbd0;}
.eyebrow {color: #38bdf8; font-size: 13px; letter-spacing: .15em; font-weight: 700; margin: 0;}
.step {color: #a9bbd0; font-size: 15px; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def file_server():
    return FileServer()


@st.cache_data(max_entries=2, show_spinner=False)
def cached_image(path):
    return load_image(path)


@st.cache_data(max_entries=6, show_spinner=False)
def cached_preview(path, seconds):
    return preview_frame(path, probe_video(path), seconds)


def apply_preset():
    for name, value in PRESETS[st.session_state["preset"]].to_dict().items():
        st.session_state["cfg_" + name] = value


def control_panel():
    if "preset" not in st.session_state:
        st.session_state["preset"] = "Original"
        apply_preset()
    with st.sidebar:
        st.markdown("### Processing")
        st.selectbox("Preset", list(PRESETS), key="preset", on_change=apply_preset)
        st.caption("Presets fill the controls below. Your adjustments apply to the preview and export.")
        st.selectbox("Maximum width", [0, 640, 960, 1280, 1920], key="cfg_max_width", format_func=lambda n: "Original size" if not n else f"{n} px")
        with st.expander("Noise reduction", expanded=True):
            st.selectbox("Filter", ["Off", "Gaussian", "Median", "Bilateral"], key="cfg_denoise")
            st.select_slider("Filter size", [3, 5, 7, 9], key="cfg_kernel")
        with st.expander("Light and detail", expanded=True):
            st.slider("Gamma", 0.2, 4.0, step=0.1, key="cfg_gamma", help="Above 1 brightens; below 1 darkens. 1 leaves brightness unchanged.")
            st.checkbox("Local contrast (CLAHE)", key="cfg_clahe")
            st.slider("CLAHE strength", 1.0, 8.0, step=0.5, key="cfg_clip_limit", disabled=not st.session_state["cfg_clahe"])
            st.slider("Sharpening", 0.0, 2.0, step=0.1, key="cfg_sharpen")
        with st.expander("Edges and shapes"):
            st.slider("Canny lower threshold", 0, 250, key="cfg_canny_low")
            st.slider("Canny upper threshold", 1, 255, key="cfg_canny_high")
            st.selectbox("Threshold method", ["Otsu", "Adaptive", "Fixed"], key="cfg_threshold_mode")
            st.slider("Binary threshold", 0, 255, key="cfg_threshold_value", disabled=st.session_state["cfg_threshold_mode"] != "Fixed")
            st.selectbox("Morphology", ["Off", "Open", "Close", "Open + close"], key="cfg_morphology")
            st.select_slider("Morphology size", [3, 5, 7, 9], key="cfg_morph_kernel")
            st.slider("Minimum line length (px)", 5, 300, key="cfg_line_length")
        with st.expander("Colour masks"):
            st.caption("Masks use the original colour frame. Hue references: red 0, amber 20, green 60.")
            st.slider("Hue centre", 0, 179, key="cfg_hue_center")
            st.slider("Hue tolerance", 1, 45, key="cfg_hue_tolerance")
            st.slider("Minimum saturation", 0, 255, key="cfg_saturation_min")
            st.slider("Minimum value", 0, 255, key="cfg_value_min")
        with st.expander("Scene changes"):
            st.slider("Scene-change sensitivity threshold", 0.05, 1.0, step=0.05, key="cfg_scene_threshold")
            st.caption("Lower thresholds report more possible changes. Lighting changes may also trigger this indicator.")
        st.divider()
        st.caption("Local IVP + experimental AI processing. AI results need review; unresolved scene context is reported explicitly.")
    try:
        return Settings(**{name: st.session_state["cfg_" + name] for name in Settings.__dataclass_fields__})
    except ValueError as exc:
        st.error(str(exc))
        st.stop()


def download_links(run):
    labels = {"processed.png": "Processed image", "detections.png": "Object detection preview", "processed.mp4": "Processed video", "report.json": "Settings + report",
              "masks.zip": "Selected masks", "measurements.csv": "Frame measurements", "scene_changes.csv": "Scene changes",
              "coordinates.json": "Coordinate mapping", "detections.jsonl": "AI frame decisions", "events.jsonl": "AI events", "evidence.zip": "Event evidence images", "scene_features.zip": "Scene masks + geometry"}
    cols = st.columns(3)
    count = 0
    for name, label in labels.items():
        path = Path(run) / name
        if path.is_file():
            with cols[count % 3]:
                st.link_button("↓ " + label, file_server().url(path, download=True), width="stretch")
            count += 1


def export_image(path, result, settings, masks, stamp, kind):
    run = new_run()
    (run / "processed.png").write_bytes(png_bytes(result.color_rgb))
    with zipfile.ZipFile(run / "masks.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in masks:
            archive.writestr(name.replace(" ", "_") + ".png", png_bytes(result.features[name]))
    report = {"schema_version": 1, "kind": kind, "source": path.name, "timestamp_seconds": stamp,
              "settings": settings.to_dict(), "measurements": result.measurements, "candidates": result.candidates,
              "source_size": result.source_size, "processed_size": [result.color_rgb.shape[1], result.color_rgb.shape[0]],
              "transform_to_source_pixel_centres": result.transform_to_source.tolist(),
              "source_orientation": "Display-oriented RGB; EXIF/display rotation already applied.",
              "selected_masks": masks, "created_at": now()}
    write_json(run / "report.json", report)
    write_json(run / "status.json", {"state": "complete", "progress": 1, "message": "Image export ready.", "updated_at": now()})
    return run


@st.fragment(run_every="1s")
def job_panel():
    run_value = st.session_state.get("video_run")
    if not run_value:
        return
    run = Path(run_value)
    status = refreshed_status(run)
    state = status.get("state")
    st.markdown("#### Processing job")
    st.progress(float(status.get("progress", 0)), text=status.get("message", state))
    if state in ("queued", "running", "encoding"):
        st.caption(f"{status.get('frames', 0):,} frames · {status.get('timestamp', 0):.1f}s processed · {status.get('fps', 0):.1f} frames/sec")
        if st.button("Cancel processing", key="cancel_active", disabled=(run / "cancel.request").exists()):
            cancel_job(run)
            st.info("Cancellation requested. The worker will stop after its current operation.")
    elif state == "complete":
        st.success("Results ready. Downloads are streamed from disk.")
        if (run / "processed.mp4").exists():
            st.video(file_server().url(run / "processed.mp4"))
        elif (run / "processed.png").exists():
            if (run / "detections.png").exists():
                detection_view, violation_view = st.tabs(["Detected objects", "Reported violations"])
                with detection_view:
                    st.image(str(run / "detections.png"), caption="Cyan: model detections and scores; these are not violation decisions", width="stretch")
                with violation_view:
                    st.image(str(run / "processed.png"), caption="Green: reported violation events", width="stretch")
            else:
                st.image(str(run / "processed.png"), width="stretch")
            records = run / "detections.jsonl"
            if records.exists():
                with records.open(encoding="utf-8") as stream:
                    line = stream.readline()
                if line.strip():
                    frame = json.loads(line)
                    with st.expander("Detected objects and rule decisions"):
                        st.dataframe([{"Object": d["label"], "Model score": round(d["confidence"], 3), "Box": d["box"]}
                                      for d in frame.get("detections", [])], hide_index=True)
                        st.dataframe([{"Rule": d["rule"], "Result": d["verdict"], "Reason": d["reason"], "Vehicle box": d.get("box")}
                                      for d in frame.get("decisions", [])], hide_index=True)
        report_path = run / "report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("ai"):
                st.write("Events by rule", report["ai"]["events_by_rule"])
                with st.expander("AI assessment coverage and limitations"):
                    st.json(report["ai"])
                scene_root = run / "scene_features"
                scene_folders = sorted(p for p in scene_root.iterdir() if p.is_dir()) if scene_root.exists() else []
                if scene_folders:
                    with st.expander("Inspect AI scene features"):
                        selected_scene = st.selectbox("Scene snapshot", [p.name for p in scene_folders], key="scene_" + run.name)
                        scene_folder = scene_root / selected_scene
                        mask_columns = st.columns(3)
                        for column, name, label in zip(mask_columns, ["road", "sidewalk", "white_road_regions"], ["Road segmentation", "Sidewalk segmentation", "White road regions · IVP"]):
                            mask_path = scene_folder / (name + ".png")
                            if mask_path.exists():
                                column.image(str(mask_path), caption=label, width="stretch")
                        scene_file = scene_folder / "scene.json"
                        if scene_file.exists():
                            scene_data = json.loads(scene_file.read_text(encoding="utf-8"))
                            signs = scene_data.get("sign_observations", [])
                            if signs:
                                st.dataframe([{"Sign": sign.get("label"), "Assessment": sign.get("status"),
                                               "Located by": sign.get("proposal_source"), "Reason": sign.get("reason")} for sign in signs], hide_index=True)
                            st.caption("These are intermediate observations. They do not establish which road approach a sign or signal controls.")
        download_links(run)
    elif state in ("failed", "interrupted"):
        st.error(status.get("message", "Job failed."))
        st.caption(f"Diagnostic log: {run / 'worker.log'}")
    elif state == "cancelled":
        st.info(status["message"])


settings = control_panel()
st.markdown('<p class="eyebrow">TRAFFIC LAB / IMAGE & VIDEO PROCESSING</p>', unsafe_allow_html=True)
st.title("Traffic Lab · IVP + AI")
st.markdown('<p class="step">Upload → Preview → Adjust → Compare → Export</p>', unsafe_allow_html=True)
demo_tab, workspace_tab, history_tab = st.tabs(["Classroom demo", "Workspace", "Saved runs"])

with workspace_tab:
    available_samples = [name for name, filename in SAMPLES.items() if filename is None or (ROOT / "demo" / filename).is_file()]
    sample = st.selectbox("Bundled demo sample", available_samples, key="demo_sample")
    sample_path = ROOT / "demo" / SAMPLES[sample] if SAMPLES[sample] else None
    upload = st.file_uploader("Traffic image or video", type=["jpg", "jpeg", "png", "mp4", "mov", "avi"], help="Up to 1 GB. Originals are saved locally and left unchanged.")
    if upload is None and sample_path is None:
        st.info("Drop a traffic image or video above to begin. Start with Original, then adjust the processing controls.")
        left, middle, right = st.columns(3)
        with left:
            st.markdown("#### 01 / Enhance")
            st.write("Reduce noise, adjust light and reveal local contrast.")
        with middle:
            st.markdown("#### 02 / Inspect")
            st.write("Compare frames, histograms, colour masks and road-feature candidates.")
        with right:
            st.markdown("#### 03 / Export")
            st.write("Save processed media, selected masks and reproducible settings.")
    else:
        try:
            upload_id = getattr(upload, "file_id", upload.name) if upload is not None else "demo_" + sample_path.name
            if st.session_state.get("upload_id") != upload_id:
                path = save_upload(upload, ROOT / "uploads") if upload is not None else sample_path
                st.session_state["upload_path"] = str(path)
                st.session_state["upload_id"] = upload_id
                st.session_state.pop("image_export", None)
            path = Path(st.session_state["upload_path"])
            is_video = path.suffix.lower() in (".mp4", ".mov", ".avi")
            stamp = 0.0
            if is_video:
                info = probe_video(path)
                st.caption(f"{path.name} · {info['width']} × {info['height']} · {info['duration']:.2f}s · {info['fps']:.2f} fps average · {'Audio present' if info['has_audio'] else 'No audio'}")
                requested = st.slider("Preview time (seconds)", 0.0, max(0.01, info["duration"] - 0.001), 0.0, step=0.01, key="time_" + upload_id)
                rgb, stamp = cached_preview(str(path), requested)
                st.caption(f"Both panes show the same decoded frame at {stamp:.3f}s.")
            else:
                rgb = cached_image(str(path))
                st.caption(f"{path.name} · {rgb.shape[1]} × {rgb.shape[0]} · RGB preview · {path.stat().st_size / 1048576:.2f} MB")
            result = process_frame(rgb, settings, stamp)
            compare, features, stages, measurements, ai_tab = st.tabs(["Before / after", "Feature views", "Processing stages", "Quality + histograms", "AI analysis"])
            with ai_tab:
                st.write("Analyse road users, riders, and traffic-rule evidence using local models. The current IVP settings are applied before detection.")
                st.warning("Experimental implementation: model and rider-association accuracy are not yet validated. Automatic legal scene association is still being developed. Unresolved rules return cannot assess.")
                st.caption("Green boxes mark reported violation events. Detection alone is not a violation. Video motion checks do not run on single images. First use downloads model weights.")
                if st.button("Analyse entire video with AI" if is_video else "Analyse image with AI", type="primary"):
                    try:
                        ai_info = info if is_video else {"kind": "image", "width": rgb.shape[1], "height": rgb.shape[0]}
                        run = start_video(path, ai_info, settings, [], ai=True)
                        st.session_state["video_run"] = str(run)
                    except (RuntimeError, OSError) as exc:
                        st.error(str(exc))
            with compare:
                before_col, after_col = st.columns(2)
                before_col.image(rgb, caption="Original · orientation corrected", width="stretch")
                after_col.image(result.color_rgb, caption="Processed colour frame", width="stretch")
                st.caption("Colour enhancement is separate from feature masks. The Original preset preserves decoded RGB pixels when no resize is selected.")
            with features:
                choice = st.selectbox("Feature view", list(result.features), index=list(result.features).index("Road candidates"))
                st.image(result.features[choice], caption=choice, width="stretch", clamp=True)
                st.warning("Road overlays are geometric candidates, not detected crossings, stop lines or violations. Colour masks do not identify traffic signals.")
                st.caption(f"{len(result.candidates['stripe_boxes'])} stripe candidates · {len(result.candidates['horizontal_segments'])} near-horizontal segments. Amber = stripe shapes; blue = line segments.")
            with stages:
                stage_cols = st.columns(2)
                for index, (name, array) in enumerate(result.stages.items()):
                    stage_cols[index % 2].image(array, caption=name, width="stretch")
            with measurements:
                before = result.measurements["original"]
                after = result.measurements["processed"]
                cols = st.columns(3)
                cols[0].metric("Brightness / 255", f"{after['brightness']:.1f}", f"{after['brightness'] - before['brightness']:+.1f}", delta_color="off")
                cols[1].metric("Contrast (std. dev.)", f"{after['contrast']:.1f}", f"{after['contrast'] - before['contrast']:+.1f}", delta_color="off")
                cols[2].metric("Edge detail (Laplacian)", f"{after['laplacian_variance']:.1f}", f"{after['laplacian_variance'] - before['laplacian_variance']:+.1f}", delta_color="off")
                st.caption("Measurements compare equal-sized frames. Blur indicators depend on resolution and scene texture; higher values do not necessarily mean better footage.")
                for label, values in (("Original", before), ("Processed", after)):
                    st.write(f"**{label}:** " + (" · ".join(values["flags"]) or "No heuristic quality flags."))
                data = pd.DataFrame({"Original": histogram(result.stages["Prepared"]), "Processed": histogram(result.color_rgb)})
                st.line_chart(data, x_label="Luminance (0–255)", y_label="Pixels", color=["#94a3b8", "#38bdf8"])
                with st.expander("Measurements and coordinate mapping"):
                    st.json({**result.measurements, "transform_to_source_pixel_centres": result.transform_to_source.tolist()})
            st.divider()
            st.subheader("Export")
            selected = st.multiselect("Include feature masks", list(result.features), default=["Edges", "Colour mask", "White marking mask"], help="Image exports include these PNG views. Video exports sample them about once per second to keep output manageable.")
            if st.button("Save this frame" if is_video else "Save processed image", type="primary"):
                st.session_state["image_export"] = str(export_image(path, result, settings, selected, stamp, "video_frame" if is_video else "image"))
            if st.session_state.get("image_export"):
                st.caption("Saved snapshot below; further adjustments require another save.")
                download_links(st.session_state["image_export"])
            if is_video:
                st.caption("Full video processing uses these fixed settings. Original frame timing and the first audio track are retained. Selected masks are exported as sampled PNGs.")
                if st.button("Process entire video", type="primary"):
                    try:
                        run = start_video(path, info, settings, selected)
                        st.session_state["video_run"] = str(run)
                    except RuntimeError as exc:
                        st.error(str(exc))
        except (MediaError, ValueError, OSError) as exc:
            st.error(str(exc))
    job_panel()

with history_tab:
    if st.button("Refresh saved runs"):
        st.rerun()
    runs = history()
    if not runs:
        st.caption("Saved images and video jobs will appear here.")
    for status_path in runs:
        run = status_path.parent
        status = refreshed_status(run)
        with st.expander(f"{run.name} · {status.get('state', 'unknown')}"):
            st.write(status.get("message", ""))
            if status.get("state") == "complete":
                if st.button("Inspect saved result", key="inspect_" + run.name):
                    st.session_state["video_run"] = str(run)
                    st.info("Open Workspace to inspect this result below the input controls.")
                download_links(run)
                if (run / "report.json").exists():
                    st.json(json.loads((run / "report.json").read_text(encoding="utf-8")), expanded=False)
            elif status.get("state") in ("queued", "running", "encoding"):
                if st.button("Show video job", key="show_" + run.name):
                    st.session_state["video_run"] = str(run)
                    st.rerun()
                if st.button("Cancel job", key="cancel_" + run.name):
                    cancel_job(run)
                    st.rerun()
            else:
                st.caption("Partial results are not offered as completed exports. Originals remain available in uploads.")

with demo_tab:
    render_demo(file_server(), download_links)
