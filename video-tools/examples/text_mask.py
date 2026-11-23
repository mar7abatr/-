import numpy as np
from PIL import Image, ImageFilter
src = Image.open("/tmp/w3/src/doc.jpg").convert("RGB")
im = np.asarray(src).astype(int)
H, W, _ = im.shape
r, g, b = im[..., 0], im[..., 1], im[..., 2]
L = np.asarray(src.convert("L")).astype(int)
# local background brightness: max filter (text is darker than the coat) then smooth
bg = np.asarray(src.convert("L").filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(6))).astype(int)
dark = (L < bg - 55) & (im.max(axis=2) < 150)
red = (r > 140) & (r - g > 60) & (r - b > 50)
yy, xx = np.mgrid[0:H, 0:W]
boxes = [
    (488, 672, 878, 798, "dark"),
    (145, 805, 885, 950, "red"),
    (140, 962, 885, 1062, "dark"),
    (140, 1062, 668, 1110, "dark"),
    (325, 1108, 668, 1162, "dark"),
]
m = np.zeros((H, W), bool)
for x0, y0, x1, y1, k in boxes:
    inb = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    m |= inb & (dark if k == "dark" else red)
m[(xx >= 545) & (xx <= 635) & (yy < 718)] = False
mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MaxFilter(5))
mi.save("/tmp/w3/mask.png")
ov = im.copy(); mm = np.asarray(mi) > 0
ov[mm] = (ov[mm] * 0.3 + np.array([0, 255, 0]) * 0.7).astype(int)
Image.fromarray(ov.astype(np.uint8)).crop((150, 640, 1024, 1200)).save("/tmp/w3/mask_ov.png")
print("mask px", mm.sum())
