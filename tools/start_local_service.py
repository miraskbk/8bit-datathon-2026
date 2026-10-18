"""Start the API with offline model loading. Never downloads models or videos."""
from __future__ import annotations
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8003)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
    import uvicorn
    uvicorn.run('app.main:app', host=args.host, port=args.port, workers=1, access_log=False)


if __name__ == '__main__':
    main()
