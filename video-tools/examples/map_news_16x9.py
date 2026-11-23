import math, pickle, os, sys, glob
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw, ImageFilter

W, H, FPS = 1920, 1080, 30
DUR = 20.0
N = int(DUR * FPS)
WORK = "/tmp/work"

def hexc(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

OLIVE = hexc("896829")
DARK = hexc("1D1D1D")
HL = hexc("C7973B")       # brighter tint of 896829 for lines/highlights
SEA = hexc("151515")
LAND = hexc("232323")
WHITE = (1, 1, 1)

MAP = pickle.load(open(f"{WORK}/geo/map.pkl", "rb"))
HOSP = MAP["hosp"]
MAIN = ["nasser", "shifa", "kamal"]
NAMES = {"nasser": "مجمع ناصر الطبي", "shifa": "مجمع الشفاء الطبي", "kamal": "مستشفى كمال عدوان"}

# ---------------------------------------------------------------- easing / timing
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v

def seg(t, a, b):
    return clamp((t - a) / (b - a))

def eio(p):  # ease in-out cubic
    return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2

def eout(p):
    return 1 - (1 - p) ** 3

def ein(p):
    return p ** 3

def eback(p, s=1.6):
    p -= 1
    return 1 + p * p * ((s + 1) * p + s)

def lerp(a, b, p):
    return a + (b - a) * p

def pchip(ts, ys):
    ts = np.asarray(ts, float); ys = np.asarray(ys, float)
    h = np.diff(ts); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for k in range(1, len(ys) - 1):
        if d[k - 1] * d[k] <= 0:
            m[k] = 0
        else:
            w1 = 2 * h[k] + h[k - 1]; w2 = h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    def f(t):
        if t <= ts[0]: return ys[0]
        if t >= ts[-1]: return ys[-1]
        k = int(np.searchsorted(ts, t) - 1)
        s = (t - ts[k]) / h[k]
        h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s
        h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
        return h00 * ys[k] + h10 * h[k] * m[k] + h01 * ys[k + 1] + h11 * h[k] * m[k + 1]
    return f

# ---------------------------------------------------------------- camera (world km, zoom = px/km)
CAM = [
    (0.0, 3.0, -2.0, 2.6),
    (1.8, 2.0, -1.5, 3.4),
    (2.3, 1.6, -1.1, 4.3),
    (4.0, 1.2, -0.8, 20.5),
    (6.9, 1.4, -1.0, 22.0),
    (7.75, -11.50, 6.74, 60),     # مجمع ناصر
    (8.85, -11.30, 6.80, 63),
    (9.40, -4.2, -3.2, 30),       # flight dip
    (9.95, 2.86, -13.18, 60),     # الشفاء
    (10.75, 3.00, -13.20, 62),
    (11.45, 7.23, -14.71, 50),    # الشفاء + كمال عدوان
    (12.35, 7.40, -14.60, 52),
    (13.30, 1.0, -0.8, 21.0),     # وغيرها -> the whole strip
    (14.40, 1.5, -1.5, 22.0),
    (14.75, 2.5, -4.0, 24.0),
    (15.60, 2.7, -4.3, 25.0),
    (16.30, -15.58, 7.57, 40),    # Nasser (military use)
    (17.70, -15.40, 7.50, 43),
    (18.60, 1.2, -0.8, 21.5),
    (20.0, 1.2, -0.8, 20.0),
]
_ct = [c[0] for c in CAM]
fcx = pchip(_ct, [c[1] for c in CAM])
fcy = pchip(_ct, [c[2] for c in CAM])
fz = pchip(_ct, [math.log(c[3]) for c in CAM])

def camera(t):
    return fcx(t), fcy(t), math.exp(fz(t))

class View:
    def __init__(self, t):
        self.cx, self.cy, self.z = camera(t)
        # gentle hand-held drift in screen space
        self.ox = 5 * math.sin(t * 0.61) + 3 * math.sin(t * 1.37)
        self.oy = 4 * math.sin(t * 0.83 + 1.1) + 2 * math.sin(t * 1.9)
    def s(self, p):
        return (W / 2 + (p[0] - self.cx) * self.z + self.ox, H / 2 + (p[1] - self.cy) * self.z + self.oy)
    def apply(self, ctx):
        ctx.translate(W / 2 + self.ox, H / 2 + self.oy)
        ctx.scale(self.z, self.z)
        ctx.translate(-self.cx, -self.cy)

# ---------------------------------------------------------------- text
FONTS = {
    "black": f"{WORK}/fonts/black.otf", "bold": f"{WORK}/fonts/bold.ttf",
    "medium": f"{WORK}/fonts/medium.otf", "light": f"{WORK}/fonts/light.otf",
}
_tcache = {}

def pil_to_surface(im):
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    al = a[..., 3:4] / 255.0
    rgb = a[..., :3] * al
    bgra = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], a[..., 3]]).astype(np.uint8)
    h, w = bgra.shape[:2]
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8)
    buf[:, :w * 4] = bgra.reshape(h, w * 4)
    surf = cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)
    return surf

