import math, sys
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 21.0
N = int(DUR * FPS)
WORK = "/tmp/w2"

def hexc(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

OLIVE = hexc("896829")
DARK = hexc("1D1D1D")
HL = hexc("C7973B")
HL8 = (0xC7, 0x97, 0x3B)
WHITE = (1, 1, 1)

# ---------------------------------------------------------------- easing
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v
def seg(t, a, b):
    return clamp((t - a) / (b - a))
def eio(p):
    return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
def eout(p):
    return 1 - (1 - p) ** 3
def ein(p):
    return p ** 3
def eback(p, s=1.7):
    p -= 1
    return 1 + p * p * ((s + 1) * p + s)
def lerp(a, b, p):
    return a + (b - a) * p
def rnd(i, k=0):
    """deterministic hash noise in [0,1)"""
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)

# ---------------------------------------------------------------- text
FONTS = {"black": "/tmp/work/fonts/black.otf", "bold": "/tmp/work/fonts/bold.ttf",
         "medium": "/tmp/work/fonts/medium.otf", "light": "/tmp/work/fonts/light.otf"}
_tc = {}

def pil_to_surface(im):
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    al = a[..., 3:4] / 255.0
    rgb = a[..., :3] * al
    bgra = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], a[..., 3]]).astype(np.uint8)
    h, w = bgra.shape[:2]
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
    return cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)

def text_surface(s, font, size, color=(255, 255, 255), ltr=False):
    key = (s, font, size, color, ltr)
    if key in _tc: return _tc[key]
    if len(_tc) > 400: _tc.clear()
    f = ImageFont.truetype(FONTS[font], size, layout_engine=ImageFont.Layout.RAQM)
    kw = dict(direction="ltr") if ltr else dict(direction="rtl", language="ar")
    bbox = f.getbbox(s, **kw)
    pad = 10
    w = bbox[2] - bbox[0] + pad * 2; h = bbox[3] - bbox[1] + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bbox[0], pad - bbox[1]), s, font=f, fill=color + (255,), **kw)
    r = (pil_to_surface(im), w, h, pad)
    _tc[key] = r
    return r

def text_w(s, font, size, ltr=False):
    _, w, h, pad = text_surface(s, font, size, ltr=ltr)
    return w - 2 * pad

def draw_text(ctx, s, font, size, x, y, align="center", alpha=1.0, color=(255, 255, 255), scale=1.0,
              ltr=False, wipe=1.0):
    """(x, y) = anchor at vertical centre. wipe reveals right-to-left (RTL reading order)."""
    if alpha <= 0 or wipe <= 0: return
    surf, w, h, pad = text_surface(s, font, size, color, ltr)
    if align == "right": x0 = -w + pad
    elif align == "left": x0 = -pad
    else: x0 = -w / 2
    ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale)
    if wipe < 1:
        ctx.rectangle(x0 + w * (1 - wipe), -h / 2 - 5, w * wipe + 5, h + 10); ctx.clip()
    ctx.set_source_surface(surf, x0, -h / 2); ctx.paint_with_alpha(alpha)
    if 0 < wipe < 1:
        ctx.set_source_rgba(*HL, alpha); ctx.rectangle(x0 + w * (1 - wipe) - 2, -h / 2 + 6, 4, h - 12); ctx.fill()
    ctx.restore()

# ---------------------------------------------------------------- icons (unit box -50..50)
def icon_hospital(ctx, fg, cut=DARK):
    ctx.set_source_rgba(*fg)
    ctx.rectangle(-42, -14, 84, 56); ctx.fill()
    ctx.rectangle(-22, -44, 44, 32); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.rectangle(-4, -39, 8, 22); ctx.rectangle(-11, -32, 22, 8); ctx.fill()
    for x in (-34, -20, 12, 26):
        for y in (-4, 14):
            ctx.rectangle(x, y, 8, 9)
    ctx.rectangle(-7, 20, 14, 22); ctx.fill()

def icon_ambulance(ctx, fg, cut=DARK):
    ctx.set_source_rgba(*fg)
    ctx.rectangle(-48, -26, 64, 46); ctx.fill()
    ctx.move_to(18, -12); ctx.line_to(34, -12); ctx.line_to(48, 4); ctx.line_to(48, 20); ctx.line_to(18, 20); ctx.close_path(); ctx.fill()
    ctx.rectangle(-28, -34, 18, 7); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.rectangle(-20, -18, 8, 28); ctx.rectangle(-30, -8, 28, 8); ctx.fill()
    ctx.move_to(24, -7); ctx.line_to(33, -7); ctx.line_to(42, 3); ctx.line_to(24, 3); ctx.close_path(); ctx.fill()
    for wx in (-30, 32):
        ctx.arc(wx, 22, 11, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*fg)
    for wx in (-30, 32):
        ctx.arc(wx, 22, 5, 0, 2 * math.pi); ctx.fill()

def icon_medic(ctx, fg, cut=DARK):
    ctx.set_source_rgba(*fg)
    ctx.arc(0, -20, 15, 0, 2 * math.pi); ctx.fill()
    ctx.move_to(-16, -30); ctx.line_to(16, -30); ctx.line_to(14, -42); ctx.line_to(-14, -42); ctx.close_path(); ctx.fill()
    ctx.move_to(-38, 44); ctx.curve_to(-38, 10, -26, 2, 0, 2); ctx.curve_to(26, 2, 38, 10, 38, 44); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.rectangle(-2.5, -41, 5, 10); ctx.rectangle(-6, -37.5, 12, 4); ctx.fill()
    ctx.rectangle(8, 16, 6, 18); ctx.rectangle(2, 22, 18, 6); ctx.fill()
    ctx.set_line_width(3.2)
    ctx.move_to(-14, 4); ctx.curve_to(-18, 24, -10, 34, -6, 34); ctx.stroke()
    ctx.arc(-6, 36, 4, 0, 2 * math.pi); ctx.fill()

def icon_supply(ctx, fg, cut=DARK):
    ctx.set_source_rgba(*fg)
    for x0 in (-48, 12):
        ctx.rectangle(x0, -6, 36, 36); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    for x0 in (-48, 12):
        ctx.rectangle(x0 + 15, 3, 6, 18); ctx.rectangle(x0 + 9, 9, 18, 6); ctx.fill()
    ctx.set_source_rgba(*fg); ctx.set_line_width(4)
    ctx.save(); ctx.translate(-5, 12); ctx.scale(1, 0.6); ctx.arc(0, 0, 8, 0, 2 * math.pi); ctx.restore(); ctx.stroke()
    ctx.save(); ctx.translate(5, 12); ctx.scale(1, 0.6); ctx.arc(0, 0, 8, 0, 2 * math.pi); ctx.restore(); ctx.stroke()
    ctx.set_line_width(4)
    ctx.move_to(-40, -26); ctx.line_to(34, -26); ctx.stroke()
    ctx.move_to(44, -26); ctx.line_to(30, -35); ctx.line_to(30, -17); ctx.close_path(); ctx.fill()

