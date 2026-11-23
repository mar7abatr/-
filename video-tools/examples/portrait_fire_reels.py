import math, sys
import numpy as np
import cairo
from PIL import Image, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 12.0
N = int(DUR * FPS)
WORK = "/tmp/w3"

def hexc(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
OLIVE = hexc("896829"); DARK = hexc("1D1D1D"); HL = hexc("C7973B")

def clamp(v, a=0.0, b=1.0): return a if v < a else b if v > b else v
def seg(t, a, b): return clamp((t - a) / (b - a))
def eio(p): return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
def eout(p): return 1 - (1 - p) ** 3
def lerp(a, b, p): return a + (b - a) * p
def rnd(i, k=0):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)

EXPL = [0.7, 4.1, 6.9, 9.6]
IMPACT = [(830, 330), (110, 560), (300, 420), (1000, 520)]
SPEC = np.load(f"{WORK}/spec.npy"); RMS = np.load(f"{WORK}/rms.npy")

# ---------------------------------------------------------------- shared FX (full-res coordinates)
def fireball(ctx, x, y, age, size=1.0):
    if age < 0: return
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    if age < 0.35:
        a = 1 - age / 0.35
        g = cairo.RadialGradient(x, y, 0, x, y, 700 * size)
        g.add_color_stop_rgba(0, 1, 0.95, 0.8, 0.8 * a); g.add_color_stop_rgba(0.3, 1, 0.6, 0.2, 0.35 * a); g.add_color_stop_rgba(1, 1, 0.5, 0.1, 0)
        ctx.set_source(g); ctx.paint()
    if age < 1.6:
        p = age / 1.6
        r = (40 + 150 * eout(min(1, age / 0.4))) * size
        a = (1 - p) ** 1.3
        cy = y - 60 * p * size
        g = cairo.RadialGradient(x, cy, 0, x, cy, r)
        g.add_color_stop_rgba(0, 1, 0.96, 0.8, a); g.add_color_stop_rgba(0.45, 1, 0.55, 0.12, 0.85 * a); g.add_color_stop_rgba(1, 0.7, 0.2, 0.05, 0)
        ctx.set_source(g); ctx.arc(x, cy, r, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    if age < 1.4:
        for k in range(22):
            ang = -math.pi * (0.05 + 0.9 * rnd(k, x))
            v = (300 + 500 * rnd(k, y)) * size
            px = x + math.cos(ang) * v * age; py = y + math.sin(ang) * v * age + 700 * age * age
            a = 1 - age / 1.4
            ctx.set_source_rgba(1, 0.75, 0.35, a); ctx.arc(px, py, 4 * size, 0, 2 * math.pi); ctx.fill()

def smoke_burst(ctx, x, y, age, size=1.0, life=5.0, n=9, alpha=0.6):
    if age < 0.05: return
    for k in range(n):
        a_ = age - k * 0.1
        if a_ <= 0: continue
        p = a_ / life
        if p >= 1: continue
        px = x + (rnd(k, x) - 0.5) * 120 * size + 120 * p * size
        py = y - (40 + 420 * eout(min(1, p * 1.3))) * size
        r = (60 + 200 * p) * size
        a = alpha * math.sin(math.pi * min(1, p * 1.1)) ** 0.8
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, 0.1, 0.09, 0.08, a); g.add_color_stop_rgba(1, 0.08, 0.08, 0.08, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()

def flames(ctx, x, y, w, strength, t, seed, n=30, height=200):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for i in range(n):
        Lf = 0.55 + 0.5 * rnd(i, seed)
        age = (t + rnd(i, seed + 1) * Lf) % Lf
        u = age / Lf
        bx = x + (rnd(i, seed + 2) - 0.5) * w
        px = bx + math.sin(t * 5 + i) * 9 * u + (rnd(i, seed + 3) - 0.5) * 24 * u
        py = y - u * height * strength * (0.7 + 0.5 * rnd(i, seed + 4))
        r = (18 + 34 * strength) * (1 - u) ** 0.7 + 4
        c0 = (1, 0.92, 0.65) if u < 0.25 else (1, 0.58, 0.16) if u < 0.6 else (0.75, 0.25, 0.06)
        a = (1 - u) * 0.6
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, *c0, a); g.add_color_stop_rgba(1, c0[0], c0[1] * 0.5, 0, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def smoke_column(ctx, x, y, t, seed, n=16, size=1.0, alpha=0.5, drift=200, rise=900):
    for i in range(n):
        Lc = 4.0 + 2.0 * rnd(i, seed)
        age = (t + rnd(i, seed + 1) * Lc) % Lc
        u = age / Lc
        px = x + (rnd(i, seed + 2) - 0.5) * 80 * size + u * drift * size + math.sin(t * 0.6 + i) * 25 * u
        py = y - u * rise * size
        r = (60 + 220 * u) * size
        a = alpha * math.sin(math.pi * u)
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, 0.11, 0.1, 0.09, a); g.add_color_stop_rgba(1, 0.09, 0.09, 0.09, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()

def flick(t, k):
    return 0.65 + 0.2 * math.sin(t * 13 + k) + 0.15 * math.sin(t * 29 + k * 2.3)

# ---------------------------------------------------------------- burning building (background, blurred)
GROUND = 1560
ROOF = 210
MAIN = [(150, ROOF), (520, ROOF), (560, ROOF - 35), (640, ROOF), (700, ROOF), (760, ROOF + 90), (820, ROOF + 70), (880, ROOF + 210),
        (930, ROOF + 270), (965, ROOF + 390), (965, GROUND), (150, GROUND)]
HOLES = [[(330, 480), (420, 440), (470, 500), (440, 580), (360, 570)],
         [(640, 790), (760, 760), (800, 840), (720, 910), (650, 870)],
         [(220, 1180), (300, 1160), (320, 1230), (240, 1250)]]

def poly(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    ctx.close_path()

def side_building(ctx, x0, x1, top, shade, seed, t, broken=None):
    pts = [(x0, top), (x1, top)] if broken is None else broken
    pts = pts + [(x1, GROUND), (x0, GROUND)]
    poly(ctx, pts); path = ctx.copy_path()
    ctx.set_source_rgb(shade, shade * 0.95, shade * 0.9); ctx.fill()
    ctx.save(); ctx.append_path(path); ctx.clip()
    k = 0
    for yy in range(int(top) + 30, GROUND - 40, 95):
        for xx in range(int(x0) + 22, int(x1) - 40, 70):
            k += 1; r = rnd(k, seed)
            if r > 0.86:
                g = cairo.RadialGradient(xx + 20, yy + 30, 0, xx + 20, yy + 30, 45)
                g.add_color_stop_rgba(0, 1, 0.6, 0.2, 0.85 * flick(t, k + seed)); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
                ctx.set_source(g); ctx.rectangle(xx, yy, 40, 55); ctx.fill()
            else:
                ctx.set_source_rgba(0.03, 0.03, 0.03, 0.9); ctx.rectangle(xx, yy, 40, 55); ctx.fill()
    ctx.restore()

def draw_building_scene(ctx, t):
    # sky lit by fire
    g = cairo.LinearGradient(0, 0, 0, GROUND)
    g.add_color_stop_rgb(0, 0.045, 0.04, 0.04); g.add_color_stop_rgb(0.45, 0.11, 0.07, 0.05)
    g.add_color_stop_rgb(0.85, 0.36, 0.16, 0.06); g.add_color_stop_rgb(1, 0.5, 0.22, 0.07)
    ctx.set_source(g); ctx.paint()
    # far skyline
    ctx.set_source_rgb(0.1, 0.08, 0.07)
    xx = -100; k = 0
    while xx < W + 100:
        k += 1; w = 90 + 80 * rnd(k, 3); h = 260 + 300 * rnd(k, 4)
        ctx.rectangle(xx, GROUND - h - 120, w, h + 200); xx += w - 10
    ctx.fill()
    smoke_column(ctx, 820, ROOF + 40, t, 1, n=18, size=1.3, alpha=0.55, drift=260)
    smoke_column(ctx, 100, 480, t, 5, n=12, size=1.0, alpha=0.45, drift=180)
    side_building(ctx, -60, 250, 440, 0.12, 11, t, broken=[(-60, 400), (120, 400), (180, 480), (250, 520)])
    side_building(ctx, 920, 1160, 360, 0.11, 17, t)
    # main building facade
    poly(ctx, MAIN); path = ctx.copy_path()
    g = cairo.LinearGradient(0, ROOF, 0, GROUND)
    g.add_color_stop_rgb(0, 0.2, 0.18, 0.165); g.add_color_stop_rgb(1, 0.28, 0.19, 0.13)
    ctx.set_source(g); ctx.fill()
    ctx.save(); ctx.append_path(path); ctx.clip()
    for yy in range(ROOF, GROUND, 112):
        ctx.set_source_rgba(0.3, 0.27, 0.24, 1); ctx.rectangle(150, yy, 820, 12); ctx.fill()
    k = 0
    for yy in range(ROOF + 32, GROUND - 60, 112):
        for xx in range(178, 950, 88):
            k += 1; r = rnd(k, 7)
            if r > 0.72:
                g = cairo.RadialGradient(xx + 25, yy + 50, 0, xx + 25, yy + 50, 70)
                g.add_color_stop_rgba(0, 1, 0.75, 0.3, 0.95 * flick(t, k)); g.add_color_stop_rgba(1, 1, 0.38, 0.06, 0)
                ctx.set_source(g); ctx.rectangle(xx, yy, 50, 66); ctx.fill()
                g = cairo.RadialGradient(xx + 25, yy - 10, 0, xx + 25, yy - 10, 60)
                g.add_color_stop_rgba(0, 0, 0, 0, 0.7); g.add_color_stop_rgba(1, 0, 0, 0, 0)
                ctx.set_source(g); ctx.rectangle(xx - 25, yy - 60, 100, 60); ctx.fill()
            else:
                ctx.set_source_rgba(0.025, 0.022, 0.02, 1); ctx.rectangle(xx, yy, 50, 66); ctx.fill()
    for hole in HOLES:
        poly(ctx, hole); ctx.set_source_rgb(0.02, 0.015, 0.012); ctx.fill_preserve()
        ctx.set_source_rgba(1, 0.5, 0.15, 0.6 * flick(t, len(hole))); ctx.set_line_width(5); ctx.stroke()
    # fire wash from below
    ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.LinearGradient(0, GROUND, 0, 700)
    g.add_color_stop_rgba(0, 1, 0.45, 0.12, 0.28 * flick(t, 2)); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
    ctx.set_source(g); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.restore()
    # flames on the broken roof edge, windows and holes
    for i, (x, y) in enumerate(MAIN[3:10]):
        flames(ctx, x, y + 10, 70, 1.1, t, 40 + i, n=22, height=230)
    flames(ctx, 400, 540, 110, 1.0, t, 61, n=26)
    flames(ctx, 720, 860, 130, 1.1, t, 62, n=26)
    flames(ctx, 270, 1215, 80, 0.8, t, 63, n=16)
    flames(ctx, 120, 440, 120, 0.9, t, 64, n=18)
    # rubble + ground fires
    ctx.set_source_rgb(0.06, 0.05, 0.045); ctx.rectangle(-100, GROUND, W + 200, H - GROUND + 100); ctx.fill()
    for k in range(40):
        rx = -80 + rnd(k, 21) * (W + 160); sz = 30 + 70 * rnd(k, 22)
        c = 0.1 + 0.08 * rnd(k, 23)
        ctx.set_source_rgb(c, c * 0.9, c * 0.8)
        ctx.move_to(rx - sz, GROUND + 20); ctx.line_to(rx - sz * 0.3, GROUND - sz * 0.6); ctx.line_to(rx + sz * 0.6, GROUND - sz * 0.3); ctx.line_to(rx + sz, GROUND + 20); ctx.close_path(); ctx.fill()
    for k, x in enumerate((60, 330, 610, 900, 1040)):
        flames(ctx, x, GROUND + 10, 160, 1.0, t, 80 + k, n=22, height=230)
    smoke_column(ctx, 560, 1000, t, 9, n=10, size=0.9, alpha=0.3, drift=120, rise=700)
    # strikes: incoming missile, fireball, smoke
    for (te, (ix, iy)) in zip(EXPL, IMPACT):
        a = t - te
        if -0.45 <= a < 0:
            u = (a + 0.45) / 0.45
            sx, sy = ix - 420, iy - 1100
            px, py = lerp(sx, ix, u), lerp(sy, iy, u)
            g = cairo.LinearGradient(px, py, px - 0.4 * (ix - sx), py - 0.4 * (iy - sy))
            g.add_color_stop_rgba(0, 1, 0.95, 0.8, 1); g.add_color_stop_rgba(1, 1, 0.6, 0.2, 0)
            ctx.set_source(g); ctx.set_line_width(10)
            ctx.move_to(px, py); ctx.line_to(px - 0.4 * (ix - sx), py - 0.4 * (iy - sy)); ctx.stroke()
            ctx.set_source_rgba(1, 1, 0.9, 1); ctx.arc(px, py, 9, 0, 2 * math.pi); ctx.fill()
        smoke_burst(ctx, ix, iy, a, 1.6)
        fireball(ctx, ix, iy, a, 2.2)

def shake(t):
    sx = sy = 0.0
    for te in EXPL:
        a = t - te
        if 0 <= a < 0.9:
            e = math.exp(-a * 5) * (22 if te < 1 else 15)
            sx += e * math.sin(a * 63 + te); sy += e * math.cos(a * 51 + te * 2)
    return sx, sy

def flash(t):
    f = 0.0
    for te in EXPL:
        a = t - te
        if a >= 0: f = max(f, math.exp(-a * 4.5))
    return f

# ---------------------------------------------------------------- person assets
S = 1.22
DX, DY = 540 - 540 * S, 1920 - 1280 * S + 10
def to_surface(rgba):
    a = rgba.astype(np.float32)
    al = a[..., 3:4] / 255
    bgra = np.dstack([a[..., 2] * al[..., 0], a[..., 1] * al[..., 0], a[..., 0] * al[..., 0], a[..., 3]]).astype(np.uint8)
    h, w = bgra.shape[:2]
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
    return cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)

cut = Image.open(f"{WORK}/cut_birefnet-portrait.png").convert("RGBA")
cw, ch = int(cut.width * S), int(cut.height * S)
cut = cut.resize((cw, ch), Image.LANCZOS)
rgb = cut.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=2))
A = np.asarray(cut)[..., 3].astype(np.float32) / 255
P = np.asarray(rgb).astype(np.float32)
# grade into the night/fire scene: warmer, slightly darker, lower body falls off
yy = np.linspace(0, 1, ch)[:, None, None]
fall = np.clip(1.0 - 0.5 * np.clip((yy - 0.5) / 0.5, 0, 1) ** 1.3, 0.45, 1.0)
P = P * np.array([1.0, 0.95, 0.88]) * 0.93 * fall
P = (P - 128) * 1.06 + 128
PERSON = to_surface(np.dstack([np.clip(P, 0, 255), A * 255]))
# rim light: inner edge band of the silhouette
Ai = Image.fromarray((A * 255).astype(np.uint8))
blur = np.asarray(Ai.filter(ImageFilter.GaussianBlur(9))).astype(np.float32) / 255
rim = np.clip((A - blur) * 2.2, 0, 1) * A
shadow_src = Ai
RIM = to_surface(np.dstack([np.full_like(A, 255), np.full_like(A, 140), np.full_like(A, 45), rim * 255]))
shadow = np.asarray(Ai.filter(ImageFilter.GaussianBlur(40))).astype(np.float32)
SHADOW = to_surface(np.dstack([np.zeros_like(A), np.zeros_like(A), np.zeros_like(A), shadow]))