def text_surface(s, font, size, color=(255, 255, 255)):
    key = (s, font, size, color)
    if key in _tcache:
        return _tcache[key]
    f = ImageFont.truetype(FONTS[font], size, layout_engine=ImageFont.Layout.RAQM)
    bbox = f.getbbox(s, direction="rtl", language="ar")
    pad = 8
    w = bbox[2] - bbox[0] + pad * 2; h = bbox[3] - bbox[1] + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((pad - bbox[0], pad - bbox[1]), s, font=f, fill=color + (255,), direction="rtl", language="ar")
    surf = (pil_to_surface(im), w, h, pad)
    _tcache[key] = surf
    return surf

def draw_text(ctx, s, font, size, x, y, align="right", alpha=1.0, color=(255, 255, 255)):
    """(x, y) is the anchor at the vertical centre; align is where the anchor sits."""
    surf, w, h, pad = text_surface(s, font, size, color)
    if align == "right": x0 = x - w + pad
    elif align == "left": x0 = x - pad
    else: x0 = x - w / 2
    ctx.set_source_surface(surf, x0, y - h / 2)
    ctx.paint_with_alpha(alpha)
    return w - 2 * pad, h - 2 * pad

# ---------------------------------------------------------------- media
_mcache = {}
CLIPS = {k: sorted(glob.glob(f"{WORK}/clips/{k}/*.jpg")) for k in ("nasser", "shifa", "kamal")}

def load_surface(path):
    if path in _mcache:
        return _mcache[path]
    if len(_mcache) > 12:
        _mcache.pop(next(iter(_mcache)))
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    h, w = a.shape[:2]
    bgra = np.dstack([a[..., 2], a[..., 1], a[..., 0], np.full((h, w), 255, np.uint8)])
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
    s = (cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride), w, h)
    _mcache[path] = s
    return s

def media_surface(src, tl):
    if src[0] == "image":
        return load_surface(src[1])
    frames = CLIPS[src[1]]
    i = int(round((src[2] + max(0.0, tl)) * FPS))
    return load_surface(frames[min(i, len(frames) - 1)])

ASPECT = {"nasser": 1080 / 716, "shifa": 1080 / 624, "kamal": 1080 / 632, "shifa_img": 1600 / 1200}

def R(x, y, w, key):
    return (x, y, w, w / ASPECT[key])

# windows: marker, source, open, close, rect keyframes [(t, rect)], anchor (side, frac), elbow mode
WINDOWS = [
    dict(m="nasser", src=("clip", "nasser", 4.0), o=7.95, c=8.82, rects=[(0, R(150, 200, 720, "nasser"))],
         anchor=("right", 0.55), mode="h"),
    dict(m="shifa", src=("clip", "shifa", 7.0), o=9.80, c=12.05,
         rects=[(10.9, R(120, 175, 760, "shifa")), (11.45, R(110, 300, 520, "shifa"))],
         anchor=("right", 0.6), mode="h"),
    dict(m="kamal", src=("clip", "kamal", 1.0), o=11.55, c=12.55, rects=[(0, R(1230, 110, 600, "kamal"))],
         anchor=("bottom", 0.12), mode="v"),
    dict(m="shifa", src=("image", f"{WORK}/src/shifa.jpg"), o=14.50, c=15.55, rects=[(0, R(230, 90, 480, "shifa_img"))],
         anchor=("right", 0.75), mode="h", kb=True),
    dict(m="nasser", src=("clip", "nasser", 0.8), o=15.95, c=18.15,
         rects=[(16.35, R(300, 340, 600, "nasser")), (16.85, R(70, 205, 1000, "nasser")),
                (17.55, R(70, 205, 1000, "nasser")), (18.0, R(300, 340, 600, "nasser"))],
         anchor=("right", 0.5), mode="h"),
]

def rect_at(wd, t):
    ks = wd["rects"]
    if len(ks) == 1 or t <= ks[0][0]:
        return ks[0][1]
    for (t0, r0), (t1, r1) in zip(ks, ks[1:]):
        if t <= t1:
            p = eio(seg(t, t0, t1))
            return tuple(lerp(a, b, p) for a, b in zip(r0, r1))
    return ks[-1][1]

def anchor_pt(rect, anchor):
    x, y, w, h = rect
    side, f = anchor
    if side == "right": return (x + w, y + h * f)
    if side == "left": return (x, y + h * f)
    if side == "bottom": return (x + w * f, y + h)
    return (x + w * f, y)

def elbow(M, A, mode):
    dx, dy = A[0] - M[0], A[1] - M[1]
    if mode == "h":
        run = min(abs(dy), abs(dx) * 0.6)
        E = (M[0] + math.copysign(run, dx), A[1]) if abs(dy) > 1 else None
    else:
        run = min(abs(dx), abs(dy) * 0.6)
        E = (A[0], M[1] + math.copysign(run, dy)) if abs(dx) > 1 else None
    return [M, E, A] if E else [M, A]