def icon_person(ctx, fg, cut=DARK):
    ctx.set_source_rgba(*fg)
    ctx.arc(0, -24, 13, 0, 2 * math.pi); ctx.fill()
    ctx.move_to(-30, 42); ctx.curve_to(-30, 4, -20, -6, 0, -6); ctx.curve_to(20, -6, 30, 4, 30, 42); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.rectangle(-3.5, 6, 7, 20); ctx.rectangle(-10, 12.5, 20, 7); ctx.fill()

def draw_icon(ctx, fn, x, y, size, fg, cut=DARK, rot=0.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(size / 100, size / 100)
    fn(ctx, fg, cut); ctx.restore()

def draw_jet(ctx, x, y, s, alpha=1.0):
    """side profile, nose pointing left"""
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    ctx.push_group()
    ctx.set_source_rgba(0.80, 0.80, 0.80, 1)
    ctx.move_to(-70, 0); ctx.curve_to(-60, -8, -40, -9, -20, -8); ctx.line_to(48, -6); ctx.line_to(62, -26); ctx.line_to(72, -26)
    ctx.line_to(68, -4); ctx.line_to(72, 2); ctx.line_to(44, 6); ctx.line_to(-30, 6); ctx.curve_to(-50, 6, -62, 4, -70, 0); ctx.fill()
    ctx.set_source_rgba(0.62, 0.62, 0.62, 1)
    ctx.move_to(-6, 0); ctx.line_to(30, 0); ctx.line_to(44, 18); ctx.line_to(30, 18); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*DARK, 1)
    ctx.move_to(-46, -6); ctx.curve_to(-38, -14, -26, -14, -20, -8); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*HL, 1); ctx.rectangle(58, -24, 10, 5); ctx.fill()
    # afterburner
    g = cairo.RadialGradient(76, 0, 0, 76, 0, 22)
    g.add_color_stop_rgba(0, 1, 0.9, 0.6, 0.9); g.add_color_stop_rgba(1, 1, 0.5, 0.1, 0)
    ctx.set_source(g); ctx.arc(76, 0, 22, 0, 2 * math.pi); ctx.fill()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(alpha)
    ctx.restore()

