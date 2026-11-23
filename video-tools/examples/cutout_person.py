import sys, numpy as np
from PIL import Image
from rembg import remove, new_session
name = sys.argv[1]
s = new_session(name)
img = Image.open("/tmp/w3/clean3.png").convert("RGB")
out = remove(img, session=s, post_process_mask=True)
out.save(f"/tmp/w3/cut_{name}.png")
a = np.asarray(out)[..., 3]
# preview on a red background to judge edges
bg = Image.new("RGB", img.size, (160, 40, 20)); bg.paste(out, (0, 0), out)
bg.resize((512, 640)).save(f"/tmp/w3/prev_{name}.png")
print(name, "alpha>0", (a > 0).mean().round(3))
