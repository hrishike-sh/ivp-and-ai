import json

import streamlit as st

from ivp.jobs import ROOT


SAMPLES = {"Upload my own file": None, "Indian motorcycles · daylight": "indian_riders.png",
           "Indian street · real night photo": "indian_night.png", "Low-light street · simulated darkness": "low_light.png",
           "Noisy street · simulated noise": "noisy.png", "Original street": "street.jpg",
           "Real zebra crossing": "crossing.jpg", "No-vehicles sign crop": "no_vehicles.png",
           "4-second video · still photo + test audio": "sample_video.mp4"}


def render_demo(server, downloads):
    folder = ROOT / "demo"
    st.subheader("Classroom progress demo")
    st.write("A working local pipeline: enhance footage with IVP, inspect AI observations, and export results with their evidence.")
    if not (folder / "manifest.json").exists():
        st.info("Run prepare_demo.py to prepare the bundled examples.")
        return
    st.info("For the live demonstration, open Workspace and choose a bundled sample. Saved AI examples below open immediately without model loading or internet.")
    st.markdown("**1. IVP live:** select the low-light sample → choose Low light in the sidebar → compare images, processing stages and histograms. Try the noisy sample with Noisy footage, then inspect edges and colour masks.")
    st.markdown("**2. AI observations:** inspect the genuine saved results below. Cyan boxes show detected objects; green boxes are reserved for reported violations.")
    example = st.selectbox("Saved AI example", ["Road users + video", "Crossing segmentation", "Traffic-sign recognition"], key="classroom_example")
    if example == "Road users + video":
        run = folder / "results/street"
        left, right = st.columns(2)
        left.image(str(folder / "detections.png"), caption="Actual YOLO detections and track IDs · cyan is not a violation", width="stretch")
        right.video(server.url(run / "processed.mp4"))
        right.write("40 frames · 4 seconds · H.264 + audio · preserved frame timestamps")
        right.caption("This clip repeats a street photograph with generated test audio. It demonstrates inference, tracking IDs and video export; it does not demonstrate driving behaviour.")
        record = json.loads((run / "detections.jsonl").read_text().splitlines()[0])
        st.dataframe([{"Object": d["label"], "Track ID": d["track_id"], "Model score": round(d["confidence"], 3)} for d in record["detections"] if d["model"] == "yolo11s"], hide_index=True)
        with st.expander("Why there are no green violation boxes"):
            st.write("No supported violation was established in this sample. People without helmets on a pavement are not automatically motorcycle rule breakers.")
            st.dataframe([{"Rule": d["rule"], "Result": d["verdict"], "Reason": d["reason"]} for d in record["decisions"]], hide_index=True)
    else:
        name = "crossing" if example == "Crossing segmentation" else "sign"
        run = folder / "results" / name
        scene = run / "scene_features/0001"
        left, right = st.columns(2)
        left.image(str(run / "processed.png"), caption="Input after processing", width="stretch")
        data = json.loads((scene / "scene.json").read_text())
        if name == "crossing":
            right.image(str(scene / "white_road_regions.png"), caption="IVP white regions constrained by AI road segmentation", width="stretch")
            right.write("The saved analysis refined one crossing candidate supported by five stripe regions.")
            st.caption("A candidate road feature is not a violation or a validated road boundary.")
        else:
            right.dataframe([{"Sign": s.get("label"), "Result": s.get("status"), "Located by": s.get("proposal_source")} for s in data.get("sign_observations", [])], hide_index=True)
            right.write("IVP colour and shape localisation → pretrained sign classification. Road applicability remains unresolved.")
    with st.expander("Download this saved result"):
        downloads(run)
    st.markdown("**3. Live AI:** in Workspace, select Original street, choose Original preset, open AI analysis and click Analyse image with AI. The installed local models run in the background.")
    st.caption("Current limits: nine rule checks exist, but full automatic scene interpretation and real-traffic accuracy are still being developed. Today’s demo shows implemented processing and model observations, not a validated enforcement system.")
    with st.expander("Sample sources and preparation"):
        st.markdown("Street photograph: [Ultralytics example](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/assets/bus.jpg). Crossing: [Vijayanrajapuram, CC BY-SA 4.0](https://commons.wikimedia.org/wiki/File:Zebra_crossing_line_kanhangad_01.jpg). Sign crop: [model author’s example](https://huggingface.co/spaces/bazyl/gtsrb/tree/main/examples). Low light and noise are deliberately simulated from the street photograph for controlled IVP demonstrations.")