def reticle(ctx, x, y, r, rot, alpha, lw=3):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot)
    ctx.set_source_rgba(*HL, alpha); ctx.set_line_width(lw)
    L = r * 0.45
    for i in range(4):
        ctx.save(); ctx.rotate(i * math.pi / 2)
        ctx.move_to(r, r - L); ctx.line_to(r, r); ctx.line_to(r - L, r); ctx.stroke(); ctx.restore()
    ctx.set_line_width(lw * 0.7)
    for i in range(4):
        ctx.save(); ctx.rotate(i * math.pi / 2); ctx.move_to(r * 0.35, 0); ctx.line_to(r * 0.7, 0); ctx.stroke(); ctx.restore()
    ctx.arc(0, 0, 4, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

# ---------------------------------------------------------------- effects
def fireball(ctx, x, y, age, size=1.0):
    if age < 0: return
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    if age < 0.25:
        a = 1 - age / 0.25
        g = cairo.RadialGradient(x, y, 0, x, y, 320 * size)
        g.add_color_stop_rgba(0, 1, 0.95, 0.8, 0.55 * a); g.add_color_stop_rgba(0.3, 1, 0.6, 0.2, 0.25 * a); g.add_color_stop_rgba(1, 1, 0.5, 0.1, 0)
        ctx.set_source(g); ctx.paint()
    if age < 1.1:
        p = age / 1.1
        r = (30 + 100 * eout(min(1, age / 0.35))) * size
        a = (1 - p) ** 1.4
        g = cairo.RadialGradient(x, y - 20 * p * size, 0, x, y - 20 * p * size, r)
        g.add_color_stop_rgba(0, 1, 0.95, 0.75, a); g.add_color_stop_rgba(0.45, 1, 0.55, 0.12, 0.8 * a); g.add_color_stop_rgba(1, 0.7, 0.2, 0.05, 0)
        ctx.set_source(g); ctx.arc(x, y - 20 * p * size, r, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    if age < 0.7:
        p = age / 0.7
        ctx.set_source_rgba(*HL, 0.7 * (1 - p)); ctx.set_line_width(3 * (1 - p) + 1)
        ctx.arc(x, y, (40 + 260 * eout(p)) * size, 0, 2 * math.pi); ctx.stroke()
    if age < 1.2:
        for k in range(12):
            ang = -math.pi * (0.1 + 0.8 * rnd(k, x))
            v = (250 + 300 * rnd(k, y)) * size
            px = x + math.cos(ang) * v * age; py = y + math.sin(ang) * v * age + 500 * age * age
            a = 1 - age / 1.2
            ctx.set_source_rgba(1, 0.75, 0.35, a); ctx.arc(px, py, 3 * size, 0, 2 * math.pi); ctx.fill()

def smoke(ctx, x, y, age, size=1.0, life=4.5, n=7, alpha=0.5):
    if age < 0.05: return
    for k in range(n):
        st = k * 0.12
        a_ = age - st
        if a_ <= 0: continue
        p = a_ / life
        if p >= 1: continue
        px = x + (rnd(k, x) - 0.5) * 70 * size + 40 * p * size * (rnd(k, 3) - 0.3)
        py = y - (40 + 380 * eout(min(1, p * 1.3))) * size
        r = (35 + 120 * p) * size
        a = alpha * math.sin(math.pi * min(1, p * 1.1)) ** 0.8
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, 0.16, 0.16, 0.16, a); g.add_color_stop_rgba(1, 0.12, 0.12, 0.12, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()

def flames(ctx, x, y, w, strength, t, seed, n=34, height=170):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for i in range(n):
        L = 0.55 + 0.5 * rnd(i, seed)
        age = (t + rnd(i, seed + 1) * L) % L
        u = age / L
        bx = x + (rnd(i, seed + 2) - 0.5) * w
        px = bx + math.sin(t * 5 + i) * 7 * u + (rnd(i, seed + 3) - 0.5) * 18 * u
        py = y - u * height * strength * (0.7 + 0.5 * rnd(i, seed + 4))
        r = (14 + 26 * strength) * (1 - u) ** 0.7 + 3
        if u < 0.25: c0 = (1, 0.92, 0.65)
        elif u < 0.6: c0 = (1, 0.58, 0.16)
        else: c0 = (0.75, 0.25, 0.06)
        a = (1 - u) * 0.55
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, *c0, a); g.add_color_stop_rgba(1, c0[0], c0[1] * 0.5, 0, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def smoke_column(ctx, x, y, t, seed, n=16, size=1.0, alpha=0.42):
    for i in range(n):
        L = 3.5 + 1.5 * rnd(i, seed)
        age = (t + rnd(i, seed + 1) * L) % L
        u = age / L
        px = x + (rnd(i, seed + 2) - 0.5) * 60 * size + u * 160 * size + math.sin(t * 0.7 + i) * 20 * u
        py = y - u * 620 * size
        r = (40 + 150 * u) * size
        a = alpha * math.sin(math.pi * u)
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, 0.13, 0.12, 0.11, a); g.add_color_stop_rgba(1, 0.11, 0.11, 0.11, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()

def embers(ctx, x, y, w, t, seed, n=26, height=520):
    for i in range(n):
        L = 1.6 + 1.4 * rnd(i, seed)
        age = (t + rnd(i, seed + 1) * L) % L
        u = age / L
        px = x + (rnd(i, seed + 2) - 0.5) * w + math.sin(t * 3 + i * 2) * 25 * u
        py = y - u * height
        a = (1 - u) * (0.6 + 0.4 * math.sin(t * 20 + i))
        ctx.set_source_rgba(1, 0.75 + 0.2 * rnd(i, 9), 0.4, max(0, a)); ctx.arc(px, py, 2 + 1.5 * rnd(i, 5), 0, 2 * math.pi); ctx.fill()

def corner_frame(ctx, x, y, w, h, alpha, L=28, lw=3):
    ctx.set_source_rgba(*HL, alpha); ctx.set_line_width(lw)
    for cx_, cy_, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        ctx.move_to(cx_, cy_ + sy * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx * L, cy_); ctx.stroke()

def panel(ctx, x, y, w, h, alpha, fill=0.88):
    ctx.set_source_rgba(0.09, 0.09, 0.09, fill * alpha); ctx.rectangle(x, y, w, h); ctx.fill()
    ctx.set_source_rgba(*OLIVE, 0.9 * alpha); ctx.set_line_width(1.5); ctx.rectangle(x + .75, y + .75, w - 1.5, h - 1.5); ctx.stroke()
    corner_frame(ctx, x - 8, y - 8, w + 16, h + 16, alpha)

# ================================================================ SCENE 1: 900+ strikes, jets
JETS = [(-0.3, 1340, -720, 290, 1.45), (0.45, 1340, -640, 430, 1.05), (1.35, 1340, -700, 240, 1.3)]
def jet_pos(j, t):
    t0, x0, vx, y0, s = JETS[j]
    return x0 + vx * (t - t0), y0 + 6 * math.sin((t - t0) * 2.3 + j)

rng = np.random.default_rng(11)
GROUND = 1600
BLD_FAR, BLD_NEAR = [], []
x = -60
while x < W + 60:
    w = int(rng.integers(70, 150)); h = int(rng.integers(230, 470)); BLD_FAR.append((x, w, h)); x += w + int(rng.integers(-10, 8))
x = -40
while x < W + 60:
    w = int(rng.integers(60, 140)); h = int(rng.integers(110, 330)); BLD_NEAR.append((x, w, h)); x += w + int(rng.integers(4, 22))

def roof_y(x):
    for bx, bw, bh in BLD_NEAR:
        if bx <= x <= bx + bw: return GROUND - bh
    return GROUND - 40

BOMBS = []
for j, trs in ((0, (0.12, 0.52, 0.92)), (1, (0.95, 1.35, 1.75)), (2, (1.75, 2.15, 2.55))):
    for tr in trs:
        xr, yr = jet_pos(j, tr)
        ti = tr + 0.75
        xt = xr + JETS[j][2] * 0.26
        BOMBS.append(dict(j=j, tr=tr, ti=ti, xr=xr, yr=yr + 14, xt=xt, yt=roof_y(xt) + 6))
IMPACTS = [b["ti"] for b in BOMBS]

def shake1(t):
    sx = sy = 0
    for b in BOMBS:
        a = t - b["ti"]
        if 0 <= a < 0.6:
            e = math.exp(-a * 7) * 9
            sx += e * math.sin(a * 70 + b["tr"] * 9); sy += e * math.cos(a * 61 + b["tr"] * 5)
    return sx, sy

def draw_skyline(ctx, t, glow):
    # far layer
    for i, (bx, bw, bh) in enumerate(BLD_FAR):
        ctx.set_source_rgba(0.15, 0.15, 0.15, 1); ctx.rectangle(bx, GROUND - bh - 60, bw, bh + 60); ctx.fill()
    ctx.set_source_rgba(0.09, 0.09, 0.09, 1)
    for i, (bx, bw, bh) in enumerate(BLD_NEAR):
        ctx.rectangle(bx, GROUND - bh, bw, bh + 400)
    ctx.fill()
    # windows
    for i, (bx, bw, bh) in enumerate(BLD_NEAR):
        for yy in range(int(GROUND - bh + 18), GROUND - 10, 30):
            for xx in range(int(bx + 12), int(bx + bw - 14), 24):
                r = rnd(xx, yy)
                if r < 0.55: continue
                a = 0.10 + 0.25 * (r > 0.92)
                ctx.set_source_rgba(*HL, a); ctx.rectangle(xx, yy, 10, 14); ctx.fill()
        # rim light from explosions
        ctx.set_source_rgba(1, 0.6, 0.2, 0.35 * glow); ctx.rectangle(bx, GROUND - bh, bw, 3); ctx.fill()
    ctx.set_source_rgba(*OLIVE, 0.7); ctx.rectangle(0, GROUND, W, 3); ctx.fill()
    ctx.set_source_rgba(0.07, 0.07, 0.07, 1); ctx.rectangle(0, GROUND + 3, W, H - GROUND); ctx.fill()

def draw_s1_world(ctx, t):
    glow = 0
    for b in BOMBS:
        a = t - b["ti"]
        if a >= 0: glow = max(glow, math.exp(-a * 2.5))
    # horizon glow
    g = cairo.LinearGradient(0, GROUND - 700, 0, GROUND)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, *OLIVE, 0.22 + 0.3 * glow)
    ctx.set_source(g); ctx.rectangle(0, GROUND - 700, W, 700); ctx.fill()
    # smoke behind
    for b in BOMBS:
        smoke(ctx, b["xt"], b["yt"], t - b["ti"], 1.0, alpha=0.45)
    draw_skyline(ctx, t, glow)
    # targets
    for b in BOMBS:
        p = seg(t, b["ti"] - 0.55, b["ti"])
        if 0 < p < 1:
            reticle(ctx, b["xt"], b["yt"] - 8, 70 - 35 * eout(p), p * 1.5, 0.9 * min(1, p * 4))
    # bombs
    for b in BOMBS:
        if b["tr"] <= t < b["ti"]:
            u = (t - b["tr"]) / (b["ti"] - b["tr"])
            bx = lerp(b["xr"], b["xt"], u); by = b["yr"] + (b["yt"] - b["yr"]) * u * u
            vx = b["xt"] - b["xr"]; vy = 2 * (b["yt"] - b["yr"]) * u + 1e-3
            ang = math.atan2(vy, vx)
            ctx.save(); ctx.translate(bx, by); ctx.rotate(ang)
            ctx.set_source_rgba(0.85, 0.85, 0.85, 1); ctx.rectangle(-14, -4, 24, 8); ctx.fill()
            ctx.move_to(10, -4); ctx.line_to(17, 0); ctx.line_to(10, 4); ctx.fill()
            ctx.set_source_rgba(*HL, 1); ctx.rectangle(-18, -6, 5, 12); ctx.fill()
            ctx.restore()
            ctx.set_source_rgba(*HL, 0.25); ctx.set_line_width(1.5)
            ctx.move_to(b["xr"], b["yr"]);
            for k in range(1, 11):
                uu = u * k / 10; ctx.line_to(lerp(b["xr"], b["xt"], uu), b["yr"] + (b["yt"] - b["yr"]) * uu * uu)
            ctx.stroke()
    # explosions
    for b in BOMBS:
        fireball(ctx, b["xt"], b["yt"], t - b["ti"], 1.0)
    # jets with contrails
    for j in range(3):
        x_, y_ = jet_pos(j, t)
        if -250 < x_ < W + 250:
            t0, x0, vx, y0, s = JETS[j]
            g = cairo.LinearGradient(x_, y_, x_ + 600 * s, y_)
            g.add_color_stop_rgba(0, 1, 1, 1, 0.22); g.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.set_source(g); ctx.set_line_width(3 * s); ctx.move_to(x_ + 70 * s, y_); ctx.line_to(x_ + 600 * s, y_); ctx.stroke()
            draw_jet(ctx, x_, y_, s)

def draw_s1(ctx, t):
    sx, sy = shake1(t)
    z = 1.0 + 0.05 * eio(seg(t, 0, 3.6))
    sink = 650 * ein(seg(t, 3.45, 4.0))
    ctx.save()
    ctx.translate(W / 2 + sx, H / 2 + sy + sink); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
    draw_s1_world(ctx, t)
    ctx.restore()

# hub / big counter shared between scene 1 and 2
def count900(t):
    return int(round(900 * eout(seg(t, 0.72, 1.35))))

def hub_layout(t):
    p = eio(seg(t, 3.45, 4.0))
    return dict(nx=540, ny=lerp(700, 925, p), ns=lerp(1.0, 0.55, p),
                lx=540, ly=lerp(880, 1030, p), ls=lerp(1.0, 0.55, p), p=p)

def bump(t, times, dur=0.25, amt=0.06):
    b = 0
    for ti in times:
        a = t - ti
        if 0 <= a < dur: b = max(b, amt * math.sin(math.pi * a / dur))
    return b

def draw_hub(ctx, t):
    L = hub_layout(t)
    n = count900(t)
    if t >= 0.62:
        sc = L["ns"] * (1 + bump(t, IMPACTS) + 0.25 * (1 - eout(seg(t, 0.62, 0.9))))
        a = seg(t, 0.62, 0.8)
        # backing glow
        g = cairo.RadialGradient(L["nx"], L["ny"], 0, L["nx"], L["ny"], 380 * L["ns"])
        g.add_color_stop_rgba(0, 0, 0, 0, 0.55 * a); g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g); ctx.arc(L["nx"], L["ny"], 380 * L["ns"], 0, 2 * math.pi); ctx.fill()
        draw_text(ctx, f"+{n}", "black", 250, L["nx"], L["ny"], "center", alpha=a, color=HL8, scale=sc, ltr=True)
    if t >= 1.12:
        draw_text(ctx, "استهداف", "bold", 104, L["lx"], L["ly"], "center", alpha=seg(t, 1.12, 1.35), scale=L["ls"],
                  wipe=eout(seg(t, 1.12, 1.5)))
    # ring (scene 2)
    rp = seg(t, 3.7, 4.2)
    if rp > 0:
        cx, cy, R = 540, 960, 178
        ctx.set_source_rgba(0.08, 0.08, 0.08, 0.85 * rp); ctx.arc(cx, cy, R - 4, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*HL, 0.9); ctx.set_line_width(3)
        ctx.arc(cx, cy, R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eout(rp)); ctx.stroke()
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 0.5)
        ctx.set_source_rgba(*OLIVE, 0.8 * rp); ctx.set_line_width(2); ctx.set_dash([14, 10])
        ctx.arc(0, 0, R + 16, 0, 2 * math.pi); ctx.stroke(); ctx.set_dash([]); ctx.restore()
        for k in range(36):
            a_ = k / 36 * 2 * math.pi
            ctx.set_source_rgba(*HL, 0.35 * rp); ctx.set_line_width(1.5)
            ctx.move_to(cx + math.cos(a_) * (R - 14), cy + math.sin(a_) * (R - 14)); ctx.line_to(cx + math.cos(a_) * (R - 6), cy + math.sin(a_) * (R - 6)); ctx.stroke()
        # redraw text above the ring fill
        draw_text(ctx, f"+{n}", "black", 250, L["nx"], L["ny"], "center", alpha=rp, color=HL8, scale=L["ns"], ltr=True)
        draw_text(ctx, "استهداف", "bold", 104, L["lx"], L["ly"], "center", alpha=rp, scale=L["ls"])

