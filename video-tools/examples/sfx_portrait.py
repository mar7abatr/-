"""Sound design for video 3 + per-frame spectrum used to drive the frequency bars."""
import numpy as np, wave
from scipy.signal import butter, sosfilt

SR = 48000; DUR = 12.0; FPS = 30; n = int(SR * DUR)
rng = np.random.default_rng(9)
L = np.zeros(n); R = np.zeros(n)
EXPL = [0.7, 4.1, 6.9, 9.6]          # impact times (shared with render3.py)
EXPL_PAN = [0.5, -0.7, -0.1, 0.8]

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
def hp(x, f, o=2): return sosfilt(butter(o, f, btype="high", fs=SR, output="sos"), x)
def norm(x): return x / (np.abs(x).max() + 1e-9)

def boom(dur=2.4, f0=50):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * np.exp(-tt * 1.4) + 26
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.2 * tt)
    s += lp(rng.normal(0, 1, len(tt)), 700) * np.exp(-3.5 * tt) * 0.9
    s += hp(rng.normal(0, 1, len(tt)), 2500) * np.exp(-9 * tt) * 0.25   # debris crack
    # distant reflection tail
    d = int(0.23 * SR); o = s.copy(); o[d:] += 0.3 * lp(s[:-d], 400)
    return norm(o * env(len(o), 0.004, 0.6))

def incoming(dur=0.45):
    m = int(dur * SR); tt = np.arange(m) / SR
    f = 1400 - 900 * (tt / dur)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25 + bp(rng.normal(0, 1, m), 600, 3000)
    return norm(s * (tt / dur) ** 2)

def crackle(dur):
    m = int(dur * SR); out = lp(rng.normal(0, 1, m), 450) * 0.6
    imp = np.zeros(m); idx = rng.integers(0, m, int(dur * 90)); imp[idx] = rng.uniform(-1, 1, len(idx))
    out += bp(imp, 1200, 7000) * 6
    return norm(out) * env(m, 1.0, 0.8)

def riser(dur):
    m = int(dur * SR); tt = np.arange(m) / SR
    f = 110 + 220 * (tt / dur) ** 2
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    s = s * 0.5 + bp(rng.normal(0, 1, m), 500, 4000) * (tt / dur) * 0.8
    return norm(s * env(m, dur * 0.7, 0.25))

def sweep(dur=0.9):
    m = int(dur * SR); tt = np.arange(m) / SR
    f = 300 + 2600 * (tt / dur)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.5 * tt) * env(m, 0.01, 0.2))

def pulse(f=55, dur=0.9):
    tt = np.arange(int(dur * SR)) / SR
    return norm(np.sin(2 * np.pi * f * tt) * np.exp(-5 * tt) * env(len(tt), 0.005, 0.1))

tt = np.arange(n) / SR
drone = np.sin(2 * np.pi * 49 * tt) + 0.5 * np.sin(2 * np.pi * 73.5 * tt + 1) + 0.25 * np.sin(2 * np.pi * 98.2 * tt)
drone = drone * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * tt)) + 0.7 * bp(rng.normal(0, 1, n), 120, 500)
add(norm(drone) * env(n, 0.8, 1.2), 0, 0, 0.05)
add(crackle(DUR), 0, 0.15, 0.05)
for t, p in zip(EXPL, EXPL_PAN):
    add(incoming(), t - 0.45, p, 0.035)
    add(boom(), t, p, 0.17 if t < 1 else 0.13)
add(sweep(), 0.5, 0, 0.05)
add(riser(2.5), 0.95, 0, 0.07)
for t in np.arange(2.0, 11.5, 1.6):
    add(pulse(), t, 0, 0.06)
add(pulse(44, 2.0), 11.0, 0, 0.05)

mix = np.stack([L, R], 1)
mix = np.clip(mix / np.abs(mix).max() * 0.5, -1, 1)
w = wave.open("/tmp/w3/sfx.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()

# per-frame log-band spectrum (96 bands) for the frequency bars
mono = mix.mean(axis=1)
hop = SR // FPS; win = 4096; nb = 96
edges = np.geomspace(40, 12000, nb + 1)
freqs = np.fft.rfftfreq(win, 1 / SR)
spec = np.zeros((int(DUR * FPS), nb)); rms = np.zeros(int(DUR * FPS))
for i in range(int(DUR * FPS)):
    c = i * hop; seg = mono[max(0, c - win // 2): c + win // 2]
    seg = np.pad(seg, (0, win - len(seg)))
    mag = np.abs(np.fft.rfft(seg * np.hanning(win)))
    for k in range(nb):
        sel = (freqs >= edges[k]) & (freqs < edges[k + 1])
        spec[i, k] = mag[sel].mean() if sel.any() else 0
    rms[i] = np.sqrt((seg ** 2).mean())
spec = np.log1p(spec * 50); spec /= np.percentile(spec, 99.5); spec = np.clip(spec, 0, 1.2)
rms /= rms.max()
np.save("/tmp/w3/spec.npy", spec); np.save("/tmp/w3/rms.npy", rms)
print("ok", spec.shape, round(float(spec.mean()), 3))
