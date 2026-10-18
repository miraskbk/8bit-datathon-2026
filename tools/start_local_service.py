"""Start the API with local offline model loading; no model or video downloads."""
from __future__ import annotations
import os
import sys
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
    import uvicorn
    uvicorn.run("app.main:app",host="127.0.0.1",port=8003,workers=1)


if __name__=="__main__":main()