def draw_s1_text(ctx, t):
    out = 1 - seg(t, 3.3, 3.6)
    if out <= 0: return
    a = seg(t, 0.36, 0.6) * out
    draw_text(ctx, "أكثر من", "medium", 66, 540, 520, "center", alpha=a, wipe=eout(seg(t, 0.36, 0.75)))
    # sentence tail, revealed with speech
    p = seg(t, 1.94, 3.62)
    if p > 0:
        ctx.set_source_rgba(*HL, 0.9 * out); ctx.rectangle(540 - 260 * eout(seg(t, 1.85, 2.2)), 985, 520 * eout(seg(t, 1.85, 2.2)), 3); ctx.fill()
        draw_text(ctx, "طال المنظومة الطبية في غزة", "medium", 62, 540, 1060, "center", alpha=out, wipe=p)

# ================================================================ SCENE 2: four categories
CARDS = [
    dict(lbl="المرافق", fn=icon_hospital, cx=790, cy=560, t=4.04, end=(690, 750)),
    dict(lbl="المركبات", fn=icon_ambulance, cx=290, cy=560, t=4.65, end=(390, 750)),
    dict(lbl="الكوادر الطبية", fn=icon_medic, cx=790, cy=1360, t=5.46, end=(690, 1170)),
    dict(lbl="سلاسل الإمداد", fn=icon_supply, cx=290, cy=1360, t=6.45, end=(390, 1170)),
]
CW, CH = 430, 380
for c in CARDS: c["ts"] = c["t"] + 0.6