def poly_partial(pts, p):
    L = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(L); target = tot * p; out = [pts[0]]
    for (a, b), l in zip(zip(pts, pts[1:]), L):
        if target >= l:
            out.append(b); target -= l
        else:
            f = target / l if l else 0
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); break
    return out, tot

def poly_point(pts, p):
    seg_pts, _ = poly_partial(pts, p)
    return seg_pts[-1]

# ---------------------------------------------------------------- map drawing
def ring_path(ctx, ring):
    ctx.move_to(*ring[0])
    for p in ring[1:]:
        ctx.line_to(*p)
    ctx.close_path()

def ring_len(ring):
    return sum(math.dist(a, b) for a, b in zip(ring, ring[1:]))

STRIP_LEN = [ring_len(r[0]) for r in MAP["strip"]]
BORDER_LEN = [ring_len(r) for r in MAP["borders"]]

def draw_grid(ctx, v, alpha):
    if alpha <= 0: return
    for step, a in ((1, 0.05), (5, 0.08), (25, 0.10), (100, 0.11)):
        px = step * v.z
        if px < 28: continue
        fa = alpha * a * clamp((px - 28) / 60)
        if px > 900: fa *= clamp(1 - (px - 900) / 900)
        if fa <= 0.003: continue
        x0 = v.cx - (W / 2 + 20) / v.z; x1 = v.cx + (W / 2 + 20) / v.z
        y0 = v.cy - (H / 2 + 20) / v.z; y1 = v.cy + (H / 2 + 20) / v.z
        ctx.set_source_rgba(*HL, fa); ctx.set_line_width(1)
        gx = math.floor(x0 / step) * step
        while gx <= x1:
            sx = v.s((gx, 0))[0]; ctx.move_to(round(sx) + .5, 0); ctx.line_to(round(sx) + .5, H); gx += step
        gy = math.floor(y0 / step) * step
        while gy <= y1:
            sy = v.s((0, gy))[1]; ctx.move_to(0, round(sy) + .5); ctx.line_to(W, round(sy) + .5); gy += step
        ctx.stroke()

def draw_map(ctx, v, t):
    reveal = eout(seg(t, 0.15, 2.1))
    # land
    ctx.save(); v.apply(ctx)
    for r in MAP["land"]:
        for ring in r: ring_path(ctx, ring)
    ctx.restore()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.set_source_rgba(*LAND, 0.25 + 0.75 * reveal); ctx.fill()
    # country borders drawn progressively ("map being published")
    for ring, L in zip(MAP["borders"], BORDER_LEN):
        ctx.save(); v.apply(ctx); ctx.move_to(*ring[0])
        for p in ring[1:]: ctx.line_to(*p)
        ctx.restore()
        Lpx = L * v.z
        ctx.set_dash([max(0.01, Lpx * reveal), Lpx + 10])
        ctx.set_source_rgba(*HL, 0.14 + 0.20 * reveal); ctx.set_line_width(1.4); ctx.stroke()
    ctx.set_dash([])
    # Gaza strip
    sp = eout(seg(t, 2.2, 4.0))
    ctx.save(); v.apply(ctx)
    for r in MAP["strip"]:
        for ring in r: ring_path(ctx, ring)
    ctx.restore()
    path = ctx.copy_path()
    ctx.set_source_rgba(*LAND, 0.25 + 0.75 * reveal); ctx.fill_preserve()
    ctx.set_source_rgba(*OLIVE, 0.10 * reveal + 0.18 * sp); ctx.fill()
    # roads inside the strip
    ra = sp * clamp((v.z - 12) / 25)
    if ra > 0:
        ctx.save(); ctx.append_path(path); ctx.clip()
        for kind, pts in MAP["roads"]:
            ctx.save(); v.apply(ctx); ctx.move_to(*pts[0])
            for p in pts[1:]: ctx.line_to(*p)
            ctx.restore()
        ctx.set_source_rgba(*HL, 0.16 * ra); ctx.set_line_width(1.1); ctx.stroke()
        # governorate boundaries
        for ring in MAP["gov"]:
            ctx.save(); v.apply(ctx); ring_path(ctx, ring); ctx.restore()
        ctx.set_dash([5, 5]); ctx.set_source_rgba(*HL, 0.35 * sp); ctx.set_line_width(1.1); ctx.stroke(); ctx.set_dash([])
        ctx.restore()
    # strip outline, drawn on
    for r, L in zip(MAP["strip"], STRIP_LEN):
        ctx.save(); v.apply(ctx); ring_path(ctx, r[0]); ctx.restore()
        Lpx = L * v.z
        ctx.set_dash([max(0.01, Lpx * max(sp, reveal)), Lpx + 10])
        ctx.set_source_rgba(*HL, max(0.95 * sp, 0.55 * reveal)); ctx.set_line_width(2.6); ctx.stroke()
    ctx.set_dash([])

