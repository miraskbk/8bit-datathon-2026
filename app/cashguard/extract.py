"""CashGuard detector feature extraction (MIT; see third_party/CASHGUARD_LICENSE)."""
import cv2
from .video import iter_frames, video_info

def extract(path, coco, owl, fps, owl_fps, batch=8):
    info = video_info(path)
    frames, owl_rows, buf = [], [], []
    owl_every = max(1, round(fps / owl_fps))

    def flush():
        dets = coco([f for _, f in buf])
        for (t, f), d in zip(buf, dets):
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            frames.append({"t": round(t, 3), "bright": round(float(gray.mean()), 1), "det": d})
        buf.clear()

    for k, (t, f) in enumerate(iter_frames(path, fps)):
        buf.append((t, f))
        if k % owl_every == 0:
            owl_rows.append({"t": round(t, 3), "det": owl(f)})
        if len(buf) == batch:
            flush()
    if buf:
        flush()
    return {"info": info, "fps": fps, "owl_fps": owl_fps, "frames": frames, "owl": owl_rows,
            "owl_queries": owl.queries}