def draw_card(ctx, c, t):
    p = seg(t, c["t"] - 0.05, c["t"] + 0.4)
    if p <= 0: return
    hit = t - c["ts"]
    sx = sy = 0
    if 0 <= hit < 0.45:
        e = math.exp(-hit * 8) * 12; sx = e * math.sin(hit * 80); sy = e * math.cos(hit * 67)
    s = eback(p)
    ctx.save(); ctx.translate(c["cx"] + sx, c["cy"] + sy); ctx.scale(s, s)
    x, y = -CW / 2, -CH / 2
    panel(ctx, x, y, CW, CH, min(1, p * 1.5))
    # icon (soot-darkened after the strike)
    dmg = eout(seg(hit, 0, 0.5)) if hit > 0 else 0
    fg = (lerp(HL[0], 0.55, dmg), lerp(HL[1], 0.43, dmg), lerp(HL[2], 0.2, dmg), 1)
    ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(0, -40, 0, 0, -40, 150)
    g.add_color_stop_rgba(0, *OLIVE, 0.25 * p); g.add_color_stop_rgba(1, *OLIVE, 0)
    ctx.set_source(g); ctx.arc(0, -40, 150, 0, 2 * math.pi); ctx.fill(); ctx.set_operator(cairo.OPERATOR_OVER)
    draw_icon(ctx, c["fn"], 0, -45, 190 * (0.6 + 0.4 * eout(seg(t, c["t"], c["t"] + 0.5))), fg, cut=(0.09, 0.09, 0.09))
    # cracks after impact
    if dmg > 0:
        ctx.set_source_rgba(0.02, 0.02, 0.02, 0.85 * dmg); ctx.set_line_width(3)
        for k in range(5):
            ang = rnd(k, c["cx"]) * 2 * math.pi
            ctx.move_to(10, -40); px, py = 10, -40
            for st in range(4):
                ang += (rnd(k, st + c["cy"]) - 0.5) * 1.2
                L = 30 * dmg
                px += math.cos(ang) * L; py += math.sin(ang) * L; ctx.line_to(px, py)
            ctx.stroke()
        smoke(ctx, 10, -60, hit, 0.45, life=2.5, n=5, alpha=0.4)
    draw_text(ctx, c["lbl"], "bold", 52, 0, 125, "center", alpha=seg(t, c["t"] + 0.1, c["t"] + 0.35),
              wipe=eout(seg(t, c["t"] + 0.05, c["t"] + 0.45)))
    # targeting
    rp = seg(t, c["ts"] - 0.5, c["ts"])
    if 0 < rp < 1:
        reticle(ctx, 10, -45, 150 - 75 * eout(rp), rp * 2, min(1, rp * 3))
    fireball(ctx, 10, -45, hit, 0.6)
    ctx.restore()

def draw_connectors(ctx, t):
    for c in CARDS:
        p = seg(t, c["t"] - 0.3, c["t"] + 0.05)
        if p <= 0: continue
        ex, ey = c["end"]
        ang = math.atan2(ey - 960, ex - 540)
        sx, sy = 540 + math.cos(ang) * 196, 960 + math.sin(ang) * 196
        px, py = lerp(sx, ex, eio(p)), lerp(sy, ey, eio(p))
        ctx.set_source_rgba(*HL, 0.9); ctx.set_line_width(2.6); ctx.move_to(sx, sy); ctx.line_to(px, py); ctx.stroke()
        ctx.arc(sx, sy, 6, 0, 2 * math.pi); ctx.fill(); ctx.arc(px, py, 5, 0, 2 * math.pi); ctx.fill()
        if p >= 1:
            q = (t * 1.3 + c["t"]) % 1
            qx, qy = lerp(sx, ex, q), lerp(sy, ey, q)
            g = cairo.RadialGradient(qx, qy, 0, qx, qy, 16)
            g.add_color_stop_rgba(0, 1, 1, 1, 0.9); g.add_color_stop_rgba(1, *HL, 0)
            ctx.set_source(g); ctx.arc(qx, qy, 16, 0, 2 * math.pi); ctx.fill()

def draw_s2(ctx, t):
    draw_connectors(ctx, t)
    draw_hub(ctx, t)
    for c in CARDS:
        draw_card(ctx, c, t)

# ================================================================ SCENE 3: ~2000 medical staff killed
COLS3, ROWS3 = 10, 8
def count2000(t):
    return int(round(2000 * eout(seg(t, 8.85, 9.75)) / 10) * 10)

def draw_s3(ctx, t):
    # header line
    draw_text(ctx, "استشهاد قرابة", "medium", 74, 540, 330, "center", alpha=seg(t, 8.38, 8.55), wipe=eout(seg(t, 8.38, 9.05)))
    n = count2000(t)
    if t >= 8.8:
        a = seg(t, 8.8, 8.95)
        g = cairo.RadialGradient(540, 520, 0, 540, 520, 330)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.5 * a); g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g); ctx.arc(540, 520, 330, 0, 2 * math.pi); ctx.fill()
        draw_text(ctx, f"{n}", "black", 250, 540, 520, "center", alpha=a, color=HL8,
                  scale=1 + 0.2 * (1 - eout(seg(t, 8.8, 9.1))) + bump(t, [9.75], 0.3, 0.05), ltr=True)
    draw_text(ctx, "من عناصر الطواقم الطبية", "bold", 66, 540, 710, "center", alpha=seg(t, 9.6, 9.8), wipe=eout(seg(t, 9.6, 10.9)))
    # figure grid
    cw, ch = 88, 84
    x0 = 540 - COLS3 * cw / 2 + cw / 2; y0 = 860
    filled = n / 2000 * COLS3 * ROWS3
    for r in range(ROWS3):
        for c in range(COLS3):
            k = r * COLS3 + c
            cc = COLS3 - 1 - c  # fill right-to-left
            x = x0 + cc * cw; y = y0 + r * ch
            ap = seg(t, 7.85 + 0.012 * k, 8.15 + 0.012 * k)
            if ap <= 0: continue
            on = seg(filled, k, k + 1)
            if on > 0:
                fl = 1 - seg(filled, k + 1, k + 6)
                col = (lerp(0.22, HL[0], on), lerp(0.22, HL[1], on), lerp(0.22, HL[2], on), ap)
                if fl > 0 and on >= 1:
                    ctx.set_operator(cairo.OPERATOR_ADD)
                    g = cairo.RadialGradient(x, y, 0, x, y, 40)
                    g.add_color_stop_rgba(0, *HL, 0.35 * fl); g.add_color_stop_rgba(1, *HL, 0)
                    ctx.set_source(g); ctx.arc(x, y, 40, 0, 2 * math.pi); ctx.fill(); ctx.set_operator(cairo.OPERATOR_OVER)
            else:
                col = (0.22, 0.22, 0.22, ap)
            draw_icon(ctx, icon_person, x, y + 6 * (1 - eout(ap)), 62, col, cut=(0.11, 0.11, 0.11))
    corner_frame(ctx, x0 - cw / 2 - 18, y0 - ch / 2 - 18, COLS3 * cw + 36, ROWS3 * ch + 36, seg(t, 7.9, 8.4) * 0.8)

