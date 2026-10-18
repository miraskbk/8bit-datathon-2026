"""Boundary and jury-schema checks using synthetic videos, never organizer data."""
import asyncio
import base64
import io
import time
import av
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.config import settings
from app.schemas import AnalysisResult


def movie(tmp_path):
    path = tmp_path / 'synthetic.mov'
    with av.open(str(path), 'w') as container:
        stream = container.add_stream('mpeg4', rate=30)
        stream.width = 64; stream.height = 32; stream.pix_fmt = 'yuv420p'
        for _ in range(4):
            frame = av.VideoFrame.from_ndarray(np.zeros((32, 64, 3), dtype=np.uint8), format='rgb24')
            for packet in stream.encode(frame): container.mux(packet)
        for packet in stream.encode(): container.mux(packet)
    return path.read_bytes()


def test_complete_positive_jury_response_and_evidence(tmp_path, monkeypatch):
    import app.main as main
    from app.jobs import JobManager
    data = io.BytesIO(); Image.new('RGB', (64, 32), 'white').save(data, 'JPEG')
    class Worker:
        loaded = ready = True
        def stop(self): pass
        def analyze(self, path, deadline):
            return {'verdict': 'violation', 'violations': [{
                'type': 'Synthetic API contract event', 'timecode_sec': 0.05,
                'description': 'Synthetic fixture only',
                'evidence_frames': [{'timestamp_sec': 0.05, 'image_base64': base64.b64encode(data.getvalue()).decode()}],
                'rule': {'document': 'Правила № 231', 'section': 'п. 20', 'url': 'https://adilet.zan.kz/rus/docs/V1900019680'}
            }]}
    monkeypatch.setattr(main, 'JobManager', lambda config: JobManager(config, Worker()))
    with TestClient(main.app) as client:
        assert client.get('/ready').status_code == 200
        headers = {'X-API-Key': settings.api_key}
        accepted = client.post('/api/v1/analyze', headers=headers, files={'file': ('test.MOV', movie(tmp_path))})
        assert accepted.status_code == 202
        for _ in range(100):
            result = client.get('/api/v1/jobs/' + accepted.json()['job_id'], headers=headers)
            if result.json()['status'] != 'processing': break
            time.sleep(.01)
        body = result.json()
        assert body['status'] == 'done' and body['verdict'] == 'violation'
        event = body['violations'][0]
        assert {'type', 'timecode_sec', 'description', 'evidence_frames', 'rule'} <= event.keys()
        assert 1 <= len(event['evidence_frames']) <= 3
        image = Image.open(io.BytesIO(base64.b64decode(event['evidence_frames'][0]['image_base64'], validate=True)))
        image.load(); assert image.format == 'JPEG' and image.size == (64, 32)
        assert result.headers['cache-control'] == 'no-store'


def test_offline_docs_security_headers_and_readiness():
    from app.main import app
    with TestClient(app) as client:
        assert client.get('/ready').status_code == 503
        for route in ['/', '/docs', '/static/app.js', '/static/styles.css', '/openapi.json']:
            response = client.get(route)
            assert response.status_code == 200
            assert response.headers['x-content-type-options'] == 'nosniff'
            assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        docs = client.get('/docs').text
        assert '<script src="https://' not in docs and 'X-API-Key' in docs
        schema = client.get('/openapi.json').json()
        assert schema['components']['securitySchemes']['APIKeyHeader']['name'] == 'X-API-Key'
        for route in ['/api/v1/analyze', '/api/v1/jobs/{job_id}']:
            operation = next(iter(schema['paths'][route].values()))
            assert operation['security'] == [{'APIKeyHeader': []}]


def test_wrong_key_rejected_before_body_is_read():
    from app.security import RequestProtection
    async def scenario():
        called = False
        async def downstream(*_):
            nonlocal called
            called = True
        async def receive(): raise AssertionError('Unauthorized body must not be consumed')
        output = []
        async def send(message): output.append(message)
        await RequestProtection(downstream, settings)({'type': 'http', 'path': '/api/v1/analyze', 'headers': []}, receive, send)
        assert not called and output[0]['status'] == 401
        assert (b'cache-control', b'no-store') in output[0]['headers']
    asyncio.run(scenario())


def test_chunked_upload_cannot_bypass_total_request_limit(monkeypatch):
    from app.main import app
    monkeypatch.setattr(settings, 'max_video_mb', 1)
    boundary = b'--limit\r\nContent-Disposition: form-data; name="file"; filename="test.mov"\r\nContent-Type: video/quicktime\r\n\r\n'
    def chunks():
        yield boundary
        for _ in range(3): yield b'x' * (1024 * 1024)
        yield b'\r\n--limit--\r\n'
    with TestClient(app) as client:
        response = client.post('/api/v1/analyze', headers={'X-API-Key': settings.api_key, 'Content-Type': 'multipart/form-data; boundary=limit'}, content=chunks())
        assert response.status_code == 413


@pytest.mark.parametrize('setting,value', [('max_duration_seconds', .01), ('max_video_pixels', 1024)])
def test_decoded_metadata_limits(tmp_path, monkeypatch, setting, value):
    from app.main import app
    monkeypatch.setattr(settings, setting, value)
    with TestClient(app) as client:
        response = client.post('/api/v1/analyze', headers={'X-API-Key': settings.api_key}, files={'file': ('test.mov', movie(tmp_path))})
        assert response.status_code == 422
        assert not list(settings.job_dir.glob('*.mov'))


def test_every_enabled_rule_has_a_kazakhstan_source():
    from app.visioncore.registry import refs
    for code in ['A_unattended_valuables', 'B_safe_open', 'C_cash_on_desk_next_client', 'E_unauthorized_person', 'F_bag_no_check', 'G_personal_items', 'H_door_open', 'L_workstation_unlocked']:
        sources = refs(code)
        assert sources, code
        assert all(r['url'].startswith('https://adilet.zan.kz/') and r['doc'] and r['label'] for r in sources)


def test_contradictory_verdict_is_rejected():
    with pytest.raises(ValueError, match='must agree'):
        AnalysisResult(verdict='violation', violations=[])
