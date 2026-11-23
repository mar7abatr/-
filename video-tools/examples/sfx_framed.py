import numpy as np, wave, subprocess
from scipy.signal import butter, sosfilt
SR = 48000; DUR = 8.0; n = int(SR * DUR)
rng = np.random.default_rng(4)
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
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)
def norm(x): return x / (np.abs(x).max() + 1e-9)
def whoosh(dur, lo=300, hi=4000):
    m = int(dur * SR); x = rng.normal(0, 1, m); out = np.zeros(m); bands = np.geomspace(lo, hi, 7)
    pos = np.sin(np.linspace(0, np.pi, m))
    for k in range(6): out += bp(x, bands[k], bands[k + 1]) * np.exp(-((pos - k / 5) ** 2) / 0.05)
    return norm(out * np.sin(np.linspace(0, np.pi, m)) ** 1.5)
def ping(f, dur=0.9, decay=5.0):
    tt = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-decay * tt) * env(len(tt), 0.004, 0.05)
    d = int(0.11 * SR); o = s.copy(); o[d:] += 0.35 * s[:-d]; return norm(o)
def tick(f=2400, dur=0.04):
    tt = np.arange(int(dur * SR)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-70 * tt)
def hit(dur=1.6, f0=60):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * np.exp(-tt * 1.5) + 30
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-3 * tt) + lp(rng.normal(0, 1, len(tt)), 600) * np.exp(-6 * tt) * 0.5
    return norm(s * env(len(s), 0.004, 0.3))
def glitch(dur=0.35):
    m = int(dur * SR); x = rng.normal(0, 1, m)
    gate = (np.sin(2 * np.pi * 38 * np.arange(m) / SR) > 0).astype(float)
    return norm(bp(x, 1500, 7000) * gate * env(m, 0.01, 0.1))

# original Baptist-hospital audio (real explosion), first 3.8 s
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.15", "-t", "3.95", "-i", "/tmp/w4/src/ahli.mp4", "-vn", "-ac", "2", "-ar", str(SR),
                      "-f", "s16le", "-"], capture_output=True).stdout
ah = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, 2) / 32768
ah = ah * env(len(ah), 0.02, 0.4)[:, None]
m = min(n, len(ah))
L[:m] += ah[:m, 0] * 0.9; R[:m] += ah[:m, 1] * 0.9

tt = np.arange(n) / SR
drone = np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.4 * tt + 1) + 0.6 * bp(rng.normal(0, 1, n), 200, 800)
add(norm(drone) * env(n, 0.6, 0.8), 0, 0, 0.05)
add(whoosh(0.7), 0.0, 0, 0.10)                 # frame opens
add(ping(880), 0.78, -0.4, 0.07)               # locator pin
add(tick(), 1.0, 0.4, 0.06); add(tick(2600), 1.3, 0.4, 0.05)   # name plate
add(whoosh(0.8, 200, 3000), TR := 3.45, 0, 0.16)   # transition
add(glitch(), 3.75, 0, 0.05)
add(hit(), 3.9, 0, 0.14)
add(ping(988), 4.2, -0.4, 0.06)
add(tick(), 4.3, 0.4, 0.06); add(tick(2600), 4.6, 0.4, 0.05)
def blast(dur=2.6):
    """real-sounding strike: transient crack, low boom, debris rumble tail"""
    tt = np.arange(int(dur * SR)) / SR
    f = 55 * np.exp(-tt * 1.6) + 28
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.2 * tt)
    s += lp(rng.normal(0, 1, len(tt)), 900) * np.exp(-3.0 * tt) * 0.9
    s += bp(rng.normal(0, 1, len(tt)), 2000, 9000) * np.exp(-14 * tt) * 0.5
    s += lp(rng.normal(0, 1, len(tt)), 180) * np.exp(-1.2 * tt) * 0.35
    return norm(s * env(len(s), 0.002, 0.6))

add(whoosh(0.4, 900, 5000), 5.47 - 0.4, 0, 0.03)
add(blast(), 5.47, 0, 0.30)
add(whoosh(0.7, 200, 2500), 7.3, 0, 0.08)

mix = np.clip(np.stack([L, R], 1), -1, 1)
w = wave.open("/tmp/w4/audio.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print("peak", float(np.abs(mix).max()))