# ---------------------------------------------------------------- markers
POP = {"nasser": 4.2, "o_european": 4.3, "o_aqsa": 4.45, "o_awda_nus": 4.55, "o_quds": 4.7,
       "shifa": 4.8, "o_ahli": 4.9, "o_rantisi": 5.0, "kamal": 5.1, "o_yemen": 5.15, "o_awda": 5.2, "o_indonesian": 5.25}
NAMED = {"nasser": 7.45, "shifa": 9.55, "kamal": 11.40}
OTHERS_BURST = {k: 12.45 + i * 0.07 for i, k in enumerate([k for k in POP if k.startswith("o_")])}

def emph(k, t):
    if k not in NAMED: return 0.0
    return eout(seg(t, NAMED[k], NAMED[k] + 0.35))

def focus(k, t):
    """spotlight strength: the location currently being talked about"""
    spans = {"nasser": [(7.4, 8.95), (15.8, 18.3)], "shifa": [(9.5, 12.2), (14.4, 15.7)], "kamal": [(11.35, 12.7)]}
    f = 0
    for a, b in spans.get(k, []):
        f = max(f, seg(t, a, a + 0.4) * (1 - seg(t, b - 0.3, b)))
    return eio(f)

def draw_cross(ctx, x, y, s, rgba):
    ctx.set_source_rgba(*rgba)
    ctx.rectangle(x - s * 0.22, y - s, s * 0.44, s * 2); ctx.rectangle(x - s, y - s * 0.22, s * 2, s * 0.44); ctx.fill()

def draw_spot(ctx, x, y, f, t):
    if f <= 0: return
    g = cairo.RadialGradient(x, y, 0, x, y, 170)
    g.add_color_stop_rgba(0, *HL, 0.30 * f); g.add_color_stop_rgba(0.4, *OLIVE, 0.12 * f); g.add_color_stop_rgba(1, *OLIVE, 0)
    ctx.set_source(g); ctx.arc(x, y, 170, 0, 2 * math.pi); ctx.fill()
    # rotating target brackets
    r = 34 + 4 * math.sin(t * 3)
    ctx.save(); ctx.translate(x, y); ctx.rotate(t * 0.6)
    ctx.set_source_rgba(*HL, 0.9 * f); ctx.set_line_width(2.2)
    for i in range(4):
        ctx.save(); ctx.rotate(i * math.pi / 2)
        ctx.move_to(r, r - 11); ctx.line_to(r, r); ctx.line_to(r - 11, r); ctx.stroke(); ctx.restore()
    ctx.restore()

def draw_markers(ctx, v, t):
    for k, t0 in POP.items():
        p = seg(t, t0, t0 + 0.45)
        if p <= 0: continue
        x, y = v.s(HOSP[k])
        if x < -100 or x > W + 100 or y < -100 or y > H + 100: continue
        sc = eback(p)
        e = emph(k, t)
        f = focus(k, t)
        draw_spot(ctx, x, y, f, t)
        r = (6.5 + 6.5 * e) * sc
        # pop flash ring
        if p < 1:
            ctx.set_source_rgba(*HL, 0.7 * (1 - p)); ctx.set_line_width(2)
            ctx.arc(x, y, r + 26 * p, 0, 2 * math.pi); ctx.stroke()
        # continuous pulse for named hospitals
        if e > 0:
            for ph in (0, 0.5):
                q = ((t * 0.8 + ph) % 1.0)
                ctx.set_source_rgba(*HL, 0.55 * (1 - q) * e); ctx.set_line_width(1.8)
                ctx.arc(x, y, r + 4 + 46 * q, 0, 2 * math.pi); ctx.stroke()
        # "and others" burst
        if k in OTHERS_BURST:
            q = seg(t, OTHERS_BURST[k], OTHERS_BURST[k] + 0.8)
            if 0 < q < 1:
                ctx.set_source_rgba(*HL, 0.8 * (1 - q)); ctx.set_line_width(2)
                ctx.arc(x, y, r + 40 * eout(q), 0, 2 * math.pi); ctx.stroke()
        ctx.set_source_rgba(*DARK, 0.9); ctx.arc(x, y, r + 4.5, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*HL, 1); ctx.set_line_width(1.6 + e); ctx.arc(x, y, r + 3.5, 0, 2 * math.pi); ctx.stroke()
        ctx.set_source_rgba(*OLIVE, 1); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
        draw_cross(ctx, x, y, r * 0.58, (1, 1, 1, 0.95))

LABEL_POS = {"nasser": ("lr",), "shifa": ("ll",), "kamal": ("ul",)}

