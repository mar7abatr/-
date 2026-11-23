"""Restrained sound design for the medical-system video, mixed under the original voice-over."""
import numpy as np, wave
from scipy.signal import butter, sosfilt
import importlib.util, sys
sys.argv = ["x", "none"]
spec = importlib.util.spec_from_file_location("r2", "/tmp/w2/render2.py"); r2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r2)

SR = 48000; DUR = 21.0; n = int(SR * DUR)
rng = np.random.default_rng(5)
L = np.zeros(n); R = np.zeros(n)

def add(sig, t, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(n, i + len(sig))
    if j <= i or i < 0: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt(0.5 * (1 - pan)); R[i:j] += s * np.sqrt(0.5 * (1 + pan))

def env(m, a, r):
    e = np.ones(m); ai = min(m // 2, max(1, int(a * SR))); ri = min(m // 2, max(1, int(r * SR)))
    e[:ai] = np.linspace(0, 1, ai) ** 2; e[-ri:] *= np.linspace(1, 0, ri) ** 2
    return e
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, btype="low", fs=SR, output="sos"), x)
def norm(x): return x / (np.abs(x).max() + 1e-9)

def whoosh(dur, lo=300, hi=3500):
    m = int(dur * SR); x = rng.normal(0, 1, m); out = np.zeros(m); bands = np.geomspace(lo, hi, 7)
    pos = np.sin(np.linspace(0, np.pi, m))
    for k in range(len(bands) - 1):
        out += bp(x, bands[k], bands[k + 1]) * np.exp(-((pos - k / (len(bands) - 2)) ** 2) / 0.05)
    return norm(out * np.sin(np.linspace(0, np.pi, m)) ** 1.5)

def ping(f, dur=0.9, decay=5.0):
    tt = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-decay * tt) * env(int(dur * SR), 0.004, 0.05)
    d = int(0.11 * SR); o = s.copy(); o[d:] += 0.35 * s[:-d]
    return norm(o)

def tick(f=2200, dur=0.045):
    tt = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * f * tt) * np.exp(-70 * tt)

def boom(dur=1.8, f0=55, dist=False):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * np.exp(-tt * 1.3) + 28
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.6 * tt)
    s += lp(rng.normal(0, 1, len(tt)), 900 if not dist else 300) * np.exp(-5 * tt) * 0.7
    if dist: s = lp(s, 400)
    return norm(s * env(len(s), 0.006, 0.3))

def jet(dur):
    m = int(dur * SR); x = rng.normal(0, 1, m)
    a = bp(x, 400, 2500) * 0.6 + lp(x, 300) * 1.2
    sweep = np.linspace(1, 0, m)
    hi = bp(x, 1500, 6000) * sweep ** 2
    return norm((a + hi) * np.sin(np.linspace(0, np.pi, m)) ** 2)

def crackle(dur):
    m = int(dur * SR); out = lp(rng.normal(0, 1, m), 500) * 0.5
    imp = np.zeros(m); idx = rng.integers(0, m, int(dur * 70)); imp[idx] = rng.uniform(-1, 1, len(idx))
    out += bp(imp, 1500, 7000) * 6
    return norm(out) * env(m, 0.8, 1.0)

tt = np.arange(n) / SR
drone = (np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.4 * tt + 1)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * tt))
drone += 0.5 * bp(rng.normal(0, 1, n), 200, 800)
add(norm(drone) * env(n, 1.0, 1.0), 0, 0, 0.04)

# scene 1: jets, bombs, counter
for (t0, x0, vx, y0, s) in r2.JETS:
    add(jet(2.4), max(0, t0 + 0.05), 0, 0.07 * s)
for b in r2.BOMBS:
    pan = (b["xt"] / 1080 - 0.5) * 1.2
    add(whoosh(0.7, 900, 5000), b["ti"] - 0.7, pan, 0.025)
    add(boom(1.6, 55, dist=True), b["ti"], pan, 0.10)
for k in range(24):
    add(tick(2400 + 30 * k), 0.72 + 0.63 * (k / 24) ** 1.5, 0, 0.02)
# hub transition, cards, strikes
add(whoosh(0.6), 3.4, 0, 0.11)
for c in r2.CARDS:
    add(ping(880 if c["cx"] > 540 else 990, 0.8), c["t"], 0.3 if c["cx"] > 540 else -0.3, 0.055)
    add(boom(0.9, 70), c["ts"], 0.3 if c["cx"] > 540 else -0.3, 0.07)
    add(tick(3000, 0.03), c["ts"] - 0.45, 0, 0.03)
add(whoosh(0.7, 200, 3000), 7.25, 0, 0.12)
# scene 3: somber low tone + counter
tt3 = np.arange(int(2.5 * SR)) / SR
add(norm(np.sin(2 * np.pi * 73.4 * tt3) + 0.4 * np.sin(2 * np.pi * 110 * tt3)) * np.exp(-1.2 * tt3) * env(len(tt3), 0.02, 0.4), 8.38, 0, 0.09)
for k in range(30):
    add(tick(2000 + 25 * k), 8.85 + 0.9 * (k / 30) ** 1.5, 0, 0.016)
# scene 4: hit, fire bed, counters, partial
add(whoosh(0.6, 200, 4000), 11.35, 0, 0.1)
add(boom(2.0, 48), 11.85, 0, 0.13)
add(crackle(9.2), 11.8, 0.1, 0.045)
add(whoosh(0.5, 400, 4000), 12.85, 0, 0.06)
for k in range(19):
    add(tick(2300 + 20 * k), 13.21 + 0.74 * (k / 19), 0.2, 0.025)
for k in range(17):
    add(boom(0.25, 90), 16.95 + 0.95 * k / 17, -0.2, 0.025)
for f, dt in ((660, 0), (523, 0.18)):
    add(ping(f, 1.0, 3.5), 18.65 + dt, 0, 0.05)
add(whoosh(1.0, 200, 2500), 20.1, 0, 0.06)

mix = np.clip(np.stack([L, R], 1), -1, 1)
print("sfx peak", np.abs(mix).max())
w = wave.open("/tmp/w2/sfx.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
