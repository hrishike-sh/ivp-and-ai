"""Real IVP-only encoder checks on generated, temporary media."""
import csv
import json
import zipfile
from PIL import Image
import pytest

from ivp.jobs import read_status
from ivp.motion_worker import run_motion
from ivp.media import probe_video, write_json
from tests.test_video import source, request_run, stamps

def motion_request(tmp_path,source):
    run=request_run(tmp_path,source)
    request=json.loads((run/'request.json').read_text())
    request['motion']={'tracking_mode':'ivp','rectangle':[.1,.1,.9,.9]}
    write_json(run/'request.json',request)
    return run

def test_motion_output_reopens_with_audio_timing_and_diagnostics(tmp_path,source):
    run=motion_request(tmp_path,source)
    run_motion(run)
    assert read_status(run)['state']=='complete'
    report=json.loads((run/'report.json').read_text())
    assert report['motion']['uses_ai'] is False
    assert report['motion']['speed']['unit']=='px/s'
    info=probe_video(run/'processed.mp4')
    assert info['has_audio'] and info['codec']=='h264'
    assert stamps(run/'processed.mp4')==pytest.approx(stamps(source),abs=2/90000)
    with (run/'motion-activity.csv').open() as stream:
        assert len(list(csv.DictReader(stream)))==18
    with zipfile.ZipFile(run/'motion-evidence.zip') as archive:
        assert 'motion-summary.json' in archive.namelist()
        assert 'coordinates.json' in archive.namelist()
        assert not any('incident' in name for name in archive.namelist())
        for name in archive.namelist():
            if name.endswith('.png'):
                with archive.open(name) as handle:Image.open(handle).load()

def test_cancelled_motion_run_never_publishes_complete_output(tmp_path,source):
    run=motion_request(tmp_path,source)
    (run/'cancel.request').touch()
    run_motion(run)
    assert read_status(run)['state']=='cancelled'
    assert not (run/'processed.mp4').exists()
    assert not (run/'report.json').exists()
    assert not (run/'motion-evidence.zip').exists()
