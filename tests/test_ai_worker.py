import json

import numpy as np
import pytest
from PIL import Image

from ivp.media import load_image, write_json
from ivp.pipeline import Settings
from traffic_ai.contracts import Detection, FrameAnalysis
from traffic_ai.worker import process_run


class FakeAnalyzer:
    def __init__(self, status, cancel):
        cancel()
        status("Test model")

    def analyze(self, result, original, video, scene_change):
        assert not video
        assert original.shape == (80, 120, 3)
        assert original[0, 0].tolist() == [80, 80, 80]
        output = result.color_rgb.copy()
        output[5:10, 5:10] = [0, 255, 0]
        return output, FrameAnalysis(0, [Detection("car", .9, (15, 15, 35, 35))], []), []

    def summary(self):
        return {"events_by_rule": {}, "assessment_counts": {}, "test_double": True}


@pytest.mark.parametrize("source_mode", ["rgb8", "gray16"])
def test_image_worker_writes_reopenable_media_and_mapping(tmp_path, monkeypatch, source_mode):
    from traffic_ai import worker

    monkeypatch.setattr(worker, "Analyzer", FakeAnalyzer)
    source = tmp_path / "original.png"
    pixels = np.full((80, 120), 80 * 257, np.uint16) if source_mode == "gray16" else np.full((80, 120, 3), 80, np.uint8)
    Image.fromarray(pixels).save(source)
    before = source.read_bytes()
    run = tmp_path / "run"
    run.mkdir()
    write_json(run / "request.json", {"source": str(source), "info": {"kind": "image"}, "settings": Settings(max_width=60).to_dict()})
    process_run(run)
    assert json.loads((run / "status.json").read_text())["state"] == "complete"
    output = load_image(run / "processed.png")
    assert output.shape == (40, 60, 3)
    assert output[7, 7].tolist() == [0, 255, 0]
    preview = load_image(run / "detections.png")
    assert preview[25, 15].tolist() == [0, 200, 255]
    assert preview[7, 7].tolist() == [80, 80, 80]
    assert output[25, 15].tolist() == [80, 80, 80]
    coordinates = json.loads((run / "coordinates.json").read_text())
    assert coordinates["transform_to_source_pixel_centres"] == [[2., 0., .5], [0., 2., .5], [0., 0., 1.]]
    assert source.read_bytes() == before
    assert len((run / "detections.jsonl").read_text().splitlines()) == 1


def test_cancel_before_model_loading(tmp_path, monkeypatch):
    from traffic_ai import worker

    monkeypatch.setattr(worker, "Analyzer", lambda **kwargs: (_ for _ in ()).throw(AssertionError("Should not load")))
    write_json(tmp_path / "request.json", {})
    (tmp_path / "cancel.request").touch()
    process_run(tmp_path)
    assert json.loads((tmp_path / "status.json").read_text())["state"] == "cancelled"
