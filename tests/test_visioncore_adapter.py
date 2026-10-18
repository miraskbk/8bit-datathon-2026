import base64
import io
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from app.visioncore_adapter import VisionCoreAdapter
from app.config import Settings
from app.service import InferenceService


def payload():
    data=io.BytesIO();Image.new('RGB',(8,8)).save(data,format='JPEG')
    return {'verdict':'violation','violations':[{'type':'Possible event','timecode_sec':4.2,
        'description':'Visible supporting observation','evidence_frames':[{'timestamp_sec':4.2,
        'image_base64':base64.b64encode(data.getvalue()).decode()}]}],
        'explain':[{'code':'L_workstation_unlocked','score':.7,'refs':[{'doc':'Requirements 53',
            'label':'Point 26','url':'https://adilet.zan.kz/rus/docs/V2600038336'}]}],
        'meta':{'scene':{'desk':True,'door':True,'safe':True,'safe_classifier':'ok','money_classifier':'ok','vlm':'ok'}}}


def test_full_pipeline_result_matches_8bit_ui_schema():
    result=VisionCoreAdapter.convert(payload())
    assert result.verdict=='violation' and len(result.violations)==1
    event=result.violations[0]
    assert event.timecode_sec==4.2 and event.rule.section=='Point 26'
    assert len(event.evidence_frames)==1 and base64.b64decode(event.evidence_frames[0].image_base64).startswith(b'\xff\xd8')
    assert result.metadata['pipeline']=='visioncore-integrated-v1' and result.metadata['local_only']


@pytest.mark.parametrize('component',['safe_classifier','money_classifier','vlm'])
def test_inference_failure_cannot_become_clean_result(component):
    data=payload();data['violations']=[];data['explain']=[];data['verdict']='no_violation'
    data['meta']['scene'][component]='error'
    with pytest.raises(RuntimeError,match='checks failed'):
        VisionCoreAdapter.convert(data)


def test_missing_evidence_or_source_is_a_failure():
    data=payload();data['violations'][0]['evidence_frames']=[]
    with pytest.raises(ValueError,match='evidence'):
        VisionCoreAdapter.convert(data)
    data=payload();data['explain'][0]['refs']=[]
    with pytest.raises(ValueError,match='source'):
        VisionCoreAdapter.convert(data)


def test_website_service_invokes_visioncore_path(tmp_path,monkeypatch):
    calls=[]
    class Adapter:
        def __init__(self,config):calls.append('load')
        def analyze(self,path):calls.append(path);return VisionCoreAdapter.convert(payload())
    monkeypatch.setattr('app.visioncore_adapter.VisionCoreAdapter',Adapter)
    config=Settings(pipeline='visioncore')
    service=InferenceService(config)
    source=tmp_path/'input.mov'
    first=service.analyze(source);second=service.analyze(source)
    assert service.loaded and first.verdict==second.verdict=='violation'
    assert calls==['load',source,source]


def test_adapter_qualifies_authorization_instead_of_claiming_hidden_fact():
    data=payload();data['explain'][0]['code']='E_unauthorized_person'
    data['violations'][0]['description']='Unsupported original claim'
    result=VisionCoreAdapter.convert(data)
    assert 'Unsupported original claim' not in result.violations[0].description
    assert 'полномочия' in result.violations[0].description
