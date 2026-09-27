import csv
import json
import subprocess
import zipfile
from pathlib import Path

import av
import numpy as np
import pytest

from ivp.jobs import read_status
from ivp.media import MediaError, hidden_process_options, preview_frame, probe_video, tool_path, video_frames, write_json
from ivp.pipeline import Settings
from ivp.worker import process_video


def ffmpeg(*args):
    subprocess.run([tool_path("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True, **hidden_process_options())


def request_run(tmp_path, source, settings=None, masks=None):
    run = tmp_path / ("run_" + str(len(list(tmp_path.glob("run_*")))))
    run.mkdir()
    write_json(run / "request.json", {"source": str(source), "info": probe_video(source),
                "settings": (settings or Settings()).to_dict(), "selected_masks": masks or []})
    return run


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=160x120:rate=12:duration=1.5", "-f", "lavfi", "-i", "sine=frequency=500:duration=1.5", "-c:v", "libx264", "-c:a", "aac", "-shortest", path)
    return path


def stamps(path):
    with av.open(str(path)) as container:
        return [float(frame.pts * frame.time_base) for frame in container.decode(video=0)]


def test_audio_timing_masks_and_output(source, tmp_path):
    run = request_run(tmp_path, source, Settings(gamma=1.2), ["Edges"])
    process_video(run)
    assert read_status(run)["state"] == "complete"
    out = run / "processed.mp4"
    info = probe_video(out)
    assert info["has_audio"]
    assert info["codec"] == "h264"
    assert info["duration"] == pytest.approx(probe_video(source)["duration"], abs=0.09)
    assert stamps(out) == pytest.approx(stamps(source), abs=2 / 90000)
    with av.open(str(out)) as container:
        audio = list(container.decode(audio=0))
        assert sum(frame.samples for frame in audio) > 40000
    with zipfile.ZipFile(run / "masks.zip") as archive:
        assert len(archive.namelist()) == 2
    rows = list(csv.DictReader((run / "measurements.csv").open()))
    assert len(rows) == 18


def test_ai_frame_hook_preserves_audio_and_presentation_times(source, tmp_path):
    run = request_run(tmp_path, source)
    calls = []

    def hook(result, original, index, distance):
        calls.append((index, result.timestamp))
        assert np.array_equal(result.color_rgb, original)
        output = result.color_rgb.copy()
        output[10:30, 10:30] = [0, 255, 0]
        return output

    process_video(run, frame_hook=hook, final_hook=lambda: {"frames": len(calls)})
    out = run / "processed.mp4"
    assert probe_video(out)["has_audio"]
    assert stamps(out) == pytest.approx(stamps(source), abs=2 / 90000)
    frame, _ = preview_frame(out, probe_video(out), 0)
    assert frame[20, 20, 1] > 240 and frame[20, 20, 0] < 20
    assert json.loads((run / "report.json").read_text())["ai"]["frames"] == 18


def test_variable_frame_rate_is_not_flattened(tmp_path):
    source = tmp_path / "variable.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=160x120:rate=25:duration=1", "-vf", "select='eq(mod(n,3),0)+eq(n,1)'", "-fps_mode", "vfr", "-c:v", "libx264", source)
    run = request_run(tmp_path, source)
    process_video(run)
    input_times, output_times = stamps(source), stamps(run / "processed.mp4")
    assert len(set(round(x, 3) for x in np.diff(input_times))) > 1
    assert output_times == pytest.approx(input_times, abs=2 / 90000)
    decoded = list(video_frames(source, probe_video(source)))
    actual_endpoint = decoded[-1][1] + decoded[-1][2]
    assert probe_video(run / "processed.mp4")["duration"] == pytest.approx(actual_endpoint, abs=0.001)
    assert not probe_video(run / "processed.mp4")["has_audio"]


def test_preview_and_source_unchanged(source, tmp_path):
    import hashlib
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    info = probe_video(source)
    rgb, timestamp = preview_frame(source, info, 0.6)
    assert rgb.shape == (120, 160, 3)
    assert 0.6 <= timestamp < 0.7
    run = request_run(tmp_path, source)
    process_video(run)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original


def test_cancel_before_start(source, tmp_path):
    run = request_run(tmp_path, source)
    (run / "cancel.request").touch()
    process_video(run)
    assert read_status(run)["state"] == "cancelled"
    assert not (run / "processed.mp4").exists()


def test_broken_video_and_missing_ffmpeg(tmp_path, source, monkeypatch):
    bad = tmp_path / "broken.mp4"
    bad.write_bytes(b"invalid")
    with pytest.raises(MediaError):
        probe_video(bad)
    run = request_run(tmp_path, source)
    monkeypatch.setenv("PATH", "")
    with pytest.raises(MediaError, match="ffmpeg is missing"):
        process_video(run)
    assert read_status(run)["state"] == "failed"


def test_rotation_metadata_applied_once(source, tmp_path):
    rotated = tmp_path / "rotated.mp4"
    ffmpeg("-display_rotation", "90", "-i", source, "-c", "copy", rotated)
    info = probe_video(rotated)
    assert info["width"] == 120
    assert info["height"] == 160
    preview, _ = preview_frame(rotated, info, 0)
    run = request_run(tmp_path, rotated)
    process_video(run)
    result_info = probe_video(run / "processed.mp4")
    assert result_info["rotation"] == 0
    output, _ = preview_frame(run / "processed.mp4", result_info, 0)
    assert output.shape == preview.shape
    assert np.abs(output.astype(float) - preview.astype(float)).mean() < 8


def test_odd_resize_padding(source, tmp_path):
    run = request_run(tmp_path, source, Settings(max_width=101))
    process_video(run)
    assert probe_video(run / "processed.mp4")["width"] == 102
    coords = json.loads((run / "coordinates.json").read_text())
    assert coords["processed_size"] == [101, 76]
    assert coords["encoded_size"] == [102, 76]


def test_cancel_during_processing(source, tmp_path, monkeypatch):
    import ivp.worker as worker
    run = request_run(tmp_path, source)
    original = worker.process_frame
    calls = []

    def process_then_cancel(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(1)
        if len(calls) == 3:
            (run / "cancel.request").touch()
        return result

    monkeypatch.setattr(worker, "process_frame", process_then_cancel)
    process_video(run)
    assert len(calls) == 3
    assert read_status(run)["state"] == "cancelled"
    assert not (run / "processed.mp4").exists()


def first_audio_time(path):
    with av.open(str(path)) as container:
        frame = next(container.decode(audio=0))
        return float(frame.pts * frame.time_base)


def test_delayed_audio_keeps_offset(tmp_path):
    source = tmp_path / "delayed_audio.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=160x120:rate=10:duration=2", "-itsoffset", "0.4",
           "-f", "lavfi", "-i", "sine=frequency=600:duration=1.3", "-c:v", "libx264", "-c:a", "aac", source)
    run = request_run(tmp_path, source)
    process_video(run)
    assert first_audio_time(run / "processed.mp4") == pytest.approx(first_audio_time(source), abs=0.05)


def test_nonzero_video_start_normalised(tmp_path):
    source = tmp_path / "nonzero.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=160x120:rate=10:duration=1.5", "-f", "lavfi", "-i",
           "sine=frequency=600:duration=1.5", "-c:v", "libx264", "-c:a", "aac", "-output_ts_offset", "2", source)
    source_times = stamps(source)
    assert source_times[0] >= 1.9
    run = request_run(tmp_path, source)
    process_video(run)
    assert stamps(run / "processed.mp4") == pytest.approx([stamp - source_times[0] for stamp in source_times], abs=2 / 90000)
    assert first_audio_time(run / "processed.mp4") == pytest.approx(0, abs=0.05)


def test_encoder_failure_exposes_failed_status(source, tmp_path, monkeypatch):
    import ivp.worker as worker
    run = request_run(tmp_path, source)

    def fail_encoder(*args, **kwargs):
        raise RuntimeError("Deliberate encoder failure")

    monkeypatch.setattr(worker.av, "open", fail_encoder)
    with pytest.raises(RuntimeError, match="encoder failure"):
        process_video(run)
    assert read_status(run)["state"] == "failed"
