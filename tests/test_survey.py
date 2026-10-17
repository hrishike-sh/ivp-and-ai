import io
import json
import zipfile
import urllib.request

import numpy as np
import pytest
from PIL import Image

from ivp.survey import survey
from tests.test_web_server import server, request


def stripes():
    image = np.full((120, 200, 3), 50, np.uint8)
    image[30:40, 20:80] = 240
    image[60:70, 20:80] = [240, 220, 0]
    return image


def test_known_geometry_coverage_and_source_coordinates():
    rgb = stripes()
    original = rgb.copy()
    report, images = survey(rgb, [0, 0, 1, 1], np.diag([2, 2, 1]))
    assert report['summary']['fragments'] == 2
    assert report['summary']['candidate_area_px'] == 1200
    assert report['summary']['coverage_percent'] == 5
    assert report['summary']['threshold_mask_iou'] == 1
    assert report['fragments'][0]['source_centre_x'] == 99
    assert report['fragments'][0]['long_side_px'] == 59
    assert report['fragments'][0]['orientation_deg_clockwise_from_right'] == 0
    assert not report['fragments'][0]['touches_roi_boundary']
    assert set(np.unique(images['cleaned-mask'])) == {0, 255}
    assert np.array_equal(original, rgb)


def test_crop_excludes_second_fragment_and_reports_truncation():
    report, _ = survey(stripes(), [.2, .1, .6, .4])
    assert report['summary']['fragments'] == 1
    assert report['fragments'][0]['touches_roi_boundary']
    assert report['fragments'][0]['bbox_x'] == 40


def test_blank_and_threshold_sensitive_input():
    empty, _ = survey(np.zeros((60, 80, 3), np.uint8), [0, 0, 1, 1])
    assert empty['summary']['fragments'] == 0
    assert empty['summary']['threshold_mask_iou'] is None
    image = np.full((60, 80, 3), 50, np.uint8)
    image[20:30, 20:50] = 105
    report, _ = survey(image, [0, 0, 1, 1])
    assert report['summary']['threshold_mask_iou'] == 0
    assert any('substantially' in s for s in report['limitations'])


def test_uniform_bright_surface_is_withheld():
    report, _ = survey(np.full((60, 80, 3), 240, np.uint8), [0, 0, 1, 1])
    assert report['summary']['candidate_area_px'] == 0
    assert any('withheld' in s for s in report['limitations'])


@pytest.mark.parametrize('roi', [None, [0, 0, 1], [0, 0, float('nan'), 1],
                               [0, 0, True, 1], [0, 0, 2, 1], [.8, .8, .2, .2], [0, 0, .01, .01]])
def test_invalid_selection(roi):
    with pytest.raises(ValueError):
        survey(stripes(), roi)


def test_survey_api_exports_original_measurements_without_enhancement(server):
    buffer = io.BytesIO()
    Image.fromarray(stripes()).save(buffer, 'PNG')
    media = request(server, '/api/upload?name=survey.png', raw=buffer.getvalue())
    run = request(server, '/api/survey', {'media': media['id'], 'rectangle': [0, 0, 1, 1],
                                       'settings': {'gamma': 4, 'saturation': 0}, 'mode': 'manual'})
    assert run['report']['summary']['coverage_percent'] == 5
    assert run['report']['uses_ai'] is False
    assert run['report']['settings']['gamma'] == 1
    assert run['status']['state'] == 'complete'
    url = next(d['url'] for d in run['downloads'] if d['name'] == 'survey-evidence.zip')
    with urllib.request.urlopen(url) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
            assert len(archive.namelist()) == 8
            assert json.loads(archive.read('report.json'))['summary']['fragments'] == 2
            assert len(archive.read('fragments.csv').decode().splitlines()) == 3
            assert Image.open(archive.open('annotated-survey.png')).size == (200, 120)
