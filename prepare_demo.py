import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from ivp.media import load_image, preview_frame, probe_video, write_json


ROOT = Path(__file__).resolve().parent


def main():
    folder = ROOT / "demo"
    folder.mkdir(exist_ok=True)
    rgb = load_image(ROOT / "temp/qa/traffic_bus.jpg")
    Image.fromarray(rgb).save(folder / "street.jpg")
    dark = np.round((rgb.astype(float) / 255) ** 2.2 * 255).astype(np.uint8)
    Image.fromarray(dark).save(folder / "low_light.png")
    noise = np.random.default_rng(42).normal(0, 22, rgb.shape)
    Image.fromarray(np.clip(rgb.astype(float) + noise, 0, 255).astype(np.uint8)).save(folder / "noisy.png")
    shutil.copy2(ROOT / "temp/qa/bus_static.mp4", folder / "sample_video.mp4")
    Image.fromarray(load_image(ROOT / "temp/qa/zebra_crossing.jpg")).resize((540, 960)).save(folder / "crossing.jpg")
    shutil.copy2(ROOT / "temp/qa/signs/00052.png", folder / "no_vehicles.png")
    runs = {"street": "20260909-215526-a0a70f65", "crossing": "20260909-143842-9b52a43d", "sign": "20260909-213746-6af376d8"}
    for name, run_id in runs.items():
        shutil.copytree(ROOT / "runs" / run_id, folder / "results" / name, dirs_exist_ok=True)
    run = folder / "results/street"
    record = json.loads((run / "detections.jsonl").read_text().splitlines()[0])
    frame, _ = preview_frame(folder / "sample_video.mp4", probe_video(folder / "sample_video.mp4"), 0)
    overlay = Image.fromarray(frame)
    draw = ImageDraw.Draw(overlay)
    for detection in record["detections"]:
        if detection["model"] != "yolo11s":
            continue
        box = detection["box"]
        draw.rectangle(box, outline="#00c8ff", width=3)
        label = f"{detection['label']} #{detection['track_id']}  {detection['confidence']:.2f}"
        x, y = max(0, box[0]), max(0, box[1] - 14)
        draw.rectangle((x, y, min(frame.shape[1], x + len(label) * 6 + 8), y + 14), fill="#102838")
        draw.text((x + 3, y + 1), label, fill="white")
    overlay.save(folder / "detections.png")
    write_json(folder / "manifest.json", {"runs": runs, "note": "Saved genuine model outputs. Cyan overlay visualises recorded road-user detections, not violations. Video is a still-photo test clip with generated audio."})
    print("Classroom demo assets prepared at", folder)


if __name__ == "__main__":
    main()