# ================================================================ SCENE 4: destroyed hospital, 19 / 36
FACADE = [(-300, 0), (-300, -420), (110, -420), (150, -365), (105, -305), (170, -255), (205, -185), (262, -205), (300, -140), (300, 0)]

def poly(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    ctx.close_path()

def flick(t, k):
    return 0.65 + 0.2 * math.sin(t * 13 + k) + 0.15 * math.sin(t * 29 + k * 2.3)

def draw_hospital(ctx, t):
    # interior behind the breach
    ctx.set_source_rgba(0.06, 0.05, 0.045, 1); ctx.rectangle(100, -420, 200, 290); ctx.fill()
    g = cairo.RadialGradient(200, -260, 0, 200, -260, 200)
    g.add_color_stop_rgba(0, 1, 0.5, 0.12, 0.55 * flick(t, 1)); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
    ctx.set_source(g); ctx.rectangle(100, -420, 200, 290); ctx.fill()
    # broken slabs & rebar
    ctx.set_source_rgba(0.18, 0.18, 0.18, 1)
    for yy, x1 in ((-315, 240), (-210, 285)):
        ctx.move_to(100, yy); ctx.line_to(x1, yy + 6); ctx.line_to(x1 - 20, yy + 16); ctx.line_to(100, yy + 14); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(0.45, 0.35, 0.25, 0.8); ctx.set_line_width(2)
    for k in range(6):
        ctx.move_to(130 + k * 22, -318 + (k % 2) * 105); ctx.line_to(140 + k * 22 + rnd(k, 1) * 20, -330 + (k % 2) * 105 - rnd(k, 2) * 18); ctx.stroke()
    # roof block with sign
    ctx.set_source_rgba(0.25, 0.25, 0.25, 1); ctx.rectangle(-130, -500, 200, 80); ctx.fill()
    ctx.save(); ctx.translate(-30, -560); ctx.rotate(0.22)
    ctx.set_source_rgba(0.3, 0.3, 0.3, 1); ctx.set_line_width(8)
    ctx.arc(0, 0, 44, math.pi * 0.15, math.pi * 1.75); ctx.stroke()
    ctx.set_source_rgba(*OLIVE, 1); ctx.rectangle(-9, -32, 18, 64); ctx.rectangle(-32, -9, 64, 18); ctx.fill()
    ctx.set_source_rgba(0.06, 0.06, 0.06, 1); ctx.move_to(14, -36); ctx.line_to(36, -10); ctx.line_to(30, 10); ctx.line_to(10, -12); ctx.close_path(); ctx.fill()
    ctx.restore()
    ctx.set_source_rgba(0.3, 0.3, 0.3, 1); ctx.set_line_width(5); ctx.move_to(-50, -500); ctx.line_to(-38, -522); ctx.stroke()
    # facade
    poly(ctx, FACADE)
    path = ctx.copy_path()
    g = cairo.LinearGradient(0, -420, 0, 0)
    g.add_color_stop_rgb(0, 0.27, 0.27, 0.27); g.add_color_stop_rgb(1, 0.19, 0.19, 0.19)
    ctx.set_source(g); ctx.fill()
    ctx.save(); ctx.append_path(path); ctx.clip()
    # floor slabs
    ctx.set_source_rgba(0.33, 0.33, 0.33, 1)
    for yy in (-420, -315, -210, -105):
        ctx.rectangle(-300, yy, 600, 10); ctx.fill()
    # windows
    wi = 0
    for fl, yy in enumerate((-395, -290, -185, -80)):
        for xx in range(-275, 280, 62):
            wi += 1
            ctx.append_path(path)
            if not ctx.in_fill(xx + 17, yy + 25):
                ctx.new_path(); continue
            ctx.new_path()
            r = rnd(wi, 7)
            ctx.set_source_rgba(0.05, 0.05, 0.05, 1)
            if fl == 3 and -60 < xx < 30:
                ctx.rectangle(xx - 10, yy - 5, 60, 80); ctx.fill()  # entrance
                continue
            ctx.rectangle(xx, yy, 34, 52); ctx.fill()
            if r > 0.62:  # burning room
                g = cairo.RadialGradient(xx + 17, yy + 40, 0, xx + 17, yy + 40, 45)
                g.add_color_stop_rgba(0, 1, 0.7, 0.25, 0.95 * flick(t, wi)); g.add_color_stop_rgba(1, 1, 0.35, 0.05, 0)
                ctx.set_source(g); ctx.rectangle(xx, yy, 34, 52); ctx.fill()
                # soot above
                g = cairo.RadialGradient(xx + 17, yy - 10, 0, xx + 17, yy - 10, 40)
                g.add_color_stop_rgba(0, 0, 0, 0, 0.6); g.add_color_stop_rgba(1, 0, 0, 0, 0)
                ctx.set_source(g); ctx.rectangle(xx - 20, yy - 50, 74, 50); ctx.fill()
            elif r < 0.2:  # shattered
                ctx.set_source_rgba(0.27, 0.27, 0.27, 1)
                ctx.move_to(xx, yy); ctx.line_to(xx + 20, yy + 18); ctx.line_to(xx + 8, yy + 30); ctx.line_to(xx, yy + 52); ctx.close_path(); ctx.fill()
    # cracks
    ctx.set_source_rgba(0.04, 0.04, 0.04, 0.9); ctx.set_line_width(3)
    for k, (sx, sy) in enumerate(((105, -305), (170, -255), (-120, -420), (300, -140))):
        ctx.move_to(sx, sy); px, py = sx, sy; ang = math.pi * (0.6 + 0.5 * rnd(k, 4))
        for st in range(6):
            ang += (rnd(k, st) - 0.5) * 1.0; px += math.cos(ang) * 30; py += abs(math.sin(ang)) * 30; ctx.line_to(px, py)
        ctx.stroke()
    # fire light wash on the facade
    ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(180, -250, 0, 180, -250, 480)
    g.add_color_stop_rgba(0, 1, 0.55, 0.15, 0.22 * flick(t, 3)); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
    ctx.set_source(g); ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.restore()
    # edge highlight
    ctx.append_path(path); ctx.set_source_rgba(*OLIVE, 0.6); ctx.set_line_width(2); ctx.stroke()
    # rubble
    for k in range(26):
        rx = 120 + rnd(k, 11) * 330; rh = (1 - abs(rx - 290) / 190) * 90 * (0.4 + 0.6 * rnd(k, 12))
        ry = -max(8, rh)
        sz = 18 + 30 * rnd(k, 13)
        c = 0.18 + 0.12 * rnd(k, 14)
        ctx.set_source_rgba(c, c, c, 1)
        ctx.move_to(rx - sz / 2, ry + sz / 2); ctx.line_to(rx - sz / 3, ry - sz / 2); ctx.line_to(rx + sz / 2, ry - sz / 3); ctx.line_to(rx + sz / 2, ry + sz / 2); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*OLIVE, 0.7); ctx.rectangle(-480, 0, 960, 3); ctx.fill()

