#!/usr/bin/env python3
"""Put the speaker IN FRONT of "back" layer graphics (cards that pass behind his head), like the
alessandro.marfella references. Apple Vision person segmentation (macOS 12+), free and local.

  uv run --with pyobjc-framework-Vision --with pyobjc-framework-Quartz python depth.py \
      <with-back.mp4> <base.mp4> <out.mp4> --window 0 18.3 --window 32.55 36.95

with-back.mp4 = the cut with only the back-layer graphics; base.mp4 = the same cut with no graphics.
Inside each window the person from base.mp4 is laid back over the cards. Audio comes from with-back.mp4.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import Quartz
import Vision
from Foundation import NSURL

sys.path.insert(0, str(Path(__file__).parent))
from _common import ffmpeg  # noqa: E402
FF = ffmpeg()
MASK_W, MASK_H = 540, 960


def mattes(base, a, b, d):
    frames = d / 'f'
    frames.mkdir()
    subprocess.run([FF, '-v', 'error', '-ss', f'{a}', '-to', f'{b}', '-i', str(base), '-vf', f'fps=30,scale={MASK_W}:{MASK_H}',
                    str(frames / '%05d.png')], check=True)
    out = d / 'm'
    out.mkdir()
    ctx = Quartz.CIContext.contextWithOptions_(None)
    gray = Quartz.CGColorSpaceCreateDeviceGray()
    for f in sorted(frames.glob('*.png')):
        ci = Quartz.CIImage.imageWithContentsOfURL_(NSURL.fileURLWithPath_(str(f)))
        req = Vision.VNGeneratePersonSegmentationRequest.alloc().initWithCompletionHandler_(None)
        req.setQualityLevel_(0)                                   # accurate: clean hair edges
        req.setOutputPixelFormat_(1278226488)                     # kCVPixelFormatType_OneComponent8
        h = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(ci, None)
        ok, err = h.performRequests_error_([req], None)
        if not ok or not req.results():
            sys.exit(f'segmentation failed on {f.name}: {err}')
        m = Quartz.CIImage.imageWithCVPixelBuffer_(req.results()[0].pixelBuffer())
        sx, sy = MASK_W / m.extent().size.width, MASK_H / m.extent().size.height
        m = m.imageByApplyingTransform_(Quartz.CGAffineTransformMakeScale(sx, sy))
        ctx.writePNGRepresentationOfImage_toURL_format_colorSpace_options_error_(
            m, NSURL.fileURLWithPath_(str(out / f.name)), Quartz.kCIFormatL8, gray, None, None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('front')
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--window', nargs=2, type=float, action='append', required=True)
    a = ap.parse_args()
    td = Path(tempfile.mkdtemp())
    ins, fc, prev = ['-i', a.front, '-i', a.base], [], '0:v'
    for k, (t0, t1) in enumerate(a.window):
        d = td / f'w{k}'
        d.mkdir()
        mdir = mattes(a.base, t0, t1, d)
        ins += ['-framerate', '30', '-i', str(mdir / '%05d.png')]
        mi = 2 + k
        # soften the matte edge a touch so hair blends instead of stair-stepping
        fc.append(f'[{mi}:v]scale=1080:1920:flags=bicubic,gblur=sigma=1.2,format=gray,setpts=PTS-STARTPTS+{t0}/TB[m{k}]')
        fc.append(f'[1:v]trim={t0}:{t1},setpts=PTS-STARTPTS+{t0}/TB,format=rgba[p{k}]')
        fc.append(f'[p{k}][m{k}]alphamerge[pa{k}]')
        fc.append(f'[{prev}][pa{k}]overlay=0:0:eof_action=pass:enable=\'between(t,{t0},{t1})\'[o{k}]')
        prev = f'o{k}'
    subprocess.run([FF, '-y', '-v', 'error', *ins, '-filter_complex', ';'.join(fc), '-map', f'[{prev}]', '-map', '0:a?',
                    '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'copy', a.out], check=True)
    print(f'depth → {a.out}')


if __name__ == '__main__':
    main()