HEAD = (DX + 505 * S, DY + 215 * S)
CC = (DX + 505 * S, DY + 300 * S)   # circle centre: behind head / neck
CR = 400

# ---------------------------------------------------------------- circle + waves
def draw_circle(ctx, t, i):
    p = seg(t, 0.45, 1.9)
    if p <= 0: return
    cx, cy = CC
    e = eout(p)
    lvl = RMS[min(i, len(RMS) - 1)]
    # glow disk
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, CR * 1.25)
    g.add_color_stop_rgba(0, *OLIVE, 0.38 * e); g.add_color_stop_rgba(0.6, *OLIVE, 0.14 * e); g.add_color_stop_rgba(1, *OLIVE, 0)
    ctx.set_source(g); ctx.arc(cx, cy, CR * 1.25, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(0.07, 0.07, 0.07, 0.55 * e); ctx.arc(cx, cy, CR - 6, 0, 2 * math.pi); ctx.fill()
    # pulse ring
    for ph in (0.0, 0.5):
        q = ((t * 0.55 + ph) % 1.0)
        ctx.set_source_rgba(*HL, 0.35 * (1 - q) * e); ctx.set_line_width(2)
        ctx.arc(cx, cy, CR + 10 + 160 * q, 0, 2 * math.pi); ctx.stroke()
    # main ring drawn on
    ctx.set_source_rgba(*HL, 0.95); ctx.set_line_width(3.5)
    ctx.arc(cx, cy, CR, -math.pi / 2, -math.pi / 2 + 2 * math.pi * e); ctx.stroke()
    # rotating thick arcs
    for k, (r, w, span, spd, col, a) in enumerate(((CR - 22, 10, 1.1, 0.35, OLIVE, 0.95), (CR - 22, 10, 0.5, 0.35, OLIVE, 0.95),
                                                   (CR + 26, 4, 1.6, -0.22, HL, 0.85), (CR - 48, 3, 2.2, 0.6, HL, 0.5))):
        a0 = t * spd + k * 2.1 + (math.pi if k == 1 else 0)
        ctx.set_source_rgba(*col, a * e); ctx.set_line_width(w)
        ctx.arc(cx, cy, r, a0, a0 + span * e); ctx.stroke()
    # dashed outer ring
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(-t * 0.18)
    ctx.set_source_rgba(*HL, 0.5 * e); ctx.set_line_width(2); ctx.set_dash([3, 12])
    ctx.arc(0, 0, CR + 46, 0, 2 * math.pi * e); ctx.stroke(); ctx.set_dash([]); ctx.restore()
    # ticks
    for k in range(72):
        if k / 72 > e: break
        ang = k / 72 * 2 * math.pi - math.pi / 2
        L = 14 if k % 6 == 0 else 7
        ctx.set_source_rgba(*HL, 0.55); ctx.set_line_width(2 if k % 6 == 0 else 1.2)
        ctx.move_to(cx + math.cos(ang) * (CR - 34), cy + math.sin(ang) * (CR - 34))
        ctx.line_to(cx + math.cos(ang) * (CR - 34 - L), cy + math.sin(ang) * (CR - 34 - L)); ctx.stroke()
    # audio-reactive frequency bars around the ring (mirrored left/right)
    sp = SPEC[min(i, len(SPEC) - 1)]
    nb = 90
    ba = seg(t, 0.9, 1.7)
    for k in range(nb):
        f = k / nb
        band = sp[int((1 - abs(2 * f - 1)) * 80) % len(sp)]
        idle = 0.18 + 0.12 * math.sin(t * 4.2 + k * 0.55) + 0.08 * math.sin(t * 7.1 + k * 1.3)
        amp = (12 + 95 * max(idle, band * 0.95) * (0.7 + 0.6 * lvl)) * ba
        ang = f * 2 * math.pi - math.pi / 2
        r0 = CR + 60
        ca, sa = math.cos(ang), math.sin(ang)
        col = HL if band > 0.55 else OLIVE
        ctx.set_source_rgba(*col, 0.9 * ba); ctx.set_line_width(5)
        ctx.move_to(cx + ca * r0, cy + sa * r0); ctx.line_to(cx + ca * (r0 + amp), cy + sa * (r0 + amp)); ctx.stroke()

def draw_waves(ctx, t, i):
    a = seg(t, 0.9, 1.8)
    if a <= 0: return
    lvl = RMS[min(i, len(RMS) - 1)]
    cy = CC[1] + 30
    for k, (amp, fr, sp, ph, col, lw, al) in enumerate(((70, 0.010, 2.2, 0, HL, 3, 0.9), (52, 0.016, -3.0, 1.3, OLIVE, 2.5, 0.85),
                                                        (34, 0.024, 4.1, 2.1, (1, 1, 1), 1.5, 0.45), (90, 0.006, 1.4, 0.7, OLIVE, 2, 0.5))):
        A_ = amp * (0.55 + 0.9 * lvl) * a
        ctx.move_to(-20, cy)
        for x in range(-20, W + 21, 6):
            env = math.exp(-((x - W / 2) / 420) ** 2) * 0.75 + 0.25
            y = cy + A_ * env * (math.sin(x * fr + t * sp + ph) * 0.7 + 0.3 * math.sin(x * fr * 2.7 - t * sp * 1.6 + ph))
            ctx.line_to(x, y)
        path = ctx.copy_path()
        ctx.set_source_rgba(*col, 0.25 * al * a); ctx.set_line_width(lw * 5); ctx.stroke()
        ctx.append_path(path); ctx.set_source_rgba(*col, al * a); ctx.set_line_width(lw); ctx.stroke()

# ---------------------------------------------------------------- person
def reveal_front(t):
    return lerp(H + 260, DY + 40 * S - 300, eio(seg(t, 1.0, 3.5)))

SOFT = 360
def draw_person(ctx, t):
    front = reveal_front(t)
    if front >= H + 250: return
    rise = 40 * (1 - eout(seg(t, 1.0, 3.8)))
    x0, y0 = DX, DY + rise
    def mask():
        g = cairo.LinearGradient(0, front - SOFT / 2, 0, front + SOFT / 2)
        g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 1)
        return g
    # soft dark halo to separate from the background
    ctx.set_source_surface(SHADOW, x0, y0 + 10); ctx.mask(mask())
    ctx.set_source_surface(PERSON, x0, y0); ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.mask(mask())
    # fire rim light, boosted by explosions
    rim = 0.22 + 0.07 * math.sin(t * 9) + 0.05 * math.sin(t * 23) + 0.55 * flash(t)
    ctx.push_group(); ctx.set_source_surface(RIM, x0, y0); ctx.mask(mask()); ctx.pop_group_to_source()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.paint_with_alpha(clamp(rim, 0, 0.9)); ctx.restore()
    # digital scan line at the reveal front, only on the silhouette
    if seg(t, 1.0, 3.5) < 1:
        ctx.save(); ctx.rectangle(0, front - 70, W, 70); ctx.clip()
        g = cairo.LinearGradient(0, front - 70, 0, front)
        g.add_color_stop_rgba(0, *HL, 0); g.add_color_stop_rgba(1, *HL, 0.55)
        ctx.set_source(g); ctx.mask_surface(PERSON, x0, y0); ctx.restore()
        ctx.save(); ctx.rectangle(0, front - 2, W, 4); ctx.clip()
        ctx.set_source_rgba(1, 0.9, 0.7, 0.95); ctx.mask_surface(PERSON, x0, y0); ctx.restore()

