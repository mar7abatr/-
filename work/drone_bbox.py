import numpy as np, subprocess, sys
D = "../.hoplite/attachments/art_upload_1e283b27cc964f6886ae3d320e7af82c/مشاهد لطائرة شاهد 136 بدون خلفية.webm"
W, H = 960, 540
for t in [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", D, "-frames:v", "1", "-vf", f"scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(int)
    g = (a[..., 1] > 150) & (a[..., 0] < 100) & (a[..., 2] < 120)
    m = ~g
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        print(t, 'none'); continue
    print(t, 'x', xs.min() * 4, xs.max() * 4, 'y', ys.min() * 4, ys.max() * 4, 'n', len(xs))
