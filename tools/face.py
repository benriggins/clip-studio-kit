#!/usr/bin/env python3
"""Where is the speaker's face? Samples frames and returns the median face box (OpenCV, free, offline).

usage: face.py <media> <start_sec> <end_sec>      -> prints JSON {cx, cy, w, h, found} in source pixels
Used by plan.py to set static, face-centred crops. No tracking: a locked crop per segment looks deliberate.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import ffmpeg, probe  # noqa: E402


def frame(media, t, width):
    import numpy as np
    info = probe(media)
    h = int(round(info['height'] * width / info['width'] / 2) * 2)
    raw = subprocess.run([ffmpeg(), '-v', 'error', '-ss', f'{t:.3f}', '-i', str(media), '-frames:v', '1',
                          '-vf', f'scale={width}:{h}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='uint8').reshape(h, width), info['width'] / width


_DET = []


def detectors():
    import cv2
    if not _DET:
        # alt2 copes with hats, beards and side light far better than the default model; default is the fallback
        _DET.extend(cv2.CascadeClassifier(cv2.data.haarcascades + f) for f in
                    ('haarcascade_frontalface_alt2.xml', 'haarcascade_frontalface_default.xml'))
    return _DET


def face_box(media, start, end, samples=5, fallback=True):
    import cv2
    import numpy as np
    boxes = []
    for k in range(samples):
        t = start + (end - start) * (k + 0.5) / samples
        img, scale = frame(media, t, 640)
        img = cv2.equalizeHist(img)
        faces = []
        for det in detectors():
            faces = det.detectMultiScale(img, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
            if len(faces):
                break
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            boxes.append([(x + w / 2) * scale, (y + h / 2) * scale, w * scale, h * scale])
    if not boxes:
        if fallback:      # speaker turned away in this span: use where their face usually is in this take
            dur = probe(media)['duration']
            whole = face_box(media, 0, dur, samples=12, fallback=False)
            if whole['found']:
                return {**whole, 'found': True, 'fallback': True}
        info = probe(media)
        return {'cx': info['width'] / 2, 'cy': info['height'] * 0.4, 'w': 0, 'h': 0, 'found': False}
    cx, cy, w, h = np.median(np.array(boxes), axis=0)
    return {'cx': float(cx), 'cy': float(cy), 'w': float(w), 'h': float(h), 'found': True}


if __name__ == '__main__':
    print(json.dumps(face_box(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))))