def draw_labels(ctx, v, t):
    for k, t0 in NAMED.items():
        p = seg(t, t0 + 0.05, t0 + 0.5)
        if p <= 0: continue
        x, y = v.s(HOSP[k])
        e = eout(p)
        tw, th = text_surface(NAMES[k], "medium", 30)[1:3]
        bw, bh = tw - 16 + 34, 46
        pos = LABEL_POS[k][0]
        if pos == "lr": bx, by = x + 24, y + 14
        elif pos == "ll": bx, by = x - 24 - bw, y + 14
        else: bx, by = x - 24 - bw, y - 14 - bh
        # leader
        lx = bx if pos == "lr" else bx + bw
        ly = by if pos != "ul" else by + bh
        ctx.set_source_rgba(*HL, 0.9 * e); ctx.set_line_width(1.4)
        ctx.move_to(x + (8 if pos == "lr" else -8), y + (8 if pos != "ul" else -8)); ctx.line_to(lx, ly); ctx.stroke()
        # wipe-in box (RTL: grows from the right edge)
        ww = bw * e
        ctx.save(); ctx.rectangle(bx + bw - ww, by - 2, ww + 2, bh + 4); ctx.clip()
        ctx.set_source_rgba(*DARK, 0.92); ctx.rectangle(bx, by, bw, bh); ctx.fill()
        ctx.set_source_rgba(*OLIVE, 1); ctx.rectangle(bx + bw - 6, by, 6, bh); ctx.fill()
        ctx.set_source_rgba(*HL, 0.6); ctx.set_line_width(1); ctx.rectangle(bx + .5, by + .5, bw - 1, bh - 1); ctx.stroke()
        draw_text(ctx, NAMES[k], "medium", 30, bx + bw - 16, by + bh / 2 + 1, "right", alpha=seg(t, t0 + 0.2, t0 + 0.55))
        ctx.restore()

# ---------------------------------------------------------------- occupation forces (tanks / soldiers)
FORCES = {  # start, control, arrive window
    "kamal": ((19.5, -11.0), (16.5, -15.5), 12.95, 14.05),
    "shifa": ((15.0, -3.0), (11.0, -6.5), 13.10, 14.25),
    "nasser": ((3.5, 10.5), (-1.5, 4.5), 13.25, 14.40),
}

def bez(a, c, b, s):
    return ((1 - s) ** 2 * a[0] + 2 * (1 - s) * s * c[0] + s * s * b[0], (1 - s) ** 2 * a[1] + 2 * (1 - s) * s * c[1] + s * s * b[1])

def draw_tank(ctx, s):
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.rectangle(-7 * s, -8 * s, 3.4 * s, 16 * s); ctx.rectangle(3.6 * s, -8 * s, 3.4 * s, 16 * s); ctx.fill()
    ctx.rectangle(-4.6 * s, -6 * s, 9.2 * s, 13 * s); ctx.fill()
    ctx.set_source_rgba(*OLIVE, 1); ctx.arc(0, 0.5 * s, 3.6 * s, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.95); ctx.rectangle(-1.1 * s, -14 * s, 2.2 * s, 13 * s); ctx.fill()
    ctx.arc(0, 0.5 * s, 2.0 * s, 0, 2 * math.pi); ctx.fill()

def draw_soldier(ctx, s):
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.arc(0, -4.8 * s, 2.6 * s, 0, 2 * math.pi); ctx.fill()
    ctx.arc(0, -5.6 * s, 3.4 * s, math.pi, 2 * math.pi); ctx.fill()        # helmet
    ctx.move_to(-4.6 * s, 6 * s); ctx.line_to(-3.6 * s, -1.2 * s); ctx.line_to(3.6 * s, -1.2 * s); ctx.line_to(4.6 * s, 6 * s); ctx.close_path(); ctx.fill()
    ctx.set_line_width(1.4 * s); ctx.move_to(-5 * s, 4 * s); ctx.line_to(5.5 * s, -4 * s); ctx.stroke()  # rifle

def draw_badge(ctx, x, y, r, icon, ang, alpha):
    ctx.set_source_rgba(*DARK, 0.95 * alpha); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*HL, alpha); ctx.set_line_width(2); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.stroke()
    ctx.save(); ctx.translate(x, y); ctx.push_group()
    if icon == "tank":
        ctx.rotate(ang); draw_tank(ctx, r / 19)
    else:
        draw_soldier(ctx, r / 14)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(alpha); ctx.restore()

