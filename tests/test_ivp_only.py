"""The distribution runs with image libraries only and exposes no model jobs."""
import urllib.error
import pytest
from ivp.motion import MotionAnalyzer
from tests.test_web_server import server, request
from tests.test_video import source

def test_config_has_no_samples_or_model_install_paths(server):
    config=request(server,'/api/config')
    assert config['scope']=='ivp-only'
    assert set(config)=={'defaults','presets','scope'}

@pytest.mark.parametrize('route',['/api/helmet','/api/zebra','/api/review','/api/evidence-review','/api/sample'])
def test_removed_workflows_are_not_callable(server,route):
    with pytest.raises(urllib.error.HTTPError) as error:request(server,route,{})
    assert error.value.code==400

def test_detector_tracking_is_rejected():
    with pytest.raises(ValueError,match='classical IVP'):
        MotionAnalyzer(tracking_mode='vehicles')

def test_video_api_rejects_ai_request(server,source,monkeypatch):
    import web_server
    media=server.lab.register(source)
    monkeypatch.setattr(web_server,'start_video',lambda *a,**k:pytest.fail('must not launch'))
    with pytest.raises(urllib.error.HTTPError) as error:
        request(server,'/api/job',{'media':media['id'],'ai':True})
    assert error.value.code==400
