"""Verify a deployed HTTPS service and prepare a private jury handoff."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from app.config import ROOT, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='Your deployed public HTTPS origin')
    args = parser.parse_args()
    parts = urlsplit(args.url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('', '/'):
        parser.error('Use an HTTPS origin, without credentials, paths, query strings or fragments')
    if len(settings.api_key) < 32:
        parser.error('Configure the same private API_KEY as the deployed server')
    origin = args.url.rstrip('/')
    with httpx.Client(base_url=origin, timeout=15, follow_redirects=False) as client:
        for path in ['/', '/docs', '/openapi.json', '/ready', '/api/v1/capabilities']:
            response = client.get(path)
            if response.status_code != 200:
                raise SystemExit(f'Deployment check failed: {path}, HTTP {response.status_code}')
        probe = '/api/v1/jobs/' + '0' * 32
        if client.get(probe).status_code != 401 or client.get(probe, headers={'X-API-Key': settings.api_key}).status_code != 404:
            raise SystemExit('Deployment authentication check failed')
    destination = ROOT / 'runtime/jury-submission.md'
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    text = (f'# Private jury access\n\nUI: {origin}/\nAPI: {origin}/api/v1\n'
            f'Instructions: {origin}/docs\nReadiness: {origin}/ready\n\n'
            f'X-API-Key: {settings.api_key}\n\n'
            'POST /api/v1/analyze, multipart field file (.mov). Poll GET /api/v1/jobs/{job_id}.\n'
            'One accepted job at a time. Retry HTTP 429 after the running job completes.\n'
            'Results/evidence expire after one hour by default. Keep this file private.\n'
            'Run a real upload/poll smoke test on the deployed host before submission.\n')
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(text)
    destination.chmod(0o600)
    print('HTTPS routes and API-key access verified. Private handoff: runtime/jury-submission.md')


if __name__ == '__main__':
    main()