def draw_forces(ctx, v, t):
    if t < 12.85: return
    for k, (a, c, t0, t1) in FORCES.items():
        A = v.s(a); C = v.s(c); B = v.s(HOSP[k])
        curve = [bez(A, C, B, i / 60) for i in range(61)]
        L = [0]
        for p0, p1 in zip(curve, curve[1:]): L.append(L[-1] + math.dist(p0, p1))
        tot = L[-1]
        def at(dist):
            dist = clamp(dist, 0, tot)
            i = int(np.searchsorted(L, dist)); i = max(1, min(i, len(L) - 1))
            f = (dist - L[i - 1]) / max(1e-6, L[i] - L[i - 1])
            p = (lerp(curve[i - 1][0], curve[i][0], f), lerp(curve[i - 1][1], curve[i][1], f))
            ang = math.atan2(curve[i][1] - curve[i - 1][1], curve[i][0] - curve[i - 1][0]) + math.pi / 2
            return p, ang
        fade_in = seg(t, t0 - 0.15, t0 + 0.2)
        prog = eio(seg(t, t0, t1))
        end_d = tot - 50
        dtank = lerp(0, end_d, prog)
        # dashed trail with moving dashes
        ctx.move_to(*curve[0])
        for p in curve[1:]:
            ctx.line_to(*p)
        ctx.set_dash([8, 9], -t * 40); ctx.set_line_width(1.6)
        ctx.set_source_rgba(*HL, 0.35 * fade_in); ctx.stroke(); ctx.set_dash([])
        # travelled part of the route, solid
        k_end = int(np.searchsorted(L, dtank))
        tr = curve[:max(1, k_end)] + [at(dtank)[0]]
        ctx.move_to(*tr[0])
        for p in tr[1:]:
            ctx.line_to(*p)
        ctx.set_source_rgba(*HL, 0.9 * fade_in); ctx.set_line_width(2.6); ctx.stroke()
        # origin ring
        ctx.set_source_rgba(*HL, 0.6 * fade_in); ctx.set_line_width(1.5); ctx.arc(*A, 9, 0, 2 * math.pi); ctx.stroke()
        # chevrons ahead of tank
        for i in range(3):
            d = dtank + 30 + ((t * 60 + i * 22) % 66)
            if d > end_d + 20: continue
            (px, py), ang = at(d)
            ctx.save(); ctx.translate(px, py); ctx.rotate(ang)
            ctx.set_source_rgba(*HL, 0.7 * fade_in); ctx.set_line_width(2.2)
            ctx.move_to(-6, 3); ctx.line_to(0, -3); ctx.line_to(6, 3); ctx.stroke(); ctx.restore()
        (sx, sy), ang = at(max(0, dtank - 50))
        draw_badge(ctx, sx, sy, 19, "soldier", 0, fade_in)
        (tx, ty), ang = at(dtank)
        draw_badge(ctx, tx, ty, 26, "tank", ang, fade_in)
        # arrival: digital waves
        arr = seg(t, t1 - 0.1, t1 + 0.3)
        if arr > 0:
            for i in range(3):
                q = ((t - t1) * 0.9 + i / 3) % 1.0
                ctx.set_source_rgba(*HL, 0.65 * (1 - q) * arr); ctx.set_line_width(2)
                ctx.arc(*B, 18 + 80 * q, 0, 2 * math.pi); ctx.stroke()
            # radar sweep arc
            ctx.save(); ctx.translate(*B); ctx.rotate(t * 3.2)
            g = cairo.LinearGradient(0, 0, 70, 0)
            ctx.move_to(0, 0); ctx.arc(0, 0, 70, -0.6, 0); ctx.close_path()
            ctx.set_source_rgba(*HL, 0.16 * arr); ctx.fill()
            ctx.restore()

# ---------------------------------------------------------------- windows (connector lines + media frames)
def window_state(wd, t):
    o, c = wd["o"], wd["c"]
    line = seg(t, o - 0.3, o) * (1 - seg(t, c + 0.12, c + 0.38))
    frame = eout(seg(t, o, o + 0.38)) * (1 - ein(seg(t, c, c + 0.26)))
    return line, frame

def draw_connectors(ctx, v, t):
    for wd in WINDOWS:
        line, frame = window_state(wd, t)
        if line <= 0: continue
        M = v.s(HOSP[wd["m"]])
        A = anchor_pt(rect_at(wd, t), wd["anchor"])
        pts = elbow(M, A, wd["mode"])
        part, tot = poly_partial(pts, eio(line))
        ctx.move_to(*part[0])
        for p in part[1:]: ctx.line_to(*p)
        ctx.set_source_rgba(*HL, 0.95); ctx.set_line_width(2.4); ctx.stroke()
        ctx.set_source_rgba(*HL, 1); ctx.arc(*M, 5, 0, 2 * math.pi); ctx.fill()
        ctx.arc(*part[-1], 4.5, 0, 2 * math.pi); ctx.fill()
        if line >= 1:  # light pulse travelling to the frame
            q = (t * 1.4) % 1.0
            px, py = poly_point(pts, q)
            g = cairo.RadialGradient(px, py, 0, px, py, 16)
            g.add_color_stop_rgba(0, 1, 1, 1, 0.9); g.add_color_stop_rgba(1, *HL, 0)
            ctx.set_source(g); ctx.arc(px, py, 16, 0, 2 * math.pi); ctx.fill()

