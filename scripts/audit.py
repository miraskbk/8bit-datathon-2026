"""Read the supplied workbook locally and produce a private manifest."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import cv2
from openpyxl import load_workbook


def identifier(value):
    match = re.search(r'[XХxх][\s_-]*(\d+)', str(value))
    return f'X-{int(match[1])}' if match else None


def audit(root, output):
    workbook = load_workbook(root / 'open_labels.xlsx', read_only=True, data_only=True)
    rows = list(workbook.active.values)
    print('Workbook headers:', rows[0])
    labels = {}
    for row in rows[1:]:
        key = identifier(row[0])
        if key:
            labels[key] = list(row[1:])
    records = []
    for path in sorted((root/'videos').glob('*')):
        if path.suffix.lower() != '.mov':
            continue
        key = identifier(path.stem)
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        raw = labels.get(key)
        records.append({'id': key, 'path': str(path.resolve()), 'sha256': digest,
                        'fps': fps, 'duration_sec': count/fps if fps else None,
                        'width': int(cap.get(3)), 'height': int(cap.get(4)),
                        'readable': cap.isOpened() and fps > 0, 'raw_label': raw})
        cap.release()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str))
    hashes = {}
    for r in records:
        hashes.setdefault(r['sha256'], []).append(r['id'])
    print(json.dumps({'videos': len(records), 'unique_videos': len(hashes),
                      'duplicates': [v for v in hashes.values() if len(v)>1],
                      'unreadable': [r['id'] for r in records if not r['readable']],
                      'label_samples': [r['raw_label'] for r in records[:4]]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    p.add_argument('--output', type=Path, default=Path('data/manifest.json'))
    args = p.parse_args()
    audit(args.root, args.output)
