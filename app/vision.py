"""Offline visual baseline. No networking, audio, identity, or label lookups at inference."""
import base64
import time
from pathlib import Path
import cv2
import numpy as np

VERSION = 1


def samples(path: Path, step: float = 1.0, budget: float = 180):
    cap = cv2.VideoCapture(str(path))
    started = time.monotonic()
    previous = None
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not cap.isOpened() or fps <= 0 or count <= 0:
            raise ValueError('Video cannot be decoded')
        duration = count / fps
        if duration > 180:
            raise ValueError('Maximum video duration is 180 seconds')
        for timestamp in np.arange(0, duration, step):
            if time.monotonic() - started > budget:
                raise TimeoutError('Local analysis time limit exceeded')
            cap.set(cv2.CAP_PROP_POS_MSEC, float(timestamp * 1000))
            ok, frame = cap.read()
            if not ok:
                # Container duration may exceed the final decodable frame slightly.
                if timestamp > 0 and timestamp >= duration - step:
                    break
                raise ValueError(f'Cannot decode video at {timestamp:.1f}s')
            small = cv2.resize(frame, (128, 128))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            features = []
            # Coarse spatial appearance and motion; deliberately a cheap baseline.
            for row in range(4):
                for col in range(4):
                    cell = hsv[row*32:(row+1)*32, col*32:(col+1)*32]
                    features.extend(cell.mean(axis=(0, 1)) / 255)
                    features.extend(cell.std(axis=(0, 1)) / 255)
                    delta = np.zeros((32, 32)) if previous is None else cv2.absdiff(gray, previous)[row*32:(row+1)*32, col*32:(col+1)*32]
                    features.extend([delta.mean()/255, (delta > 25).mean()])
            previous = gray
            yield float(timestamp), np.asarray(features, dtype=np.float32), frame
    finally:
        cap.release()


def jpeg(frame):
    h, w = frame.shape[:2]
    if max(h, w) > 960:
        frame = cv2.resize(frame, (round(w*960/max(h,w)), round(h*960/max(h,w))))
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise ValueError('Evidence encoding failed')
    return base64.b64encode(encoded).decode('ascii')


def analyze(path, artifact):
    if artifact.get('feature_version') != VERSION:
        raise ValueError('Model feature version mismatch')
    candidates = []
    classes = list(artifact['model'].classes_)
    for timestamp, vector, frame in samples(path):
        probability = artifact['model'].predict_proba(vector.reshape(1, -1))[0]
        index = int(np.argmax(probability))
        category = str(classes[index])
        if category != 'normal' and probability[index] >= artifact['threshold']:
            candidates.append((timestamp, float(probability[index]), category, frame))
    # Keep one peak per contiguous class segment, preserving separate events.
    groups = []
    for candidate in candidates:
        if groups and candidate[0] - groups[-1][-1][0] <= 2 and candidate[2] == groups[-1][-1][2]:
            groups[-1].append(candidate)
        else:
            groups.append([candidate])
    violations = []
    for group in groups[:12]:
        timestamp, confidence, category, frame = max(group, key=lambda x: x[1])
        violations.append({
            'type': category,
            'timecode_sec': timestamp,
            'description': 'Local visual model flagged this segment for human review. The action and applicable rule have not yet been verified.',
            'evidence_frames': [{'timestamp_sec': timestamp, 'image_base64': jpeg(frame)}],
            'confidence': round(confidence, 4),
            'rule': None,
        })
    return {'verdict': 'violation' if violations else 'no_violation', 'violations': violations,
            'model_stage': 'experimental_baseline', 'requires_human_review': True}