def draw_building_fx(ctx, t, back):
    if back:
        smoke_column(ctx, 190, -330, t, 1, n=18, size=1.0)
        smoke_column(ctx, -180, -300, t, 5, n=10, size=0.7, alpha=0.3)
    else:
        flames(ctx, 200, -230, 150, 1.25, t, 21, n=40, height=200)
        flames(ctx, 150, -360, 90, 0.9, t, 22, n=26)
        flames(ctx, 300, -40, 160, 0.8, t, 23, n=26)
        flames(ctx, -210, -340, 60, 0.6, t, 24, n=16)
        flames(ctx, 28, -130, 60, 0.55, t, 25, n=14)
        embers(ctx, 150, -250, 380, t, 31)

# grid of 36 hospitals
GC, GR = 9, 4
GCW, GCH = 108, 100
GX0 = 540 - GC * GCW / 2 + GCW / 2
GY0 = 1250

def grid_pos(k):
    r, c = divmod(k, GC)
    return GX0 + (GC - 1 - c) * GCW, GY0 + r * GCH

def count19(t):
    return int(round(19 * eout(seg(t, 13.21, 13.95))))

def count36(t):
    return int(round(19 + 17 * eout(seg(t, 16.95, 17.9)))) if t >= 16.95 else 0

def draw_s4(ctx, t):
    # building placement: big hero shot, then moves up to make room for the numbers
    mp = eio(seg(t, 12.85, 13.35))
    bx, by = 540, lerp(1240, 790, mp)
    bs = lerp(1.32, 0.86, mp) * (1 + 0.04 * seg(t, 11.9, 13.0))
    ctx.save(); ctx.translate(bx, by); ctx.scale(bs, bs)
    draw_building_fx(ctx, t, True)
    draw_hospital(ctx, t)
    draw_building_fx(ctx, t, False)
    ctx.restore()
    # ground glow
    ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(bx + 150 * bs, by, 0, bx + 150 * bs, by, 500 * bs)
    g.add_color_stop_rgba(0, 1, 0.5, 0.12, 0.18 * flick(t, 8)); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
    ctx.set_source(g); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)
    # ---- counters
    pa = seg(t, 13.15, 13.4)
    if pa > 0:
        ctx.set_source_rgba(0.08, 0.08, 0.08, 0.92 * pa); ctx.rectangle(0, 830, W, 330); ctx.fill()
        ctx.set_source_rgba(*HL, pa); ctx.rectangle(W - W * eout(pa), 830, W * eout(pa), 3); ctx.fill()
        ctx.set_source_rgba(*OLIVE, 0.8 * pa); ctx.rectangle(0, 1157, W * eout(pa), 2); ctx.fill()
        n19 = count19(t)
        draw_text(ctx, f"{n19}", "black", 210, 760, 950, "center", alpha=pa, color=HL8,
                  scale=1 + 0.25 * (1 - eout(seg(t, 13.21, 13.5))) + bump(t, [13.95], 0.3, 0.06), ltr=True)
        draw_text(ctx, "مستشفى فقط تعمل", "bold", 54, 760, 1090, "center", alpha=seg(t, 13.65, 13.85), wipe=eout(seg(t, 13.65, 15.15)))
        dv = seg(t, 16.55, 16.85)
        if dv > 0:
            ctx.set_source_rgba(*OLIVE, dv); ctx.rectangle(520, 870, 3, 250 * eout(dv)); ctx.fill()
        draw_text(ctx, "من أصل", "medium", 56, 290, 880, "center", alpha=seg(t, 16.6, 16.8), wipe=eout(seg(t, 16.6, 16.95)))
        if t >= 16.95:
            draw_text(ctx, f"{count36(t)}", "black", 170, 290, 1015, "center", alpha=seg(t, 16.95, 17.1),
                      color=(235, 235, 235), scale=1 + 0.2 * (1 - eout(seg(t, 16.95, 17.25))), ltr=True)
    # ---- 36 hospital icons
    ga = seg(t, 13.1, 13.5)
    if ga > 0:
        n19 = count19(t)
        part = eio(seg(t, 18.65, 19.4))
        for k in range(36):
            x, y = grid_pos(k)
            ap = seg(t, 13.1 + 0.008 * k, 13.35 + 0.008 * k)
            if ap <= 0: continue
            sz = 74
            if k < 19:
                on = 1.0 if k < n19 else 0.0
                if on:
                    lit = seg(t, 13.21 + 0.74 * (k / 19), 13.21 + 0.74 * (k / 19) + 0.12)
                    if part > 0:
                        # partial: only the lower part stays lit
                        draw_icon(ctx, icon_hospital, x, y, sz, (0.2, 0.2, 0.2, ap), cut=(0.1, 0.1, 0.1))
                        lvl = lerp(1.0, 0.5, part)
                        top = y + sz * 0.42 - sz * 0.86 * lvl
                        ctx.save(); ctx.rectangle(x - sz, top, sz * 2, sz * 2); ctx.clip()
                        draw_icon(ctx, icon_hospital, x, y, sz, (*HL, ap), cut=(0.1, 0.1, 0.1))
                        ctx.restore()
                        ctx.set_source_rgba(1, 1, 1, 0.8 * part); ctx.rectangle(x - 34, top - 1, 68, 2); ctx.fill()
                    else:
                        draw_icon(ctx, icon_hospital, x, y, sz * (1 + 0.15 * (1 - lit)), (*HL, ap), cut=(0.1, 0.1, 0.1))
                    # operating-status bar: full while working, drops to half for partial operation
                    bw_ = 64 * lit
                    ctx.set_source_rgba(0.25, 0.25, 0.25, ap); ctx.rectangle(x - 32, y + 40, 64, 6); ctx.fill()
                    ctx.set_source_rgba(*HL, ap); ctx.rectangle(x + 32 - bw_ * lerp(1.0, 0.5, part), y + 40, bw_ * lerp(1.0, 0.5, part), 6); ctx.fill()
                else:
                    draw_icon(ctx, icon_hospital, x, y, sz, (0.24, 0.24, 0.24, ap), cut=(0.1, 0.1, 0.1))
            else:
                j = k - 19
                d = seg(t, 16.95 + 0.95 * j / 17, 16.95 + 0.95 * j / 17 + 0.15)
                if d <= 0:
                    draw_icon(ctx, icon_hospital, x, y, sz, (0.24, 0.24, 0.24, ap), cut=(0.1, 0.1, 0.1))
                else:
                    draw_icon(ctx, icon_hospital, x, y, sz, (0.32, 0.27, 0.22, ap), cut=(0.1, 0.1, 0.1), rot=0.12 * d)
                    ctx.set_source_rgba(0.06, 0.06, 0.06, 0.9 * d); ctx.set_line_width(5)
                    ctx.move_to(x - 30, y - 30); ctx.line_to(x + 30, y + 30); ctx.move_to(x + 30, y - 30); ctx.line_to(x - 30, y + 30); ctx.stroke()
                    ctx.set_source_rgba(*OLIVE, d); ctx.set_line_width(2.4)
                    ctx.move_to(x - 30, y - 30); ctx.line_to(x + 30, y + 30); ctx.move_to(x + 30, y - 30); ctx.line_to(x - 30, y + 30); ctx.stroke()
                    flames(ctx, x + 14, y - 22, 26, 0.22, t, 100 + k, n=6, height=110)
        corner_frame(ctx, GX0 - GCW / 2 - 16 - (GC - 1) * 0, GY0 - GCH / 2 - 16, GC * GCW + 32, GR * GCH + 32, 0.7 * ga)
        if part > 0:
            draw_text(ctx, "تعمل بشكل جزئي", "bold", 52, 540, GY0 + GR * GCH + 38, "center", alpha=seg(t, 18.75, 18.95),
                      color=HL8, wipe=eout(seg(t, 18.75, 19.5)))

