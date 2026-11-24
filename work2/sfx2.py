"""Subtle sound design for the Oslo-areas reel, reusing the synth helpers from work/sfx.py's style."""
import numpy as np, wave, os, sys
from scipy.signal import butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["x", "none"]; sys.path.insert(0, HERE)
import render2 as r

SR = 48000; n = int(SR * r.DUR)
rng = np.random.default_rng(9)
L = np.zeros(n); Rr = np.zeros(n)

def add(sig, t, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(n, i + len(sig))
    if j <= i or i < 0: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt(0.5 * (1 - pan)); Rr[i:j] += s * np.sqrt(0.5 * (1 + pan))
def env(m, a, rr):
    e = np.ones(m); ai = min(m // 2, max(1, int(a * SR))); ri = min(m // 2, max(1, int(rr * SR)))
    e[:ai] = np.linspace(0, 1, ai) ** 2; e[-ri:] *= np.linspace(1, 0, ri) ** 2
    return e
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)
def norm(x): return x / (np.abs(x).max() + 1e-9)
def whoosh(dur, lo=300, hi=3500):
    m = int(dur * SR); x = rng.normal(0, 1, m); out = np.zeros(m); bands = np.geomspace(lo, hi, 7)
    pos = np.sin(np.linspace(0, np.pi, m))
    for k in range(6): out += bp(x, bands[k], bands[k + 1]) * np.exp(-((pos - k / 5) ** 2) / 0.05)
    return norm(out * np.sin(np.linspace(0, np.pi, m)) ** 1.5)
def ping(f, dur=0.9, decay=5.0):
    tt = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-decay * tt) * env(len(tt), 0.004, 0.05)
    d = int(0.11 * SR); o = s.copy(); o[d:] += 0.35 * s[:-d]
    return norm(o)
def tick(f=2200, dur=0.045):
    tt = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * f * tt) * np.exp(-70 * tt)
def boom(dur=1.2, f0=60):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * np.exp(-tt * 1.3) + 28
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.6 * tt) + lp(rng.normal(0, 1, len(tt)), 700) * np.exp(-5 * tt) * 0.6
    return norm(s * env(len(s), 0.006, 0.3))
def scan(dur):
    m = int(dur * SR); tt = np.arange(m) / SR
    s = bp(rng.normal(0, 1, m), 1500, 5000) * 0.4 + np.sin(2 * np.pi * (600 + 500 * tt / dur) * tt) * 0.3
    return norm(s) * env(m, 0.1, 0.2)

tt = np.arange(n) / SR
drone = (np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.4 * tt + 1)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * tt))
drone += 0.5 * bp(rng.normal(0, 1, n), 200, 800)
add(norm(drone) * env(n, 1.0, 0.6), 0, 0, 0.035)

add(whoosh(1.4, 200, 2500), 0.05, 0, 0.07)
for k, t0 in r.SPOT_T.items():
    add(tick(1700 + 35 * k, 0.04), t0, (r.SPOTS[k][0][0] / 40), 0.02)
add(boom(0.9, 70), 2.10, 0, 0.05)
add(ping(880, 0.8), 3.04, 0.4, 0.04)
add(whoosh(0.6), 4.55, 0, 0.05)
for key, t0 in r.REV.items():
    add(scan(0.75), t0, 0.2, 0.02)
    add(tick(2600, 0.05), t0, 0.4, 0.03)
add(ping(660, 1.2, 3.5), r.A_FOCUS, 0, 0.05)
add(boom(0.8, 80), r.A_FOCUS, 0, 0.04)
add(whoosh(0.6, 300, 3000), 6.6, 0, 0.06)
add(ping(784, 0.9), 7.4, 0, 0.035)
for lbl, fn, t0, x in r.ITEMS:
    add(ping(990 if x > 540 else 880, 0.7), t0, (x - 540) / 600, 0.035)
add(whoosh(1.0, 200, 2500), 12.9, 0, 0.04)

mix = np.clip(np.stack([L, Rr], 1), -1, 1)
print("sfx peak", np.abs(mix).max())
w = wave.open(os.path.join(HERE, "sfx.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
