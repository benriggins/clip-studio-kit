"""Subject cut-out with Apple Vision (macOS 14+), for the "word behind the subject" carousel move.

    uv run --with pyobjc-framework-Vision --with pyobjc-framework-Quartz python cutout.py <in.png|jpg> <out.png>

Writes a full-size PNG (same dimensions as the input) with the background made transparent.
"""
import sys

import Quartz
import Vision
from Foundation import NSURL

src, dst = sys.argv[1], sys.argv[2]
ci = Quartz.CIImage.imageWithContentsOfURL_(NSURL.fileURLWithPath_(src))
handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(ci, None)
req = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
ok, err = handler.performRequests_error_([req], None)
if not ok or not req.results():
    sys.exit(f'no subject found: {err}')
obs = req.results()[0]
buf, err = obs.generateMaskedImageOfInstances_fromRequestHandler_croppedToInstancesExtent_error_(
    obs.allInstances(), handler, False, None)
if buf is None:
    sys.exit(f'mask failed: {err}')
out = Quartz.CIImage.imageWithCVPixelBuffer_(buf)
ctx = Quartz.CIContext.contextWithOptions_(None)
cs = Quartz.CGColorSpaceCreateWithName(Quartz.kCGColorSpaceSRGB)
ok, err = ctx.writePNGRepresentationOfImage_toURL_format_colorSpace_options_error_(
    out, NSURL.fileURLWithPath_(dst), Quartz.kCIFormatRGBA8, cs, {}, None)
if not ok:
    sys.exit(f'write failed: {err}')
print('ok', int(out.extent().size.width), int(out.extent().size.height))
