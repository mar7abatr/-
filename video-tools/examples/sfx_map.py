"""Subtle synthesized sound design, mixed under the original voice-over."""
import numpy as np, wave
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 20.0
n = int(SR * DUR)
rng = np.random.default_rng(3)
L = np.zeros(n); Rch = np.zeros(n)

def add(sig, t, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(n, i + len(sig))
    if j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt(0.5 * (1 - pan)); Rch[i:j] += s * np.sqrt(0.5 * (1 + pan))

def env(m, a, r):
    e = np.ones(m); ai = max(1, int(a * SR)); ri = max(1, int(r * SR))
    e[:ai] = np.linspace(0, 1, ai) ** 2; e[-ri:] *= np.linspace(1, 0, ri) ** 2
    return e

def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)

def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)

def whoosh(dur, lo=300, hi=3500):
    m = int(dur * SR); x = rng.normal(0, 1, m)
    # sweep: blend of bands following a rise/fall envelope
    out = np.zeros(m); bands = np.geomspace(lo, hi, 7)
    pos = np.sin(np.linspace(0, np.pi, m))
    for k in range(len(bands) - 1):
        y = bp(x, bands[k], bands[k + 1])
        centre = k / (len(bands) - 2)
        w = np.exp(-((pos - centre) ** 2) / 0.05)
        out += y * w
    e = np.sin(np.linspace(0, np.pi, m)) ** 1.5
    return out * e / (np.abs(out).max() + 1e-9)

def ping(f, dur=0.9, decay=5.0):
    tt = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-decay * tt)
    s *= env(len(s), 0.004, 0.05)
    # small echo
    d = int(0.11 * SR); out = s.copy(); out[d:] += 0.35 * s[:-d]
    return out / np.abs(out).max()

def tick(f=2200, dur=0.05):
    tt = np.arange(int(dur * SR)) / SR
    return np.sign(np.sin(2 * np.pi * f * tt)) * np.exp(-60 * tt) * 0.6 + np.sin(2 * np.pi * f / 2 * tt) * np.exp(-40 * tt) * 0.4

def boom(dur=1.6):
    tt = np.arange(int(dur * SR)) / SR
    f = 62 * np.exp(-tt * 1.2) + 30
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.8 * tt)
    s += lp(rng.normal(0, 1, len(tt)), 200) * np.exp(-6 * tt) * 0.5
    return s * env(len(s), 0.01, 0.3) / np.abs(s).max()

def rumble(dur):
    m = int(dur * SR); x = lp(rng.normal(0, 1, m), 140, 4)
    x += 0.3 * np.sin(2 * np.pi * 38 * np.arange(m) / SR) * (1 + 0.3 * np.sin(2 * np.pi * 7 * np.arange(m) / SR))
    return x * env(m, 0.5, 0.6) / np.abs(x).max()

# ambient drone bed
tt = np.arange(n) / SR
drone = (np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.4 * tt + 1) + 0.25 * np.sin(2 * np.pi * 110.3 * tt)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * tt))
drone += 0.6 * bp(rng.normal(0, 1, n), 200, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * tt))
drone = drone / np.abs(drone).max() * env(n, 1.5, 1.2)
add(drone, 0, 0, 0.045)

# camera moves
for t, d, g, pan in [(0.05, 2.0, 0.10, 0), (2.25, 1.7, 0.16, 0), (6.85, 1.0, 0.13, -0.3), (8.80, 1.1, 0.14, 0.3),
                     (10.70, 0.8, 0.10, 0.2), (12.30, 1.1, 0.14, 0), (15.55, 0.8, 0.12, -0.3), (17.70, 1.0, 0.13, 0.2),
                     (16.30, 0.6, 0.08, -0.4), (17.50, 0.6, 0.07, -0.4)]:
    add(whoosh(d), t, pan, g)
# hospital markers popping in
for i, t in enumerate([4.2, 4.3, 4.45, 4.55, 4.7, 4.8, 4.9, 5.0, 5.1, 5.15, 5.2, 5.25]):
    add(tick(2000 + 120 * (i % 4)), t, (i % 5 - 2) * 0.2, 0.05)
# named hospital: soft ping
for t, f in [(7.45, 880), (9.55, 988), (11.40, 1046)]:
    add(ping(f), t, 0, 0.09)
# media windows opening / closing
for t in [7.95, 9.80, 11.55, 14.50, 15.95]:
    add(whoosh(0.35, 1500, 8000), t - 0.05, -0.2, 0.08); add(tick(3000, 0.04), t + 0.25, -0.2, 0.06)
for t in [8.82, 12.05, 12.55, 15.55, 18.15]:
    add(whoosh(0.3, 1200, 6000), t, 0.2, 0.05)
# title & label
add(whoosh(0.5, 800, 6000), 3.40, 0.4, 0.07); add(tick(2600), 3.75, 0.4, 0.05)
add(tick(2400), 5.9, -0.3, 0.05)
# "and others" bursts
for i in range(10):
    add(tick(1800 + 80 * i, 0.04), 12.45 + i * 0.07, (i % 3 - 1) * 0.3, 0.035)
# claim: low hit, tanks rumble, sonar pings on arrival
add(boom(), 12.88, 0, 0.16)
add(rumble(1.8), 12.9, 0.1, 0.06)
for t, f in [(14.05, 1200), (14.25, 1150), (14.40, 1100)]:
    add(ping(f, 1.2, 3.5), t, 0, 0.06)
add(boom(1.4), 16.35, 0, 0.06)

mix = np.stack([L, Rch], 1)
peak = np.abs(mix).max()
print("sfx peak", peak)
mix = np.clip(mix, -1, 1)
w = wave.open("/tmp/work/sfx.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