def draw_frames(ctx, v, t):
    for idx, wd in enumerate(WINDOWS):
        line, frame = window_state(wd, t)
        if frame <= 0: continue
        x, y, w, h = rect_at(wd, t)
        # floating motion
        fy = 4 * math.sin(t * 1.3 + idx); fx = 3 * math.sin(t * 0.9 + idx * 2)
        ax, ay = anchor_pt((x, y, w, h), wd["anchor"])
        # uniform scale about the anchor -> aspect ratio always preserved
        s = 0.04 + 0.96 * frame
        x = ax + (x - ax) * s + fx * frame; y = ay + (y - ay) * s + fy * frame; w *= s; h *= s
        ca = seg(frame, 0.45, 1.0)
        # shadow
        for i in range(8):
            ctx.set_source_rgba(0, 0, 0, 0.05 * frame)
            ctx.rectangle(x - 8 - i * 3, y - 8 - i * 3 + 6, w + 16 + i * 6, h + 16 + i * 6); ctx.fill()
        ctx.set_source_rgba(*DARK, 0.95 * frame); ctx.rectangle(x - 7, y - 7, w + 14, h + 14); ctx.fill()
        if ca > 0:
            tl = t - wd["o"]
            surf, sw, sh = media_surface(wd["src"], tl)
            kb = 1.0 + (0.06 * seg(t, wd["o"], wd["c"] + 0.3) if wd.get("kb") else 0.0)
            sc = max(w / sw, h / sh) * kb
            ctx.save(); ctx.rectangle(x, y, w, h); ctx.clip()
            ctx.translate(x + w / 2, y + h / 2); ctx.scale(sc, sc); ctx.translate(-sw / 2, -sh / 2)
            ctx.set_source_surface(surf, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD)
            ctx.paint_with_alpha(ca)
            ctx.restore()
            # digital reveal sweep line
            if ca < 1:
                yy = y + h * ca
                ctx.set_source_rgba(*HL, 0.8 * (1 - ca)); ctx.rectangle(x, yy - 1.5, w, 3); ctx.fill()
        ctx.set_source_rgba(*OLIVE, frame); ctx.set_line_width(2); ctx.rectangle(x - 1, y - 1, w + 2, h + 2); ctx.stroke()
        # corner brackets
        L = 26; o = 13
        ctx.set_source_rgba(*HL, frame); ctx.set_line_width(3)
        for cx_, cy_, sx_, sy_ in ((x - o, y - o, 1, 1), (x + w + o, y - o, -1, 1), (x - o, y + h + o, 1, -1), (x + w + o, y + h + o, -1, -1)):
            ctx.move_to(cx_, cy_ + sy_ * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx_ * L, cy_); ctx.stroke()
        # small live-dot in the corner
        if ca > 0 and wd["src"][0] == "clip":
            a = 0.5 + 0.5 * math.sin(t * 6)
            ctx.set_source_rgba(*HL, ca * (0.4 + 0.6 * a)); ctx.arc(x + w - 18, y + 18, 5, 0, 2 * math.pi); ctx.fill()

# ---------------------------------------------------------------- titles
TITLE = "أبرز المستشفيات والمرافق الطبية في قطاع غزة"

def draw_title(ctx, t):
    a0, a1 = 3.45, 6.95
    pin = seg(t, a0, a0 + 0.5); pout = seg(t, a1, a1 + 0.4)
    if pin <= 0 or pout >= 1: return
    tw, th = text_surface(TITLE, "bold", 46)[1:3]
    bw, bh = tw - 16 + 70, 84
    right = W - 90; bx, by = right - bw, H - 170
    e = eout(pin) * (1 - ein(pout))
    ww = bw * e
    ctx.save(); ctx.rectangle(right - ww, by - 10, ww + 2, bh + 20); ctx.clip()
    ctx.set_source_rgba(*DARK, 0.94); ctx.rectangle(bx, by, bw, bh); ctx.fill()
    ctx.set_source_rgba(*OLIVE, 1); ctx.rectangle(right - 12, by, 12, bh); ctx.fill()
    ctx.set_source_rgba(*HL, 1); ctx.rectangle(bx, by - 4, bw * eout(seg(t, a0 + 0.2, a0 + 0.9)), 4); ctx.fill()
    ta = seg(t, a0 + 0.25, a0 + 0.6) * (1 - pout)
    draw_text(ctx, TITLE, "bold", 46, right - 34 + 24 * (1 - eout(seg(t, a0 + 0.25, a0 + 0.7))), by + bh / 2 + 2, "right", alpha=ta)
    ctx.restore()

def draw_strip_label(ctx, v, t):
    a = seg(t, 5.85, 6.25) * (1 - seg(t, 6.95, 7.3))
    if a <= 0: return
    x, y = v.s((-3.0, -6.0))
    draw_text(ctx, "قطاع غزة", "black", 54, x, y, "right", alpha=a, color=(0xC7, 0x97, 0x3B))
    ctx.set_source_rgba(*HL, a); ctx.set_line_width(2)
    ctx.move_to(x, y + 40); ctx.line_to(x - 230 * eout(seg(t, 5.9, 6.4)), y + 40); ctx.stroke()

