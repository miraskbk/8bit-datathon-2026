import numpy as np
from pathlib import Path

from app.model import event_peaks, window_centers
from app.rules import RULES
from app.train import parse_timestamp
from app.train_types import read_type_labels


def test_window_centers_cover_a_video_at_one_second_stride():
    assert np.array_equal(window_centers(8, 1), np.array([2, 3, 4, 5, 6], dtype=np.float32))


def test_event_peaks_collapse_adjacent_positive_windows():
    centers = np.arange(2, 27, dtype=np.float32)
    scores = np.zeros_like(centers)
    scores[1:4] = [0.7, 0.9, 0.8]
    scores[19:21] = [0.6, 0.7]
    peaks = event_peaks(centers, scores, threshold=0.5, max_events=5)
    assert len(peaks) == 2
    assert np.isclose(peaks[0][0], 4.0, atol=0.1) and np.isclose(peaks[0][1], 0.9)
    assert 21.0 < peaks[1][0] < 22.0 and np.isclose(peaks[1][1], 0.7)


def test_event_peaks_respect_threshold():
    assert event_peaks(np.array([2, 3]), np.array([0.1, 0.4]), 0.5, 5) == []


def test_russian_timestamp_parser():
    assert parse_timestamp("1 мин 8 сек") == 68
    assert parse_timestamp("22 сек") == 22
    assert parse_timestamp(None) is None


def test_audited_type_labels_are_varied_and_supported():
    labels = read_type_labels(Path("open/violation_types.csv"))
    known_codes = {rule.code for rule in RULES}
    assert len(labels) == 22
    assert len(set(labels.values())) == 7
    assert set(labels.values()) <= known_codes