# ---------------------------------------------------------------- foreground
def draw_embers(ctx, t):
    for i in range(46):
        Lf = 3.0 + 3.0 * rnd(i, 1)
        age = (t + rnd(i, 2) * Lf) % Lf
        u = age / Lf
        px = rnd(i, 3) * W + math.sin(t * 1.3 + i) * 40 + u * 140
        py = H + 40 - u * (H + 200)
        r = 1.5 + 3.5 * rnd(i, 4)
        a = math.sin(math.pi * u) * (0.55 + 0.45 * math.sin(t * 9 + i * 3))
        g = cairo.RadialGradient(px, py, 0, px, py, r * 3.5)
        g.add_color_stop_rgba(0, 1, 0.8, 0.45, max(0, a)); g.add_color_stop_rgba(1, 1, 0.5, 0.1, 0)
        ctx.set_source(g); ctx.arc(px, py, r * 3.5, 0, 2 * math.pi); ctx.fill()

def corner_frame(ctx, x, y, w, h, alpha, L=50, lw=2):
    ctx.set_source_rgba(*HL, alpha); ctx.set_line_width(lw)
    for cx_, cy_, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        ctx.move_to(cx_, cy_ + sy * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx * L, cy_); ctx.stroke()

# ---------------------------------------------------------------- post
yy_, xx_ = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2)
VIG = np.clip(1.0 - 0.5 * np.clip(_d - 0.45, 0, None) ** 1.5, 0.35, 1.0).astype(np.float32)[..., None]
del yy_, xx_, _d
_rng = np.random.default_rng(7)
GRAIN = [_rng.normal(0, 2.4, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]

def surf_array(surf, w=W, h=H):
    return np.ndarray((h, w, 4), np.uint8, buffer=surf.get_data())

BW, BH = W // 2, H // 2
def render_bg(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, BW, BH)
    c = cairo.Context(s)
    sx, sy = shake(t)
    z = 1.08 + 0.07 * (t / DUR)
    c.scale(0.5, 0.5)
    c.translate(W / 2 + sx, H / 2 + sy); c.scale(z, z); c.translate(-W / 2 - 20 * math.sin(t * 0.2), -H / 2)
    draw_building_scene(c, t)
    s.flush()
    im = Image.fromarray(surf_array(s, BW, BH).copy(), "RGBA").filter(ImageFilter.GaussianBlur(7))
    return np.asarray(im.resize((W, H), Image.BILINEAR))

def render(i):
    t = i / FPS
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    arr = surf_array(surf)
    arr[:] = render_bg(t); arr[..., 3] = 255
    surf.mark_dirty()
    ctx = cairo.Context(surf)
    # darken + warm grade over the blurred background so the subject reads
    ctx.set_source_rgba(0.05, 0.04, 0.035, 0.18); ctx.paint()
    sx, sy = shake(t)
    z = 1.0 + 0.045 * eio(seg(t, 0, DUR))
    ctx.save()
    ctx.translate(W / 2 + sx * 0.35, H * 0.55 + sy * 0.35); ctx.scale(z, z); ctx.translate(-W / 2, -H * 0.55)
    draw_waves(ctx, t, i)
    draw_circle(ctx, t, i)
    draw_person(ctx, t)
    ctx.restore()
    # bottom fade so the cut-out meets the frame edge softly
    g = cairo.LinearGradient(0, H - 420, 0, H)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0.03, 0.025, 0.02, 0.85)
    ctx.set_source(g); ctx.rectangle(0, H - 420, W, 420); ctx.fill()
    draw_embers(ctx, t)
    fl = flash(t)
    if fl > 0.01:
        ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_rgba(1, 0.55, 0.2, 0.22 * fl); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)
    corner_frame(ctx, 34, 34, W - 68, H - 68, 0.45 * seg(t, 0.3, 1.2) * (1 - seg(t, 11.3, 11.8)))
    surf.flush()
    a = surf_array(surf)[..., :3].astype(np.float32)
    a *= VIG
    a += np.repeat(np.repeat(GRAIN[i % 6], 2, axis=0), 2, axis=1)
    a *= seg(t, 0.0, 0.5) * (1 - seg(t, 11.45, 11.98))
    return np.clip(a, 0, 255).astype(np.uint8)[..., ::-1].tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        import os; os.makedirs(f"{WORK}/stills", exist_ok=True)
        for ts in sys.argv[2:]:
            Image.frombytes("RGB", (W, H), render(int(round(float(ts) * FPS)))).save(f"{WORK}/stills/s_{float(ts):05.2f}.jpg", quality=90)
        print("stills ok")
    else:
        import subprocess
        from multiprocessing import Pool
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-preset", "slow", "-b:v", "16M", "-maxrate", "22M", "-bufsize", "32M",
                               "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", sys.argv[2]], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render, range(N), chunksize=3)):
                ff.stdin.write(fr)
                if k % 90 == 0: print("frame", k, flush=True)
        ff.stdin.close(); ff.wait(); print("done")