def draw_hud(ctx, t):
    a = 0.45 * seg(t, 0.3, 1.2) * (1 - seg(t, 19.4, 19.9))
    ctx.set_source_rgba(*HL, a); ctx.set_line_width(2)
    m, L = 36, 46
    for cx_, cy_, sx_, sy_ in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        ctx.move_to(cx_, cy_ + sy_ * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx_ * L, cy_); ctx.stroke()

def draw_scan(ctx, t):
    # radial "publishing the map" scan ring at the start
    p = seg(t, 0.15, 2.1)
    if 0 < p < 1:
        r = 60 + 1300 * eout(p)
        g = cairo.RadialGradient(W / 2, H / 2, r - 60, W / 2, H / 2, r)
        g.add_color_stop_rgba(0, *HL, 0); g.add_color_stop_rgba(0.85, *HL, 0.10 * (1 - p)); g.add_color_stop_rgba(1, *HL, 0)
        ctx.set_source(g); ctx.paint()
    # light sweeps
    for t0, dur in ((2.3, 1.4), (12.9, 1.3)):
        q = seg(t, t0, t0 + dur)
        if 0 < q < 1:
            cx = -400 + (W + 800) * eio(q)
            g = cairo.LinearGradient(cx - 300, 0, cx + 300, 200)
            g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(0.5, *HL, 0.07); g.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(g); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)

# ---------------------------------------------------------------- post
yy, xx = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIG = np.clip(1.0 - 0.42 * np.clip(_d - 0.45, 0, None) ** 1.6, 0.45, 1.0).astype(np.float32)[..., None]
del yy, xx, _d
_rng = np.random.default_rng(7)
GRAIN = [_rng.normal(0, 2.2, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]

def surf_array(surf):
    return np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())

def bloom(surf, strength=0.85):
    a = surf_array(surf)
    small = Image.fromarray(a[..., :3].copy()).resize((W // 4, H // 4), Image.BILINEAR)
    s = np.asarray(small).astype(np.float32) / 255
    lum = s.max(axis=2, keepdims=True)
    s = s * np.clip((lum - 0.32) / 0.5, 0, 1)
    im = Image.fromarray((s * 255).astype(np.uint8))
    b1 = np.asarray(im.filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
    b2 = np.asarray(im.filter(ImageFilter.GaussianBlur(10))).astype(np.float32)
    b = Image.fromarray(np.clip(b1 * 0.9 + b2 * 1.3, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    out = a[..., :3].astype(np.float32) + np.asarray(b).astype(np.float32) * strength
    a[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
    surf.mark_dirty()

def render(i):
    t = i / FPS
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    v = View(t)
    # background
    g = cairo.RadialGradient(W / 2, H / 2, 100, W / 2, H / 2, 1200)
    g.add_color_stop_rgb(0, *[c * 1.15 for c in SEA]); g.add_color_stop_rgb(1, *[c * 0.7 for c in SEA])
    ctx.set_source(g); ctx.paint()
    draw_grid(ctx, v, seg(t, 0.0, 1.0))
    draw_map(ctx, v, t)
    draw_scan(ctx, t)
    draw_forces(ctx, v, t)
    draw_markers(ctx, v, t)
    draw_connectors(ctx, v, t)
    surf.flush()
    bloom(surf)
    draw_frames(ctx, v, t)
    draw_labels(ctx, v, t)
    draw_strip_label(ctx, v, t)
    draw_title(ctx, t)
    draw_hud(ctx, t)
    # emphasis flash as the claim starts
    fl = seg(t, 12.88, 13.0) * (1 - seg(t, 13.0, 13.45))
    if fl > 0:
        ctx.set_source_rgba(*OLIVE, 0.10 * fl); ctx.paint()
    surf.flush()
    a = surf_array(surf)[..., :3].astype(np.float32)
    a *= VIG
    gr = GRAIN[i % len(GRAIN)]
    a += np.repeat(np.repeat(gr, 2, axis=0), 2, axis=1)
    fade = seg(t, 0.0, 0.45) * (1 - seg(t, 19.35, 19.95))
    a *= fade
    out = np.clip(a, 0, 255).astype(np.uint8)
    return out[..., ::-1].tobytes()  # BGR -> RGB

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        for ts in sys.argv[2:]:
            i = int(float(ts) * FPS)
            Image.frombytes("RGB", (W, H), render(i)).save(f"{WORK}/stills/s_{float(ts):05.2f}.jpg", quality=90)
            print("still", ts, flush=True)
    else:
        import subprocess
        from multiprocessing import Pool
        out = sys.argv[2]
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-preset", "slow", "-b:v", "17M", "-maxrate", "22M", "-bufsize", "34M", "-pix_fmt", "yuv420p",
                               "-profile:v", "high", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render, range(N), chunksize=4)):
                ff.stdin.write(fr)
                if k % 60 == 0: print("frame", k, flush=True)
        ff.stdin.close(); ff.wait()
        print("done")