# ================================================================ background, scenes, post
def draw_bg(ctx, t):
    g = cairo.RadialGradient(W / 2, H * 0.45, 100, W / 2, H * 0.45, 1300)
    g.add_color_stop_rgb(0, 0.135, 0.135, 0.135); g.add_color_stop_rgb(1, 0.075, 0.075, 0.075)
    ctx.set_source(g); ctx.paint()
    # drifting dot grid
    off = (t * 8) % 60
    ctx.set_source_rgba(*HL, 0.07)
    for yy in range(-60, H + 60, 60):
        for xx in range(0, W + 60, 60):
            ctx.rectangle(xx - 1 + (off if (yy // 60) % 2 else -off) * 0.3, yy + off, 2, 2)
    ctx.fill()

def group(ctx, fn, t, alpha, scale=1.0, cx=W / 2, cy=H / 2):
    if alpha <= 0.002: return
    ctx.push_group()
    ctx.save(); ctx.translate(cx, cy); ctx.scale(scale, scale); ctx.translate(-cx, -cy)
    fn(ctx, t)
    ctx.restore()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(alpha)

def drift(t):
    return 4 * math.sin(t * 0.7), 5 * math.sin(t * 0.53 + 1)

yy_, xx_ = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2)
VIG = np.clip(1.0 - 0.40 * np.clip(_d - 0.5, 0, None) ** 1.6, 0.45, 1.0).astype(np.float32)[..., None]
del yy_, xx_, _d
_rng = np.random.default_rng(7)
GRAIN = [_rng.normal(0, 2.2, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]

def surf_array(surf):
    return np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())

def bloom(surf, strength=0.7):
    a = surf_array(surf)
    small = Image.fromarray(a[..., :3].copy()).resize((W // 4, H // 4), Image.BILINEAR)
    s = np.asarray(small).astype(np.float32) / 255
    lum = s.max(axis=2, keepdims=True)
    s = s * np.clip((lum - 0.45) / 0.45, 0, 1)
    im = Image.fromarray((s * 255).astype(np.uint8))
    b1 = np.asarray(im.filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
    b2 = np.asarray(im.filter(ImageFilter.GaussianBlur(11))).astype(np.float32)
    b = Image.fromarray(np.clip(b1 * 0.8 + b2 * 1.2, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    a[..., :3] = np.clip(a[..., :3].astype(np.float32) + np.asarray(b).astype(np.float32) * strength, 0, 255).astype(np.uint8)
    surf.mark_dirty()

def render(i):
    t = i / FPS
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    draw_bg(ctx, t)
    dx, dy = drift(t)
    ctx.translate(dx, dy)
    # scene 1 world (sinks away as the hub takes over)
    group(ctx, draw_s1, t, 1 - seg(t, 3.55, 4.0))
    if t < 3.45:
        draw_hub(ctx, t)
    group(ctx, draw_s1_text, t, 1.0)
    # scene 2, zooms into the medical-staff card on exit
    if 3.45 <= t < 7.9:
        zp = eio(seg(t, 7.3, 7.85))
        group(ctx, draw_s2, t, 1 - seg(t, 7.5, 7.85), scale=1 + 2.6 * zp, cx=790, cy=1300)
    # scene 3
    if 7.45 <= t < 12.1:
        ip = eout(seg(t, 7.5, 8.0)); op = ein(seg(t, 11.45, 11.95))
        group(ctx, draw_s3, t, ip * (1 - op), scale=lerp(0.85, 1.0, ip) * (1 + 0.04 * seg(t, 8, 11.4)) * (1 + 0.5 * op), cx=540, cy=900)
    # scene 4
    if t >= 11.75:
        ip = eout(seg(t, 11.8, 12.3))
        group(ctx, draw_s4, t, ip * (1 - seg(t, 20.45, 20.95)), scale=lerp(1.25, 1.0, ip), cx=540, cy=960)
    # flash on the cut to the burning hospital
    fl = seg(t, 11.8, 11.9) * (1 - seg(t, 11.9, 12.35))
    if fl > 0:
        ctx.identity_matrix(); ctx.set_source_rgba(1, 0.8, 0.5, 0.35 * fl); ctx.paint()
    ctx.identity_matrix()
    surf.flush()
    bloom(surf)
    # HUD corners
    ha = 0.45 * seg(t, 0.2, 1.0) * (1 - seg(t, 20.4, 20.9))
    corner_frame(ctx, 34, 34, W - 68, H - 68, ha, L=50, lw=2)
    surf.flush()
    a = surf_array(surf)[..., :3].astype(np.float32)
    a *= VIG
    gr = GRAIN[i % len(GRAIN)]
    a += np.repeat(np.repeat(gr, 2, axis=0), 2, axis=1)
    a *= seg(t, 0.0, 0.3) * (1 - seg(t, 20.5, 21.0))
    out = np.clip(a, 0, 255).astype(np.uint8)
    return out[..., ::-1].tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        import os
        os.makedirs(f"{WORK}/stills", exist_ok=True)
        for ts in sys.argv[2:]:
            Image.frombytes("RGB", (W, H), render(int(round(float(ts) * FPS)))).save(f"{WORK}/stills/s_{float(ts):05.2f}.jpg", quality=90)
        print("stills ok")
    else:
        import subprocess
        from multiprocessing import Pool
        out = sys.argv[2]
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-preset", "slow", "-b:v", "15M", "-maxrate", "20M", "-bufsize", "30M",
                               "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render, range(N), chunksize=3)):
                ff.stdin.write(fr)
                if k % 90 == 0: print("frame", k, flush=True)
        ff.stdin.close(); ff.wait()
        print("done")
