"""Create private local configuration; never overwrite an existing .env."""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path


def configure(root: Path, backend: str) -> bool:
    path = root / '.env'
    if path.exists():
        return False
    model = 'Qwen3-VL-8B-Instruct-4bit' if backend == 'mlx' else 'Qwen3-VL-4B-Instruct'
    key = secrets.token_urlsafe(32)
    text = (root / '.env.example').read_text()
    text = text.replace('replace-with-a-private-jury-key', key)
    text = text.replace('VLM_BACKEND=mlx', f'VLM_BACKEND={backend}')
    text = text.replace('models/Qwen3-VL-8B-Instruct-4bit', f'models/{model}')
    with open(path, 'x', opener=lambda name, flags: os.open(name, flags, 0o600)) as output:
        output.write(text)
    runtime = root / 'runtime'
    runtime.mkdir(exist_ok=True, mode=0o700)
    access = runtime / 'jury-access.txt'
    with open(access, 'w', opener=lambda name, flags: os.open(name, flags, 0o600)) as output:
        output.write(f'Local UI: http://127.0.0.1:8003\nX-API-Key: {key}\n')
    access.chmod(0o600)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=['mlx', 'transformers'], default='mlx')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if configure(root, args.backend):
        print('Created private .env. Your key is in runtime/jury-access.txt. Do not commit either file.')
    else:
        print('Existing .env preserved. Use its API_KEY; no configuration was overwritten.')


if __name__ == '__main__':
    main()
