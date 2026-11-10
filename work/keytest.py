import numpy as np
from PIL import Image
for name, i in [('drone_side', 60), ('drone_front', 60)]:
    a = np.fromfile(f'media/{name}.rgba', np.uint8, count=960*540*4, offset=960*540*4*i).reshape(540, 960, 4)
    bg = np.zeros((540, 960, 3), np.float32); bg[:] = (10, 25, 45)
    al = a[..., 3:4] / 255.0
    out = a[..., :3] * al + bg * (1 - al)
    Image.fromarray(out.astype(np.uint8)).save(f'thumbs/key_{name}.png')
