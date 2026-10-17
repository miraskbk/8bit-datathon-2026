"""Weakly supervised baseline and honest held-out video evaluation."""
import argparse
import json
import re
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.model_selection import train_test_split
from app.vision import VERSION, samples


def label(row):
    # Audit output retains workbook columns verbatim; fail closed on unknown labels.
    values = row['raw_label'] or []
    value = str(values[1]).strip().lower() if len(values)>1 else ''
    if value in ('нет', 'no', '0', 'false', 'без нарушения', 'нет нарушения', 'no violation', 'no_violation'):
        return 0
    if value in ('да', 'yes', '1', 'true', 'нарушение', 'violation'):
        return 1
    raise ValueError(f'Unknown label for {row["id"]}: {values}')


def train(args):
    rows = json.loads(args.manifest.read_text())
    unique = {}
    for row in rows:
        group = unique.setdefault(row['sha256'], {'rows': [], 'label': label(row)})
        if group['label'] != label(row):
            raise ValueError('Conflicting labels for identical videos')
        group['rows'].append(row)
    keys = sorted(unique)
    train_keys, test_keys = train_test_split(keys, test_size=.25, random_state=42, stratify=[unique[k]['label'] for k in keys])
    features = {}
    x, y = [], []
    for i, key in enumerate(keys):
        group = unique[key]
        row = group['rows'][0]
        cache = Path('data/features')/f'{key}-v{VERSION}.npz'
        if cache.exists():
            with np.load(cache) as saved:
                times, vectors = saved['times'].tolist(), saved['vectors']
        else:
            times, vectors = [], []
            for timestamp, vector, _ in samples(Path(row['path'])):
                times.append(timestamp)
                vectors.append(vector)
            vectors = np.asarray(vectors)
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache, times=np.asarray(times), vectors=vectors)
        features[key] = (np.asarray(times), vectors)
        if key in train_keys:
            if group['label']:
                stamps = [float(re.search(r'\d+(?:[.,]\d+)?', str(r['raw_label'][0]))[0].replace(',', '.')) for r in group['rows']]
                mask = np.asarray([any(abs(t-s)<=2 for s in stamps) for t in times])
                # Other positive-video frames remain unlabeled, never assumed normal.
                x.extend(vectors[mask]); y.extend(['possible_violation_unclassified']*int(mask.sum()))
            else:
                x.extend(vectors); y.extend(['normal']*len(vectors))
        print(f'Features {i+1}/{len(keys)}', flush=True)
    model = ExtraTreesClassifier(n_estimators=160, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=2)
    model.fit(x, y)
    positive_index = list(model.classes_).index('possible_violation_unclassified')
    results = []
    for key in test_keys:
        times, vectors = features[key]
        probabilities = model.predict_proba(vectors)[:, positive_index]
        peak = int(probabilities.argmax())
        group = unique[key]
        predicted = bool(probabilities[peak]>=args.threshold)
        stamps = [float(re.search(r'\d+(?:[.,]\d+)?', str(r['raw_label'][0]))[0].replace(',', '.')) for r in group['rows']] if group['label'] else []
        results.append({'ids': [r['id'] for r in group['rows']], 'actual': group['label'], 'predicted': int(predicted),
                        'peak_sec': float(times[peak]), 'score': float(probabilities[peak]),
                        'timestamp_error_sec': min(abs(times[peak]-t) for t in stamps) if stamps and predicted else None})
    tp = sum(r['actual']==1 and r['predicted']==1 for r in results)
    fp = sum(r['actual']==0 and r['predicted']==1 for r in results)
    positives = sum(r['actual'] for r in results)
    report = {'stage': 'weakly_supervised_baseline', 'threshold': args.threshold, 'train_unique_videos': len(train_keys),
              'test_unique_videos': len(test_keys), 'video_recall': tp/positives if positives else None,
              'false_positive_rate': fp/(len(results)-positives), 'results': results,
              'limitations': ['One small grouped holdout; not a reliable generalization estimate.',
                             'No action taxonomy or legal interpretation learned.', 'Fixed camera appearance baseline; unproven on new angles.',
                             'Only training fold used in saved model; held-out videos remain unseen.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'feature_version': VERSION, 'model': model, 'threshold': args.threshold,
                 'train_hashes': train_keys, 'test_hashes': test_keys}, args.output)
    Path('data/evaluation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='results'}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, default=Path('data/manifest.json'))
    p.add_argument('--output', type=Path, default=Path('models/baseline.joblib'))
    p.add_argument('--threshold', type=float, default=.65)
    train(p.parse_args())
