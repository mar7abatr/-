"""Restrained sound design under the original voice-over (event times mirror render.py)."""
import numpy as np, wave, os, sys
from scipy.signal import butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["x", "none"]
sys.path.insert(0, HERE)
import render as r

SR = 48000; DUR = r.DUR; n = int(SR * DUR)
rng = np.random.default_rng(5)
L = np.zeros(n); R = np.zeros(n)

def add(sig, t, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(n, i + len(sig))
    if j <= i or i < 0: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt(0.5 * (1 - pan)); R[i:j] += s * np.sqrt(0.5 * (1 + pan))

def env(m, a, rr):
    e = np.ones(m); ai = min(m // 2, max(1, int(a * SR))); ri = min(m // 2, max(1, int(rr * SR)))
    e[:ai] = np.linspace(0, 1, ai) ** 2; e[-ri:] *= np.linspace(1, 0, ri) ** 2
    return e
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, btype="low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, btype="high", fs=SR, output="sos"), x)
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

def chop():
    tt = np.arange(int(0.35 * SR)) / SR
    s = bp(rng.normal(0, 1, len(tt)), 300, 2500) * np.exp(-28 * tt) + 0.8 * np.sin(2 * np.pi * 140 * tt) * np.exp(-18 * tt)
    return norm(s)

def crackle(dur):
    m = int(dur * SR); out = lp(rng.normal(0, 1, m), 500) * 0.5
    imp = np.zeros(m); idx = rng.integers(0, m, int(dur * 70)); imp[idx] = rng.uniform(-1, 1, len(idx))
    out += bp(imp, 1500, 7000) * 6
    return norm(out) * env(m, 0.8, 1.0)

def shot():
    tt = np.arange(int(0.5 * SR)) / SR
    s = hp(rng.normal(0, 1, len(tt)), 600) * np.exp(-40 * tt) + lp(rng.normal(0, 1, len(tt)), 200) * np.exp(-12 * tt) * 1.5
    return norm(lp(s, 3000))

def hum(dur, rise=0.0):
    tt = np.arange(int(dur * SR)) / SR
    f = 110 + rise * 220 * (1 - np.exp(-tt * 4))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(f * 2.0) / SR)
    s *= 0.8 + 0.2 * np.sin(2 * np.pi * 7 * tt)
    return norm(s) * env(len(tt), 0.3, 0.6)

tt = np.arange(n) / SR
drone = (np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.4 * tt + 1)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * tt))
drone += 0.5 * bp(rng.normal(0, 1, n), 200, 800)
add(norm(drone) * env(n, 1.0, 1.0), 0, 0, 0.035)

# 1 map
add(whoosh(1.4, 200, 2500), 0.1, 0, 0.07)
for k in range(len(r.SPOTS)):
    add(tick(1800 + 40 * k, 0.04), 1.5 + 0.045 * k, (r.SPOTS[k][0] / 40), 0.015)
add(ping(660, 1.0, 4), 0.9, 0, 0.035)
# 2 trees
add(whoosh(0.6), 2.5, 0, 0.09)
for k in range(28):
    add(tick(2400 + 30 * k), 3.18 + 0.87 * (k / 28) ** 1.5, 0, 0.018)
add(ping(880, 0.8), 4.05, 0, 0.04)
for c in r.CHOPS:
    add(chop(), c, 0.2, 0.09)
for k, tk in r.KILL2.items():
    add(tick(1200, 0.03), tk, (r.GRID2[k][0] - 540) / 600, 0.02)
add(boom(1.2, 70), r.FALL + 0.55, -0.2, 0.08)
# 3 crops
add(whoosh(0.7, 200, 3000), 5.2, 0, 0.09)
add(ping(990, 0.8), 5.75, 0.4, 0.04)
add(ping(880, 0.8), 6.70, -0.4, 0.04)
for k in range(len(r.SPOTS)):
    add(whoosh(0.5, 900, 5000), 7.2 + 0.08 * k + 0.4, 0, 0.012)
for k in range(32):
    add(tick(2200 + 25 * k), 7.40 + 1.22 * (k / 32) ** 1.5, 0, 0.018)
add(boom(0.8, 80), 8.62, 0, 0.06)
for j in range(4):
    add(tick(2600, 0.05), 9.45 + 0.28 * j, (1.5 - j) * 0.3, 0.025)
# 4 window
add(whoosh(0.8, 200, 4000), 11.15, 0, 0.1)
add(boom(1.6, 50), 11.85, 0, 0.11)
add(crackle(6.0), 11.9, 0.1, 0.035)
for k in range(30):
    add(tick(2000 + 20 * k, 0.035), 12.62 + 1.5 * (k / 30) ** 1.2, 0, 0.014)
add(ping(740, 0.8), 14.28, 0, 0.035)
for k in range(30):
    add(tick(1500, 0.03), r.CAL_T0 + (r.CAL_T1 - r.CAL_T0) * k / 30, 0.3, 0.012)
# 5 hologram
add(whoosh(0.7, 200, 3000), 17.6, 0, 0.1)
add(hum(1.2, 1.0), 18.0, 0, 0.05)
add(hum(13.6) * 0.5, 18.4, 0, 0.03)
for k in range(32):
    add(tick(2300 + 20 * k), 19.25 + 1.75 * (k / 32) ** 1.5, 0, 0.018)
add(boom(0.9, 75), 21.0, 0, 0.06)
add(ping(880, 0.8), 22.25, 0.4, 0.04)
add(ping(784, 0.8), 23.45, -0.4, 0.04)
add(whoosh(0.7), 24.3, 0, 0.08)
for lbl, kind, t0 in r.CATS:
    add(tick(3000, 0.04), t0 - 0.1, 0, 0.025)
    if kind == "fire": add(crackle(1.6), t0, 0.2, 0.04)
    elif kind == "vandal": add(boom(0.5, 120), t0, -0.2, 0.06)
    elif kind == "gun":
        for k in range(3): add(shot(), t0 + k / 3.0, 0.3, 0.045)
    elif kind == "fist": add(chop(), t0 + 0.05, -0.2, 0.07)
    else: add(ping(990, 0.6), t0, 0, 0.03)
add(boom(2.2, 45), 31.6, 0, 0.07)

mix = np.clip(np.stack([L, R], 1), -1, 1)
print("sfx peak", np.abs(mix).max())
w = wave.open(os.path.join(HERE, "sfx.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
