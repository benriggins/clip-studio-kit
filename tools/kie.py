#!/usr/bin/env python3
"""kie.ai generation for the cinema engine: stills (GPT Image 2.5) and B-roll clips (Grok Imagine Video 1.5).

usage:
  kie.py image "<prompt>" out.png [--aspect 9:16] [--transparent] [--res 1K]      about $0.03 an image
  kie.py video "<prompt>" out.mp4 [--image first-frame.png] [--seconds 5]         about $0.0225 a second at 720p

Best B-roll: make the first frame with `image` (it renders exact on-screen text), then animate it with `video`,
prompting only the camera move and what must NOT change ("the text stays exactly the same").
Every image prompt opens with a realism plan ("Plan for maximum realism with zero physical defects: …").
Key: KIE_API_KEY, or my-studio/kie.local.json {"apiKey": "…"}. Local first frames go through kie.ai's own upload.
"""
import argparse
import json
import os
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = 'https://api.kie.ai/api/v1/jobs'
UPLOAD = 'https://kieai.redpandaai.co/api/file-stream-upload'
IMAGE_MODEL = 'gpt-image-2-5-{variant}-text-to-image'
VIDEO_MODEL = 'grok-imagine-video-1-5-preview'


def key():
    if os.environ.get('KIE_API_KEY'):
        return os.environ['KIE_API_KEY']
    for p in (ROOT / 'my-studio' / 'kie.local.json', Path('/Users/Shared/Projects/agent-os/secrets/kie-ai.local.json')):
        if p.exists():
            return json.loads(p.read_text())['apiKey']
    raise SystemExit('No kie.ai key: set KIE_API_KEY or save my-studio/kie.local.json as {"apiKey": "…"} (kie.ai → API keys)')


def call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method='POST' if body else 'GET',
                                 headers={'Authorization': f'Bearer {key()}', 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def upload(path):
    """Host a local file on kie.ai (temporary URL) so a model can read it."""
    b = uuid.uuid4().hex
    data = (f'--{b}\r\nContent-Disposition: form-data; name="uploadPath"\r\n\r\nclip-studio\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{Path(path).name}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n').encode() + Path(path).read_bytes() + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(UPLOAD, data=data, method='POST', headers={
        'Authorization': f'Bearer {key()}', 'Content-Type': f'multipart/form-data; boundary={b}'})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if r.get('code') != 200:
        raise SystemExit(f'upload failed: {r}')
    return r['data']['downloadUrl']


def _run(model, inp, out, poll=4, tries=150):
    r = call(f'{API}/createTask', {'model': model, 'input': inp})
    if r.get('code') != 200:
        raise SystemExit(f'createTask failed: {r}')
    tid = r['data']['taskId']
    for _ in range(tries):
        time.sleep(poll)
        d = call(f'{API}/recordInfo?taskId={tid}')['data']
        if d.get('state') == 'success':
            url = json.loads(d['resultJson'])['resultUrls'][0]
            Path(out).write_bytes(urllib.request.urlopen(url, timeout=300).read())
            return out
        if d.get('state') == 'fail':
            raise SystemExit(f'generation failed: {d.get("failMsg") or d}')
    raise SystemExit('timed out')


def image(prompt, out, aspect='9:16', transparent=False, res='1K', variant='flare'):
    inp = {'prompt': prompt, 'aspect_ratio': aspect, 'resolution': res}
    if transparent:
        inp['background'] = 'transparent'
    return _run(IMAGE_MODEL.format(variant=variant), inp, out)


def video(prompt, out, first_frame=None, seconds=5, aspect='9:16', res='720p'):
    inp = {'prompt': prompt, 'duration': seconds, 'aspect_ratio': aspect, 'resolution': res}
    if first_frame:
        inp['image_urls'] = [first_frame if str(first_frame).startswith('http') else upload(first_frame)]
    return _run(VIDEO_MODEL, inp, out, poll=6)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=['image', 'video'])
    ap.add_argument('prompt')
    ap.add_argument('out')
    ap.add_argument('--aspect', default='9:16')
    ap.add_argument('--transparent', action='store_true')
    ap.add_argument('--res')
    ap.add_argument('--image')
    ap.add_argument('--seconds', type=int, default=5)
    a = ap.parse_args()
    if a.what == 'image':
        print(image(a.prompt, a.out, a.aspect, a.transparent, a.res or '1K'))
    else:
        print(video(a.prompt, a.out, a.image, a.seconds, a.aspect, a.res or '720p'))
