import numpy as np
from PIL import Image, ImageFilter
from simple_lama_inpainting import SimpleLama

BOXES = [(488, 672, 878, 798), (145, 805, 885, 950), (140, 962, 885, 1062), (140, 1062, 668, 1110), (325, 1108, 668, 1162)]
SPOTS = [(325, 930, 24), (625, 865, 22), (437, 842, 20), (510, 920, 16), (595, 1131, 18), (632, 785, 14), (330, 900, 16)]
lama = SimpleLama()
img = Image.open("/tmp/w3/clean2.png").convert("RGB")
H, W = img.height, img.width
yy, xx = np.mgrid[0:H, 0:W]
inb = np.zeros((H, W), bool)
for x0, y0, x1, y1 in BOXES:
    inb |= (xx >= x0 - 8) & (xx <= x1 + 8) & (yy >= y0 - 6) & (yy <= y1 + 6)
inb &= ~((xx >= 545) & (xx <= 635) & (yy < 718))
a = np.asarray(img).astype(float)
med = np.dstack([np.asarray(img.getchannel(c).filter(ImageFilter.MedianFilter(41))).astype(float) for c in range(3)])
dist = np.sqrt(((a - med) ** 2).sum(axis=2))
m = (dist > 20) & inb
for x, y, r in SPOTS:
    m |= (xx - x) ** 2 + (yy - y) ** 2 <= r * r
mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(11))
print("px", int((np.asarray(mi) > 0).sum()))
img = lama(img, mi).crop((0, 0, W, H))
img.save("/tmp/w3/clean3.png")
