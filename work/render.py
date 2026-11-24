"""West Bank settler-attacks reel: 1080x1920, 30 fps, synced to the voice-over word timings."""
import math, sys, os, pickle
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "..", "video-tools", "fonts")
W, H, FPS = 1080, 1920, 30
DUR = 32.1
N = int(round(DUR * FPS))

def hexc(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
OLIVE = hexc("896829"); DARK = hexc("1D1D1D"); HL = hexc("C7973B")
HL8 = (0xC7, 0x97, 0x3B); OL8 = (0x89, 0x68, 0x29)
CUT = (0.11, 0.11, 0.11)

# ---------------------------------------------------------------- easing
def clamp(v, a=0.0, b=1.0): return a if v < a else b if v > b else v
def seg(t, a, b): return clamp((t - a) / (b - a))
def eio(p): return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
def eout(p): return 1 - (1 - p) ** 3
def ein(p): return p ** 3
def eback(p, s=1.7):
    p -= 1; return 1 + p * p * ((s + 1) * p + s)
def lerp(a, b, p): return a + (b - a) * p
def rnd(i, k=0):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)
def bump(t, times, dur=0.25, amt=0.06):
    b = 0
    for ti in times:
        a = t - ti
        if 0 <= a < dur: b = max(b, amt * math.sin(math.pi * a / dur))
    return b

# ---------------------------------------------------------------- text
FONTS = {"heavy": f"{FD}/DIN NEXT™ ARABIC HEAVY.otf", "bold": f"{FD}/DIN NEXT™ ARABIC BOLD (1).otf",
         "medium": f"{FD}/DIN NEXT™ ARABIC MEDIUM .otf", "light": f"{FD}/DIN NEXT™ ARABIC LIGHT.otf"}
_tc = {}; _fc = {}

def pil_to_surface(im):
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    al = a[..., 3:4] / 255.0
    rgb = a[..., :3] * al
    bgra = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], a[..., 3]]).astype(np.uint8)
    h, w = bgra.shape[:2]
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
    return cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)

def font(name, size):
    k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(FONTS[name], size, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]

def text_surface(s, fname, size, color=(255, 255, 255), ltr=False):
    key = (s, fname, size, color, ltr)
    if key in _tc: return _tc[key]
    if len(_tc) > 300: _tc.clear()
    f = font(fname, size)
    kw = dict(direction="ltr") if ltr else dict(direction="rtl", language="ar")
    bbox = f.getbbox(s, **kw)
    pad = 12
    w = bbox[2] - bbox[0] + pad * 2; h = bbox[3] - bbox[1] + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bbox[0], pad - bbox[1]), s, font=f, fill=color + (255,), **kw)
    r = (pil_to_surface(im), w, h, pad)
    _tc[key] = r
    return r

def text_w(s, fname, size, ltr=False):
    _, w, h, pad = text_surface(s, fname, size, ltr=ltr)
    return w - 2 * pad

def draw_text(ctx, s, fname, size, x, y, align="center", alpha=1.0, color=(255, 255, 255), scale=1.0, ltr=False, wipe=1.0):
    """anchor = vertical centre; wipe reveals right-to-left (Arabic reading order)."""
    if alpha <= 0 or wipe <= 0: return
    surf, w, h, pad = text_surface(s, fname, size, color, ltr)
    if align == "right": x0 = -w + pad
    elif align == "left": x0 = -pad
    else: x0 = -w / 2
    ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale)
    if wipe < 1:
        ctx.rectangle(x0 + w * (1 - wipe), -h / 2 - 5, w * wipe + 5, h + 10); ctx.clip()
    ctx.set_source_surface(surf, x0, -h / 2); ctx.paint_with_alpha(alpha)
    if 0 < wipe < 1:
        ctx.set_source_rgba(*HL, alpha); ctx.rectangle(x0 + w * (1 - wipe) - 2, -h / 2 + 8, 4, h - 16); ctx.fill()
    ctx.restore()

def counter_text(ctx, n, size, x, y, alpha, scale=1.0, color=HL8):
    draw_text(ctx, f"{n:,}", "heavy", size, x, y, "center", alpha=alpha, color=color, scale=scale, ltr=True)

# ---------------------------------------------------------------- frames / panels
def corner_frame(ctx, x, y, w, h, alpha, L=28, lw=3, col=HL):
    if alpha <= 0: return
    ctx.set_source_rgba(*col, alpha); ctx.set_line_width(lw)
    for cx_, cy_, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        ctx.move_to(cx_, cy_ + sy * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx * L, cy_); ctx.stroke()

def panel(ctx, x, y, w, h, alpha, fill=0.88, glow=0.0):
    if alpha <= 0: return
    ctx.set_source_rgba(0.085, 0.085, 0.085, fill * alpha); ctx.rectangle(x, y, w, h); ctx.fill()
    if glow > 0:
        g = cairo.LinearGradient(0, y, 0, y + h)
        g.add_color_stop_rgba(0, *OLIVE, 0.22 * glow * alpha); g.add_color_stop_rgba(1, *OLIVE, 0)
        ctx.set_source(g); ctx.rectangle(x, y, w, h); ctx.fill()
    ctx.set_source_rgba(*OLIVE, 0.9 * alpha); ctx.set_line_width(1.5); ctx.rectangle(x + .75, y + .75, w - 1.5, h - 1.5); ctx.stroke()
    corner_frame(ctx, x - 8, y - 8, w + 16, h + 16, alpha)

def glow_disc(ctx, x, y, r, a, col=OLIVE):
    if a <= 0: return
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *col, a); g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

def dark_disc(ctx, x, y, r, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, 0, 0, 0, a); g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

def pulse_rings(ctx, x, y, r0, t, a, n=2, spread=46, speed=0.9):
    for k in range(n):
        q = (t * speed + k / n) % 1.0
        ctx.set_source_rgba(*HL, 0.6 * (1 - q) * a); ctx.set_line_width(2)
        ctx.arc(x, y, r0 + spread * q, 0, 2 * math.pi); ctx.stroke()

# ---------------------------------------------------------------- effects
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
        c0 = (1, 0.92, 0.65) if u < 0.25 else (1, 0.58, 0.16) if u < 0.6 else (0.75, 0.25, 0.06)
        a = (1 - u) * 0.55
        g = cairo.RadialGradient(px, py, 0, px, py, r)
        g.add_color_stop_rgba(0, *c0, a); g.add_color_stop_rgba(1, c0[0], c0[1] * 0.5, 0, 0)
        ctx.set_source(g); ctx.arc(px, py, r, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def smoke_column(ctx, x, y, t, seed, n=16, size=1.0, alpha=0.42, drift=160, rise=620):
    for i in range(n):
        L = 3.5 + 1.5 * rnd(i, seed)
        age = (t + rnd(i, seed + 1) * L) % L
        u = age / L
        px = x + (rnd(i, seed + 2) - 0.5) * 60 * size + u * drift * size + math.sin(t * 0.7 + i) * 20 * u
        py = y - u * rise * size
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

def burst(ctx, x, y, age, size=1.0, n=10, col=HL):
    """small debris / chips burst"""
    if age < 0 or age > 0.7: return
    for k in range(n):
        ang = -math.pi * (0.05 + 0.9 * rnd(k, x + y))
        v = (180 + 240 * rnd(k, y)) * size
        px = x + math.cos(ang) * v * age; py = y + math.sin(ang) * v * age + 700 * age * age * size
        ctx.set_source_rgba(*col, 1 - age / 0.7); ctx.rectangle(px - 3 * size, py - 3 * size, 6 * size, 6 * size); ctx.fill()

def flick(t, k=1):
    return 0.75 + 0.25 * math.sin(t * 17 + k) * math.sin(t * 5.3 + 2 * k)

# ---------------------------------------------------------------- icons (unit box -50..50)
def icon_tree(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(-7, 48); ctx.line_to(7, 48); ctx.line_to(4, 18); ctx.line_to(14, 4); ctx.line_to(9, 2); ctx.line_to(1, 12)
    ctx.line_to(-4, 0); ctx.line_to(-9, 2); ctx.line_to(-4, 18); ctx.close_path(); ctx.fill()
    for cx_, cy_, r in ((0, -18, 24), (-21, -8, 18), (21, -8, 18), (-11, -33, 17), (12, -31, 17), (0, -2, 15)):
        ctx.arc(cx_, cy_, r, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    for cx_, cy_ in ((-14, -14), (8, -22), (18, -4), (-4, -36), (-22, 0)):
        ctx.save(); ctx.translate(cx_, cy_); ctx.scale(1, 1.4); ctx.arc(0, 0, 2.8, 0, 2 * math.pi); ctx.restore(); ctx.fill()

def icon_seedling(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.save(); ctx.translate(0, 40); ctx.scale(1, 0.32); ctx.arc(0, 0, 36, math.pi, 2 * math.pi); ctx.restore(); ctx.close_path(); ctx.fill()
    ctx.set_line_width(6); ctx.move_to(0, 40); ctx.curve_to(0, 20, -2, 4, 0, -8); ctx.stroke()
    ctx.move_to(0, -2); ctx.curve_to(-10, -22, -30, -26, -42, -20); ctx.curve_to(-34, -4, -16, 2, 0, -2); ctx.fill()
    ctx.move_to(0, -10); ctx.curve_to(8, -32, 26, -42, 40, -38); ctx.curve_to(36, -20, 18, -8, 0, -10); ctx.fill()

def icon_person(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.arc(0, -24, 14, 0, 2 * math.pi); ctx.fill()
    ctx.move_to(-31, 44); ctx.curve_to(-31, 4, -20, -5, 0, -5); ctx.curve_to(20, -5, 31, 4, 31, 44); ctx.close_path(); ctx.fill()

def icon_injured(ctx, fg, cut=CUT):
    icon_person(ctx, fg, cut)
    ctx.set_source_rgba(*cut, 1); ctx.set_line_width(4.5)
    ctx.move_to(-15, -30); ctx.line_to(15, -21); ctx.stroke()
    ctx.rectangle(-4, 12, 8, 22); ctx.rectangle(-11, 19, 22, 8); ctx.fill()

def icon_settler(ctx, fg, cut=CUT):
    """civilian figure with cap and slung rifle"""
    ctx.set_source_rgba(*fg)
    ctx.arc(0, -22, 14, 0, 2 * math.pi); ctx.fill()
    ctx.rectangle(-16, -38, 30, 9); ctx.fill(); ctx.rectangle(-26, -33, 20, 5); ctx.fill()
    ctx.move_to(-31, 44); ctx.curve_to(-31, 6, -20, -3, 0, -3); ctx.curve_to(20, -3, 31, 6, 31, 44); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.set_line_width(5)
    ctx.move_to(-24, 40); ctx.line_to(22, 2); ctx.stroke()
    ctx.set_source_rgba(*fg); ctx.set_line_width(6); ctx.move_to(14, 10); ctx.line_to(44, -22); ctx.stroke()
    ctx.rectangle(30, -12, 6, 10); ctx.fill()

def icon_soldier(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.arc(0, -20, 14, 0, 2 * math.pi); ctx.fill()
    ctx.arc(0, -24, 19, math.pi, 2 * math.pi); ctx.close_path(); ctx.fill()
    ctx.rectangle(-22, -26, 44, 5); ctx.fill()
    ctx.move_to(-33, 44); ctx.curve_to(-33, 6, -22, -2, 0, -2); ctx.curve_to(22, -2, 33, 6, 33, 44); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.rectangle(-20, 14, 14, 10); ctx.rectangle(6, 14, 14, 10); ctx.fill()
    ctx.set_line_width(3); ctx.move_to(-12, -30); ctx.line_to(12, -30); ctx.stroke()
    ctx.set_source_rgba(*fg); ctx.set_line_width(7); ctx.move_to(-46, 26); ctx.line_to(30, -12); ctx.stroke()
    ctx.set_line_width(4); ctx.move_to(30, -12); ctx.line_to(48, -21); ctx.stroke()

def icon_sack(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(-10, -30); ctx.curve_to(-36, -16, -44, 20, -30, 38); ctx.curve_to(-14, 46, 14, 46, 30, 38)
    ctx.curve_to(44, 20, 36, -16, 10, -30); ctx.close_path(); ctx.fill()
    ctx.move_to(-10, -30); ctx.line_to(-18, -44); ctx.line_to(0, -38); ctx.line_to(18, -44); ctx.line_to(10, -30); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.set_line_width(4); ctx.move_to(-12, -28); ctx.line_to(12, -28); ctx.stroke()

def icon_wheat(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg); ctx.set_line_width(4)
    for ang in (-0.32, 0, 0.32):
        ctx.save(); ctx.translate(0, 46); ctx.rotate(ang)
        ctx.move_to(0, 0); ctx.line_to(0, -62); ctx.stroke()
        for k in range(5):
            yy = -58 - 0 + k * 9
            for sx in (-1, 1):
                ctx.save(); ctx.translate(sx * 6, yy - 30); ctx.rotate(sx * 0.5); ctx.scale(0.55, 1)
                ctx.arc(0, 0, 7, 0, 2 * math.pi); ctx.restore(); ctx.fill()
        ctx.save(); ctx.translate(0, -96); ctx.scale(0.55, 1); ctx.arc(0, 0, 7, 0, 2 * math.pi); ctx.restore(); ctx.fill()
        ctx.restore()

def icon_olive(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg); ctx.set_line_width(4.5)
    ctx.move_to(-44, 34); ctx.curve_to(-10, 20, 14, -6, 40, -36); ctx.stroke()
    for k, (x, y, a) in enumerate(((-30, 26, -1.9), (-14, 16, -2.3), (2, 4, -1.7), (16, -10, -2.4), (28, -24, -1.6), (-22, 30, 0.9), (-4, 18, 1.2), (12, 2, 0.8))):
        ctx.save(); ctx.translate(x, y); ctx.rotate(a); ctx.scale(1, 0.38); ctx.arc(0, -22, 18, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    for x, y in ((-8, 34), (8, 22), (24, 6)):
        ctx.save(); ctx.translate(x, y); ctx.scale(0.8, 1); ctx.arc(0, 0, 8, 0, 2 * math.pi); ctx.restore(); ctx.fill()

def icon_crate(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    for x, y, r in ((-24, -8, 14), (0, -14, 15), (24, -8, 14), (-12, -24, 12), (13, -26, 12)):
        ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
    ctx.rectangle(-46, -4, 92, 48); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    for yy in (8, 24):
        ctx.rectangle(-40, yy, 80, 5); ctx.fill()
    ctx.set_line_width(3); ctx.move_to(0, -30); ctx.line_to(4, -40); ctx.stroke()

def icon_grapes(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    for row, n in enumerate((4, 3, 2, 1)):
        for k in range(n):
            ctx.arc((k - (n - 1) / 2) * 19, -14 + row * 17, 10, 0, 2 * math.pi); ctx.fill()
    ctx.set_line_width(4); ctx.move_to(0, -24); ctx.curve_to(0, -36, 6, -42, 14, -46); ctx.stroke()
    ctx.move_to(4, -34); ctx.curve_to(18, -48, 38, -44, 40, -30); ctx.curve_to(26, -24, 12, -26, 4, -34); ctx.fill()

def icon_flame(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(0, 48); ctx.curve_to(-34, 48, -42, 18, -28, -4); ctx.curve_to(-22, -14, -20, -24, -14, -40)
    ctx.curve_to(-4, -26, 4, -22, 6, -10); ctx.curve_to(10, -28, 18, -38, 14, -52); ctx.curve_to(38, -30, 42, 0, 36, 18)
    ctx.curve_to(32, 38, 18, 48, 0, 48); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.move_to(0, 44); ctx.curve_to(-16, 44, -20, 30, -12, 18); ctx.curve_to(-6, 10, -2, 4, 0, -6)
    ctx.curve_to(8, 6, 18, 16, 16, 28); ctx.curve_to(14, 40, 8, 44, 0, 44); ctx.fill()

def icon_car(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(-48, 22); ctx.line_to(-48, 4); ctx.curve_to(-48, -2, -44, -4, -36, -5); ctx.line_to(-26, -6)
    ctx.line_to(-16, -26); ctx.line_to(18, -26); ctx.line_to(30, -6); ctx.line_to(42, -4); ctx.curve_to(48, -2, 48, 4, 48, 8)
    ctx.line_to(48, 22); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.move_to(-20, -8); ctx.line_to(-13, -21); ctx.line_to(-2, -21); ctx.line_to(-2, -8); ctx.close_path(); ctx.fill()
    ctx.move_to(3, -8); ctx.line_to(3, -21); ctx.line_to(15, -21); ctx.line_to(23, -8); ctx.close_path(); ctx.fill()
    for wx in (-28, 28):
        ctx.arc(wx, 22, 13, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*fg)
    for wx in (-28, 28):
        ctx.arc(wx, 22, 9, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    for wx in (-28, 28):
        ctx.arc(wx, 22, 3.5, 0, 2 * math.pi); ctx.fill()

def icon_house(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(-44, -2); ctx.line_to(0, -42); ctx.line_to(44, -2); ctx.line_to(36, -2); ctx.line_to(36, 44)
    ctx.line_to(-36, 44); ctx.line_to(-36, -2); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.rectangle(-8, 18, 16, 26); ctx.rectangle(-26, 4, 13, 12); ctx.rectangle(13, 4, 13, 12); ctx.fill()

def icon_vandal(ctx, fg, cut=CUT):
    """house with smashed windows and a crack"""
    icon_house(ctx, fg, cut)
    ctx.set_source_rgba(*cut, 1); ctx.set_line_width(4.2)
    ctx.move_to(4, -40); ctx.line_to(-6, -20); ctx.line_to(6, -8); ctx.line_to(-4, 6); ctx.line_to(4, 16); ctx.stroke()
    ctx.set_line_width(2.4); ctx.move_to(-6, -20); ctx.line_to(-20, -14); ctx.move_to(6, -8); ctx.line_to(20, -16); ctx.stroke()

def icon_theft(ctx, fg, cut=CUT):
    """property carried away: house -> sack with an arrow"""
    ctx.save(); ctx.translate(-20, 6); ctx.scale(0.58, 0.58); icon_house(ctx, fg, cut); ctx.restore()
    ctx.save(); ctx.translate(26, 14); ctx.scale(0.52, 0.52); icon_sack(ctx, fg, cut); ctx.restore()
    ctx.set_source_rgba(*fg); ctx.set_line_width(4)
    ctx.move_to(-20, -26); ctx.curve_to(-8, -44, 14, -44, 24, -24); ctx.stroke()
    ctx.move_to(30, -14); ctx.line_to(16, -24); ctx.line_to(30, -32); ctx.close_path(); ctx.fill()

def icon_gun(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(-48, -6); ctx.line_to(-4, -6); ctx.line_to(2, -14); ctx.line_to(30, -14); ctx.line_to(48, -8); ctx.line_to(48, 12)
    ctx.line_to(34, 12); ctx.line_to(28, 2); ctx.line_to(14, 2); ctx.line_to(10, 24); ctx.line_to(0, 24); ctx.line_to(2, 2)
    ctx.line_to(-14, 2); ctx.line_to(-14, 0); ctx.line_to(-48, 0); ctx.close_path(); ctx.fill()
    ctx.rectangle(-12, -18, 12, 4); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.rectangle(16, -9, 10, 4); ctx.fill()

def icon_fist(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.save(); ctx.translate(0, -6)
    r = 10
    x, y, w, h = -30, -30, 56, 46
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path(); ctx.fill()
    ctx.rectangle(-22, 12, 40, 34); ctx.fill()
    ctx.move_to(-30, -4); ctx.curve_to(-44, -2, -44, 18, -26, 18); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.set_line_width(3.2)
    for xx in (-16, -2, 12):
        ctx.move_to(xx, -30); ctx.line_to(xx, -10); ctx.stroke()
    ctx.move_to(-30, 4); ctx.line_to(-12, 4); ctx.stroke()
    ctx.restore()

def icon_calendar(ctx, fg, cut=CUT, fill_n=0):
    ctx.set_source_rgba(*fg)
    ctx.rectangle(-44, -36, 88, 82); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.rectangle(-38, -14, 76, 54); ctx.fill()
    ctx.set_source_rgba(*fg)
    for x in (-24, 24):
        ctx.rectangle(x - 4, -48, 8, 20); ctx.fill()
    for k in range(30):
        r, c = divmod(k, 6)
        cx_ = 30 - c * 12.2; cy_ = -6 + r * 9.8
        on = k < fill_n
        ctx.set_source_rgba(*fg) if on else ctx.set_source_rgba(fg[0], fg[1], fg[2], 0.22 * fg[3])
        ctx.rectangle(cx_ - 4.5, cy_ - 3.5, 9, 7); ctx.fill()

def icon_axe(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg); ctx.set_line_width(6)
    ctx.move_to(-30, 44); ctx.line_to(20, -38); ctx.stroke()
    ctx.move_to(8, -38); ctx.curve_to(18, -52, 40, -48, 44, -30); ctx.line_to(22, -20); ctx.close_path(); ctx.fill()

def draw_icon(ctx, fn, x, y, size, fg, cut=CUT, rot=0.0, **kw):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(size / 100, size / 100)
    fn(ctx, fg, cut, **kw); ctx.restore()

# ---------------------------------------------------------------- articulated figure (feet at y=0, ~180 units tall)
def limb(ctx, x0, y0, a1, l1, a2, l2):
    x1 = x0 + math.sin(a1) * l1; y1 = y0 + math.cos(a1) * l1
    x2 = x1 + math.sin(a1 + a2) * l2; y2 = y1 + math.cos(a1 + a2) * l2
    ctx.move_to(x0, y0); ctx.line_to(x1, y1); ctx.line_to(x2, y2); ctx.stroke()
    return x2, y2, a1 + a2

def figure(ctx, x, y, s, col, face=1, lean=0.0, armF=(0.4, 0.4), armB=(-0.3, 0.3), legF=(0.18, -0.05), legB=(-0.18, 0.08),
           head=None, hold=None, hold_ang=None, back=None, t=0.0, rim=None):
    def body(c):
        ctx.save(); ctx.translate(x, y); ctx.scale(s * face, s); ctx.rotate(lean)
        ctx.set_source_rgba(*c); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        if back == "sack":
            ctx.save(); ctx.translate(-22, -136); ctx.rotate(-0.4); ctx.scale(0.62, 0.62); icon_sack(ctx, c); ctx.restore()
            ctx.set_source_rgba(*c)
        ctx.set_line_width(15)
        limb(ctx, -4, -82, legB[0], 44, legB[1], 44)
        ctx.set_line_width(11)
        limb(ctx, -2, -134, armB[0], 32, armB[1], 30)
        ctx.set_line_width(15)
        limb(ctx, 4, -82, legF[0], 44, legF[1], 44)
        ctx.set_line_width(31); ctx.move_to(0, -132); ctx.line_to(0, -88); ctx.stroke()
        ctx.arc(0, -162, 14, 0, 2 * math.pi); ctx.fill()
        if head == "cap":
            ctx.rectangle(-14, -178, 26, 8); ctx.fill(); ctx.rectangle(6, -174, 16, 4); ctx.fill()
        elif head == "helmet":
            ctx.arc(0, -165, 19, math.pi, 2 * math.pi); ctx.close_path(); ctx.fill(); ctx.rectangle(-21, -167, 42, 5); ctx.fill()
        elif head == "scarf":
            ctx.move_to(-14, -170); ctx.line_to(-24, -128); ctx.line_to(-4, -140); ctx.close_path(); ctx.fill()
        ctx.set_line_width(11)
        hx, hy, ha = limb(ctx, 2, -134, armF[0], 32, armF[1], 30)
        if hold:
            a = ha if hold_ang is None else hold_ang
            dx, dy = math.sin(a), math.cos(a)
            if hold == "stick":
                ctx.set_line_width(6); ctx.move_to(hx - dx * 14, hy - dy * 14); ctx.line_to(hx + dx * 70, hy + dy * 70); ctx.stroke()
            elif hold == "axe":
                ctx.set_line_width(6); ctx.move_to(hx - dx * 10, hy - dy * 10); ctx.line_to(hx + dx * 66, hy + dy * 66); ctx.stroke()
                ex, ey = hx + dx * 62, hy + dy * 62
                ctx.save(); ctx.translate(ex, ey); ctx.rotate(-a)
                ctx.move_to(-3, -4); ctx.curve_to(-20, -6, -26, 10, -24, 22); ctx.line_to(3, 10); ctx.close_path(); ctx.fill(); ctx.restore()
            elif hold == "rifle":
                ctx.set_line_width(7); ctx.move_to(hx - dx * 26, hy - dy * 26); ctx.line_to(hx + dx * 62, hy + dy * 62); ctx.stroke()
                ctx.set_line_width(4); ctx.move_to(hx + dx * 62, hy + dy * 62); ctx.line_to(hx + dx * 82, hy + dy * 82); ctx.stroke()
            elif hold == "torch":
                ctx.set_line_width(6); ctx.move_to(hx - dx * 8, hy - dy * 8); ctx.line_to(hx + dx * 40, hy + dy * 40); ctx.stroke()
        ctx.restore()
        if hold:
            a = ha if hold_ang is None else hold_ang
            m = cairo.Matrix(); m.translate(x, y); m.scale(s * face, s); m.rotate(lean)
            return m, (hx, hy, a)
        return None, None
    if rim is not None:
        ctx.save(); ctx.translate(rim[0], rim[1]); body(rim[2]); ctx.restore()
    return body(col)

def tip_point(info, dist):
    m, (hx, hy, a) = info
    return m.transform_point(hx + math.sin(a) * dist, hy + math.cos(a) * dist)

# ---------------------------------------------------------------- map
MAP = pickle.load(open(os.path.join(HERE, "geo", "map.pkl"), "rb"))
WBC = MAP["wb_c"]
SPOTS = MAP["spots"]

def ring_path(ctx, ring):
    ctx.move_to(*ring[0])
    for p in ring[1:]: ctx.line_to(*p)
    ctx.close_path()

def ring_len(ring): return sum(math.dist(a, b) for a, b in zip(ring, ring[1:]))
WB_LEN = [ring_len(r[0]) for r in MAP["wb"]]

class View:
    def __init__(self, cx, cy, z, sy, a):
        self.cx, self.cy, self.z, self.sy, self.a = cx, cy, z, sy, a
    def s(self, p): return (W / 2 + (p[0] - self.cx) * self.z, self.sy + (p[1] - self.cy) * self.z)
    def apply(self, ctx):
        ctx.translate(W / 2, self.sy); ctx.scale(self.z, self.z); ctx.translate(-self.cx, -self.cy)

def vmix(a, b, p):
    return (lerp(a[0], b[0], p), lerp(a[1], b[1], p), math.exp(lerp(math.log(a[2]), math.log(b[2]), p)), lerp(a[3], b[3], p), lerp(a[4], b[4], p))

HUWARA = SPOTS[0]
def camera(t):
    s = (-40, 20, 2.3, 960, 1.0)
    s = vmix(s, (WBC[0], WBC[1] - 2, 11.2, 960, 1.0), eio(seg(t, 0.05, 2.6)))
    s = vmix(s, (WBC[0], WBC[1] - 2, 15.5, 960, 0.14), eio(seg(t, 2.55, 3.2)))
    s = vmix(s, (WBC[0], WBC[1], 5.1, 655, 1.0), eio(seg(t, 5.2, 5.95)))
    if t > 5.95:
        s = (s[0], s[1], s[2] * (1 + 0.035 * seg(t, 5.95, 11.2)), s[3], s[4])
    s = vmix(s, (HUWARA[0], HUWARA[1], 70, 655, 0.0), ein(seg(t, 11.2, 11.9)))
    return View(*s)

def draw_grid(ctx, v, alpha):
    if alpha <= 0: return
    for step, a in ((5, 0.06), (25, 0.10), (100, 0.10)):
        px = step * v.z
        if px < 26: continue
        fa = alpha * a * clamp((px - 26) / 60)
        if px > 900: fa *= clamp(1 - (px - 900) / 900)
        if fa <= 0.003: continue
        x0 = v.cx - (W / 2 + 20) / v.z; x1 = v.cx + (W / 2 + 20) / v.z
        y0 = v.cy - (v.sy + 20) / v.z; y1 = v.cy + (H - v.sy + 20) / v.z
        ctx.set_source_rgba(*HL, fa); ctx.set_line_width(1)
        gx = math.floor(x0 / step) * step
        while gx <= x1:
            sx = v.s((gx, 0))[0]; ctx.move_to(round(sx) + .5, 0); ctx.line_to(round(sx) + .5, H); gx += step
        gy = math.floor(y0 / step) * step
        while gy <= y1:
            sy = v.s((0, gy))[1]; ctx.move_to(0, round(sy) + .5); ctx.line_to(W, round(sy) + .5); gy += step
        ctx.stroke()

def spot_on(k, t):
    """hotspot visibility"""
    return seg(t, 1.5 + 0.045 * k, 1.75 + 0.045 * k)

def draw_map(ctx, t):
    v = camera(t)
    if v.a <= 0.003: return
    ctx.push_group()
    draw_grid(ctx, v, 1.0)
    reveal = eout(seg(t, 0.05, 1.9))
    ctx.save(); v.apply(ctx)
    for r in MAP["land"]:
        for ring in r: ring_path(ctx, ring)
    ctx.restore()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.set_source_rgba(0.155, 0.150, 0.140, 0.4 + 0.6 * reveal); ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    for ring in MAP["borders"]:
        ctx.save(); v.apply(ctx); ctx.move_to(*ring[0])
        for p in ring[1:]: ctx.line_to(*p)
        ctx.restore()
    ctx.set_source_rgba(*HL, 0.22 * reveal); ctx.set_line_width(1.3); ctx.stroke()
    # West Bank
    wp = eout(seg(t, 0.6, 2.2))
    ctx.save(); v.apply(ctx)
    for r in MAP["wb"]: ring_path(ctx, r[0])
    ctx.restore()
    path = ctx.copy_path()
    ctx.set_source_rgba(*OLIVE, 0.30 * wp + 0.06 * math.sin(t * 2.2) * wp); ctx.fill()
    ctx.save(); ctx.append_path(path); ctx.clip()
    for ring in MAP["gov"]:
        ctx.save(); v.apply(ctx); ring_path(ctx, ring); ctx.restore()
    ctx.set_dash([5, 5]); ctx.set_source_rgba(*HL, 0.33 * wp); ctx.set_line_width(1.1); ctx.stroke(); ctx.set_dash([])
    ctx.restore()
    for r, L in zip(MAP["wb"], WB_LEN):
        Lpx = L * v.z
        for lw, a in ((12, 0.12), (6, 0.25), (2.6, 1.0)):
            ctx.save(); v.apply(ctx); ring_path(ctx, r[0]); ctx.restore()
            ctx.set_dash([max(0.01, Lpx * wp), Lpx + 10])
            ctx.set_source_rgba(*HL, a * wp); ctx.set_line_width(lw); ctx.stroke()
    ctx.set_dash([])
    # hotspots
    for k, p in enumerate(SPOTS):
        a = spot_on(k, t)
        if a <= 0: continue
        x, y = v.s(p)
        act = 1 + 0.5 * seg(t, 5.6, 6.0)
        if a < 1:
            ctx.set_source_rgba(*HL, 0.8 * (1 - a)); ctx.set_line_width(2); ctx.arc(x, y, 6 + 30 * a, 0, 2 * math.pi); ctx.stroke()
        glow_disc(ctx, x, y, 34 * act, 0.35 * a, HL)
        pulse_rings(ctx, x, y, 7, t + rnd(k, 3), a * 0.8, n=1, spread=30 * act, speed=0.8 + 0.4 * rnd(k, 4))
        ctx.set_source_rgba(*DARK, a); ctx.arc(x, y, 7.5, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 0.86, 0.6, a); ctx.arc(x, y, 4.5, 0, 2 * math.pi); ctx.fill()
    # West Bank label
    la = seg(t, 0.9, 1.3) * (1 - seg(t, 2.45, 2.75)) + seg(t, 5.8, 6.2) * (1 - seg(t, 10.9, 11.2))
    if la > 0:
        if t < 4:
            lx, ly = v.s((WBC[0] - 6, WBC[1] + 10)); sz = 70
            dark_disc(ctx, lx, ly, 260, 0.55 * la)
            draw_text(ctx, "الضفة الغربية", "heavy", sz, lx, ly, alpha=la, wipe=eout(seg(t, 0.9, 1.6)))
        else:
            ex, ey = v.s((WBC[0] - 16, WBC[1] + 8))
            tw = text_w("الضفة الغربية", "bold", 42)
            lx, ly = 100 + tw / 2, 840
            q = eout(seg(t, 5.8, 6.3))
            ctx.set_source_rgba(*HL, 0.8 * la); ctx.set_line_width(2)
            ctx.move_to(ex, ey); ctx.line_to(lerp(ex, lx + tw / 2, q), lerp(ey, ly + 36, q)); ctx.stroke()
            ctx.arc(ex, ey, 5, 0, 2 * math.pi); ctx.fill()
            draw_text(ctx, "الضفة الغربية", "bold", 42, lx, ly, alpha=la, wipe=eout(seg(t, 6.0, 6.5)))
            ctx.set_source_rgba(*HL, la); ctx.rectangle(lx - tw / 2 + tw * (1 - q), ly + 34, tw * q, 3); ctx.fill()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(v.a)

# ================================================================ SCENE 2: 4000 trees and seedlings
GRID2 = []
for r in range(3):
    for c in range(6):
        GRID2.append((540 + (2.5 - c) * 140, 1355 + r * 92, (r + c) % 3 == 1))
_order = sorted(range(18), key=lambda k: rnd(k, 77))
KILL2 = {k: 3.25 + 1.9 * i / 17 for i, k in enumerate(_order)}
CHOPS = [3.35, 3.85, 4.35]
FALL = 4.6

def count4000(t): return int(round(4000 * eout(seg(t, 3.18, 4.05)) / 10) * 10)

def axe_angle(t):
    """swing: wind-up then strike at each chop time"""
    a = -2.6
    for c in CHOPS:
        if c - 0.35 <= t < c: a = lerp(-2.6, -0.95, ein(seg(t, c - 0.35, c)))
        elif c <= t < c + 0.15: a = -0.95
        elif c + 0.15 <= t < c + 0.5: a = lerp(-0.95, -2.6, eio(seg(t, c + 0.15, c + 0.5)))
    if t >= CHOPS[-1] + 0.5: a = -2.6 + 0.08 * math.sin(t * 3)
    return a

def draw_s2(ctx, t):
    # "more than"
    draw_text(ctx, "أكثر من", "medium", 70, 540, 350, alpha=seg(t, 2.74, 2.95), wipe=eout(seg(t, 2.74, 3.15)))
    if t >= 3.15:
        a = seg(t, 3.15, 3.3)
        dark_disc(ctx, 540, 500, 380, 0.5 * a)
        counter_text(ctx, count4000(t), 230, 540, 500, a, scale=1 + 0.22 * (1 - eout(seg(t, 3.15, 3.45))) + bump(t, [4.05], 0.3, 0.06))
    if t >= 4.0:
        q = eout(seg(t, 4.0, 4.35))
        ctx.set_source_rgba(*HL, 0.9); ctx.rectangle(540 - 240 * q, 628, 480 * q, 3); ctx.fill()
        draw_text(ctx, "شجرة وشتلة", "bold", 84, 540, 705, alpha=seg(t, 4.0, 4.15), wipe=eout(seg(t, 4.0, 4.7)))
    # hero: settler cutting an olive tree
    ha = seg(t, 2.9, 3.3)
    if ha > 0:
        ctx.push_group()
        gy = 1232
        ctx.set_source_rgba(*OLIVE, 0.75); ctx.rectangle(150, gy, 780, 3); ctx.fill()
        g = cairo.LinearGradient(0, gy - 200, 0, gy); g.add_color_stop_rgba(0, *OLIVE, 0); g.add_color_stop_rgba(1, *OLIVE, 0.16)
        ctx.set_source(g); ctx.rectangle(150, gy - 200, 780, 200); ctx.fill()
        fall = ein(seg(t, FALL, FALL + 0.55))
        bounce = 0.04 * math.sin(math.pi * seg(t, FALL + 0.55, FALL + 0.8)) if t > FALL + 0.55 else 0
        tx = 470
        ctx.save(); ctx.translate(tx, gy); ctx.rotate(-1.42 * fall + bounce)
        hit = max([math.exp(-(t - c) * 14) if t >= c else 0 for c in CHOPS])
        ctx.translate(3 * hit * math.sin(t * 90), 0)
        dmg = seg(t, CHOPS[0], FALL + 0.5)
        fg = (lerp(HL[0], 0.42, dmg), lerp(HL[1], 0.36, dmg), lerp(HL[2], 0.22, dmg), 1)
        draw_icon(ctx, icon_tree, 0, -45 * 3.5, 350, fg)
        ctx.restore()
        # stump + notch
        if dmg > 0:
            ctx.set_source_rgba(*CUT, 1); ctx.move_to(tx + 26, gy - 34); ctx.line_to(tx + 4, gy - 24); ctx.line_to(tx + 26, gy - 16); ctx.fill()
        if t > FALL + 0.5:
            ctx.set_source_rgba(0.42, 0.36, 0.22, 1); ctx.rectangle(tx - 24, gy - 30, 48, 30); ctx.fill()
        for c in CHOPS:
            burst(ctx, tx + 22, gy - 28, t - c, 0.9, n=9)
        if t > FALL + 0.5:
            for k in range(8):
                age = t - FALL - 0.5 - k * 0.02
                if 0 < age < 1.4:
                    px = tx - 120 - 330 * rnd(k, 5) * eout(min(1, age))
                    r = 30 + 90 * age
                    g = cairo.RadialGradient(px, gy - 20, 0, px, gy - 20, r)
                    g.add_color_stop_rgba(0, 0.45, 0.4, 0.3, 0.35 * (1 - age / 1.4)); g.add_color_stop_rgba(1, 0.3, 0.3, 0.3, 0)
                    ctx.set_source(g); ctx.arc(px, gy - 20, r, 0, 2 * math.pi); ctx.fill()
        # settler with axe
        aa = axe_angle(t)
        figure(ctx, 690, gy, 1.45, (0.88, 0.88, 0.86, 1), face=-1, lean=-0.06 + 0.05 * math.sin(aa),
               armF=(aa, 0.25), armB=(aa + 0.25, 0.3), legF=(0.28, -0.1), legB=(-0.22, 0.12), head="cap", hold="axe",
               rim=(3, 0, (*HL, 0.9)))
        ctx.pop_group_to_source(); ctx.paint_with_alpha(ha)
    # grid of trees / seedlings destroyed progressively
    for k, (x, y, seed) in enumerate(GRID2):
        ap = seg(t, 3.0 + 0.015 * k, 3.25 + 0.015 * k)
        if ap <= 0: continue
        d = seg(t, KILL2[k], KILL2[k] + 0.22)
        fn = icon_seedling if seed else icon_tree
        sz = 80 * (0.6 + 0.4 * eback(ap))
        if d <= 0:
            draw_icon(ctx, fn, x, y, sz, (*HL, ap))
        else:
            col = (lerp(HL[0], 0.30, d), lerp(HL[1], 0.27, d), lerp(HL[2], 0.22, d), ap)
            draw_icon(ctx, fn, x + 10 * d, y + 12 * d, sz, col, rot=(0.9 if k % 2 else -0.9) * eout(d))
            q = seg(t, KILL2[k], KILL2[k] + 0.18)
            if q < 1:
                ctx.set_source_rgba(1, 0.9, 0.7, 1 - q); ctx.set_line_width(4)
                ctx.move_to(x + 40, y - 40); ctx.line_to(lerp(x + 40, x - 40, eout(q * 1.5 if q < 0.66 else 1)), lerp(y - 40, y + 40, eout(min(1, q * 1.5)))); ctx.stroke()
            burst(ctx, x, y, t - KILL2[k], 0.45, n=6)
            ctx.set_source_rgba(*OLIVE, 0.9 * d); ctx.set_line_width(3)
            ctx.move_to(x - 30, y - 30); ctx.line_to(x + 30, y + 30); ctx.move_to(x + 30, y - 30); ctx.line_to(x - 30, y + 30); ctx.stroke()
    ga = seg(t, 3.0, 3.4)
    corner_frame(ctx, 540 - 3 * 140 - 10, 1355 - 56, 6 * 140 + 20, 2 * 92 + 112, 0.6 * ga)

# ================================================================ SCENE 3: 25,000 kg of crops
CTR3 = (540, 1200)
def count25k(t): return int(round(25000 * eout(seg(t, 7.40, 8.62)) / 50) * 50)
SACKS = [k for k in range(len(SPOTS))]

def draw_s3(ctx, t):
    v = camera(t)
    # badges: steal / destroy
    for (bx, by, t0, lbl, kind) in ((875, 520, 5.75, "سرقة", "thief"), (205, 520, 6.70, "إتلاف", "crops")):
        p = seg(t, t0, t0 + 0.4)
        if p <= 0: continue
        sc = eback(p)
        # connector to nearest hotspots
        lp = eout(seg(t, t0 + 0.1, t0 + 0.6))
        tgt = [SPOTS[i] for i in ((1, 6, 9) if kind == "thief" else (4, 10, 16))]
        for j, sp in enumerate(tgt):
            sx, sy = v.s(sp)
            ctx.set_source_rgba(*HL, 0.55); ctx.set_line_width(1.6)
            ctx.move_to(bx, by); ctx.line_to(lerp(bx, sx, lp), lerp(by, sy, lp)); ctx.stroke()
        ctx.save(); ctx.translate(bx, by); ctx.scale(sc, sc)
        ctx.set_source_rgba(0.085, 0.085, 0.085, 0.95); ctx.arc(0, 0, 92, 0, 2 * math.pi); ctx.fill()
        glow_disc(ctx, 0, 0, 92, 0.25)
        ctx.set_source_rgba(*HL, 1); ctx.set_line_width(2.5); ctx.arc(0, 0, 92, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eout(p)); ctx.stroke()
        ctx.save(); ctx.rotate(t * 0.5); ctx.set_dash([10, 8]); ctx.set_source_rgba(*OLIVE, 0.8); ctx.set_line_width(2)
        ctx.arc(0, 0, 104, 0, 2 * math.pi); ctx.stroke(); ctx.set_dash([]); ctx.restore()
        if kind == "thief":
            walk = math.sin(t * 7)
            figure(ctx, 6, 66, 0.66, (*HL, 1), face=-1, lean=0.12, armF=(-2.7, 0.2), armB=(0.3 * walk, 0.3),
                   legF=(0.35 * walk, -0.1), legB=(-0.35 * walk, 0.15), head="cap", back="sack")
        else:
            draw_icon(ctx, icon_crate, 0, 8, 105, (*HL, 1))
            dd = seg(t, t0 + 0.3, t0 + 0.7)
            ctx.set_source_rgba(*CUT, 1); ctx.set_line_width(4)
            ctx.move_to(-6, -40); ctx.line_to(4 * dd, -20); ctx.line_to(-6 * dd, 0); ctx.line_to(6 * dd, 24 * dd); ctx.stroke()
            flames(ctx, 26, 0, 30, 0.35 * dd, t, 41, n=10, height=100)
        ctx.restore()
        draw_text(ctx, lbl, "bold", 50, bx, by + 140, alpha=seg(t, t0 + 0.1, t0 + 0.3), wipe=eout(seg(t, t0 + 0.1, t0 + 0.5)))
    # sacks flowing from hotspots to the counter
    for k in SACKS:
        t0 = 7.2 + 0.08 * k
        u = seg(t, t0, t0 + 0.9)
        if u <= 0 or u >= 1: continue
        sx, sy = v.s(SPOTS[k])
        ex, ey = CTR3
        cx_, cy_ = lerp(sx, ex, 0.5) + (sx - ex) * 0.35, lerp(sy, ey, 0.5)
        uu = eio(u)
        px = (1 - uu) ** 2 * sx + 2 * (1 - uu) * uu * cx_ + uu * uu * ex
        py = (1 - uu) ** 2 * sy + 2 * (1 - uu) * uu * cy_ + uu * uu * ey
        ctx.set_source_rgba(*HL, 0.35 * (1 - u)); ctx.set_line_width(1.5)
        ctx.move_to(sx, sy); ctx.curve_to(sx, sy, cx_, cy_, px, py); ctx.stroke()
        draw_icon(ctx, icon_sack if k % 2 else icon_crate, px, py, 44 * (1 - 0.4 * u), (*HL, 1 - 0.6 * ein(u)))
    # counter
    pa = seg(t, 7.05, 7.3)
    if pa > 0:
        ctx.set_source_rgba(0.075, 0.075, 0.075, 0.9 * pa); ctx.rectangle(0, 1035, W, 590); ctx.fill()
        q = eout(pa)
        ctx.set_source_rgba(*HL, pa); ctx.rectangle(W - W * q, 1035, W * q, 3); ctx.fill()
        ctx.set_source_rgba(*OLIVE, pa); ctx.rectangle(0, 1622, W * q, 2); ctx.fill()
        draw_text(ctx, "قرابة", "medium", 58, 540, 1090, alpha=seg(t, 7.12, 7.3), wipe=eout(seg(t, 7.12, 7.45)))
        if t >= 7.38:
            a = seg(t, 7.38, 7.5)
            counter_text(ctx, count25k(t), 190, 540, 1200, a, scale=1 + 0.2 * (1 - eout(seg(t, 7.38, 7.7))) + bump(t, [8.62], 0.3, 0.06))
        draw_text(ctx, "كيلوغرام", "bold", 66, 540, 1318, alpha=seg(t, 8.64, 8.8), wipe=eout(seg(t, 8.64, 9.1)))
        draw_text(ctx, "من المحاصيل الزراعية", "medium", 52, 540, 1402, alpha=seg(t, 9.3, 9.5), wipe=eout(seg(t, 9.3, 10.6)))
    # crop icons
    crops = (icon_olive, icon_wheat, icon_crate, icon_grapes)
    for j, fn in enumerate(crops):
        t0 = 9.45 + 0.28 * j
        p = seg(t, t0, t0 + 0.35)
        if p <= 0: continue
        x = 540 + (1.5 - j) * 170; y = 1530
        ctx.set_source_rgba(0.085, 0.085, 0.085, 0.9 * p); ctx.arc(x, y, 58 * eback(p), 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*OLIVE, p); ctx.set_line_width(2); ctx.arc(x, y, 58 * eback(p), 0, 2 * math.pi); ctx.stroke()
        draw_icon(ctx, fn, x, y + 4 * math.sin(t * 2 + j), 74 * eback(p), (*HL, p))

# ================================================================ village scenes (window / hologram)
def village_bg(ctx, t, WW, HH, gy, fire_x, glow=1.0):
    g = cairo.LinearGradient(0, 0, 0, gy)
    g.add_color_stop_rgb(0, 0.07, 0.065, 0.06); g.add_color_stop_rgb(1, 0.24, 0.15, 0.08)
    ctx.set_source(g); ctx.rectangle(0, 0, WW, gy); ctx.fill()
    f = flick(t, 3) * glow
    g = cairo.RadialGradient(fire_x, gy - 60, 0, fire_x, gy - 60, 520)
    g.add_color_stop_rgba(0, 1, 0.55, 0.15, 0.45 * f); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
    ctx.set_source(g); ctx.rectangle(0, 0, WW, HH); ctx.fill()
    # far hills with houses
    ctx.set_source_rgb(0.12, 0.10, 0.085)
    ctx.move_to(0, gy - 150)
    for x in range(0, WW + 21, 20):
        ctx.line_to(x, gy - 150 - 45 * math.sin(x * 0.006 + 1) - 20 * math.sin(x * 0.017))
    ctx.line_to(WW, gy); ctx.line_to(0, gy); ctx.close_path(); ctx.fill()
    for k in range(14):
        hx = 30 + k * 72 + 20 * rnd(k, 1); hy = gy - 150 - 45 * math.sin(hx * 0.006 + 1) - 20 * math.sin(hx * 0.017)
        hw, hh = 40 + 20 * rnd(k, 2), 30 + 26 * rnd(k, 3)
        ctx.set_source_rgb(0.09, 0.08, 0.07); ctx.rectangle(hx, hy - hh + 8, hw, hh + 20); ctx.fill()
        if rnd(k, 4) > 0.4:
            ctx.set_source_rgba(*HL, 0.35); ctx.rectangle(hx + 8, hy - hh + 18, 7, 9); ctx.fill()
    # near hill olive trees
    ctx.set_source_rgb(0.085, 0.075, 0.065)
    ctx.move_to(0, gy - 50)
    for x in range(0, WW + 21, 20):
        ctx.line_to(x, gy - 50 - 18 * math.sin(x * 0.01 + 2))
    ctx.line_to(WW, gy); ctx.line_to(0, gy); ctx.close_path(); ctx.fill()
    ctx.set_source_rgb(0.12, 0.11, 0.08); ctx.rectangle(0, gy, WW, HH - gy); ctx.fill()
    g = cairo.RadialGradient(fire_x, gy + 20, 0, fire_x, gy + 20, 420)
    g.add_color_stop_rgba(0, 1, 0.55, 0.2, 0.35 * f); g.add_color_stop_rgba(1, 1, 0.5, 0.2, 0)
    ctx.set_source(g); ctx.rectangle(0, gy, WW, HH - gy); ctx.fill()
    ctx.set_source_rgba(0.2, 0.18, 0.14, 1); ctx.rectangle(0, gy + 60, WW, 8); ctx.fill()

def window_scene(ctx, t):
    """settlers torch a car and attack farmers among olive trees (illustrative)"""
    WW, HH, gy = 1000, 750, 560
    village_bg(ctx, t, WW, HH, gy, 470)
    smoke_column(ctx, 470, gy - 90, t, 7, n=16, size=0.9, alpha=0.55, drift=120, rise=700)
    for x, s in ((30, 1.9), (300, 1.3), (960, 1.7)):
        draw_icon(ctx, icon_tree, x, gy - 45 * s, 100 * s, (0.07, 0.07, 0.055, 1), cut=(0.07, 0.07, 0.055))
    # burning car
    ctx.save(); ctx.translate(470, gy - 40); ctx.scale(2.6, 2.6)
    icon_car(ctx, (0.06, 0.055, 0.05, 1), cut=(0.6, 0.3, 0.1))
    ctx.restore()
    flames(ctx, 470, gy - 70, 210, 1.2, t, 11, n=44, height=220)
    flames(ctx, 430, gy - 20, 120, 0.6, t, 12, n=18, height=120)
    embers(ctx, 470, gy - 120, 300, t, 13, n=30, height=500)
    rim = (-3, 0, (1, 0.6, 0.25, 0.85))
    dark = (0.035, 0.035, 0.035, 1)
    # settlers (right), facing left
    sw = math.sin(t * 6.0)
    figure(ctx, 760, gy + 40, 1.15, dark, face=-1, lean=-0.05, armF=(-2.3 + 1.2 * max(0, sw), 0.3), armB=(0.4, 0.4),
           legF=(0.3, -0.1), legB=(-0.25, 0.15), head="cap", hold="stick", rim=rim)
    figure(ctx, 860, gy + 46, 1.05, dark, face=-1, armF=(-2.9, 0.1), armB=(0.2, 0.5), legF=(0.15, 0), legB=(-0.12, 0.05),
           head="cap", hold="torch", rim=rim)
    info = figure(ctx, 860, gy + 46, 1.05, dark, face=-1, armF=(-2.9, 0.1), armB=(0.2, 0.5), legF=(0.15, 0), legB=(-0.12, 0.05),
                  head="cap", hold="torch")
    tx, ty = tip_point(info, 44)
    flames(ctx, tx, ty + 6, 14, 0.25, t, 51, n=10, height=80)
    figure(ctx, 640, gy + 52, 1.2, dark, face=-1, lean=-0.1, armF=(-1.4, -0.2), armB=(-1.2, 0.2), legF=(0.4, -0.15), legB=(-0.3, 0.2),
           head="cap", hold="rifle", hold_ang=-1.55, rim=rim)
    # farmers (left): one recoiling, one on the ground
    rec = 0.15 * math.sin(t * 3.0)
    figure(ctx, 110, gy + 50, 1.12, dark, face=1, lean=-0.22 + rec, armF=(-2.6, -0.4), armB=(-2.3, 0.2), legF=(0.35, -0.1), legB=(-0.3, 0.2),
           head="scarf", rim=(3, 0, (1, 0.6, 0.25, 0.7)))
    ctx.save(); ctx.translate(195, gy + 70); ctx.rotate(1.45)
    figure(ctx, 0, 0, 0.82, dark, face=1, armF=(-2.0, 0.4), armB=(-1.4, 0.6), legF=(0.2, 0), legB=(-0.1, 0.1), head="scarf")
    ctx.restore()
    # spilled olive basket
    ctx.set_source_rgba(0.06, 0.05, 0.04, 1); ctx.save(); ctx.translate(40, gy + 78); ctx.rotate(0.6)
    ctx.rectangle(-22, -16, 44, 30); ctx.fill(); ctx.restore()
    for k in range(9):
        ctx.set_source_rgba(0.35, 0.4, 0.15, 1); ctx.arc(62 + k * 9, gy + 88 + 4 * rnd(k, 2), 3.5, 0, 2 * math.pi); ctx.fill()

def holo_scene(ctx, t):
    """occupation army and settlers: patrol jeep, soldiers firing, a house set alight (illustrative)"""
    WW, HH, gy = 1000, 667, 500
    village_bg(ctx, t, WW, HH, gy, 820, glow=0.8)
    # burning house
    ctx.save(); ctx.translate(820, gy - 70); ctx.scale(1.6, 1.6); icon_house(ctx, (0.06, 0.06, 0.05, 1), cut=(0.9, 0.45, 0.1)); ctx.restore()
    smoke_column(ctx, 820, gy - 120, t, 9, n=12, size=0.8, alpha=0.5, drift=-80, rise=600)
    flames(ctx, 830, gy - 120, 120, 1.0, t, 61, n=30, height=180)
    embers(ctx, 820, gy - 150, 200, t, 62, n=20, height=400)
    # military jeep
    ctx.save(); ctx.translate(250, gy - 34); ctx.scale(2.5, 2.5)
    ctx.set_source_rgba(0.05, 0.05, 0.045, 1)
    ctx.move_to(-48, 22); ctx.line_to(-48, -2); ctx.line_to(-30, -4); ctx.line_to(-20, -26); ctx.line_to(30, -26); ctx.line_to(30, -4)
    ctx.line_to(48, -2); ctx.line_to(48, 22); ctx.close_path(); ctx.fill()
    ctx.rectangle(-10, -40, 4, 16); ctx.fill(); ctx.set_line_width(1); ctx.move_to(24, -26); ctx.line_to(30, -60); ctx.stroke()
    ctx.set_source_rgba(0.3, 0.25, 0.15, 1); ctx.rectangle(-16, -21, 18, 12); ctx.rectangle(6, -21, 18, 12); ctx.fill()
    ctx.set_source_rgba(0.02, 0.02, 0.02, 1)
    for wx in (-28, 28): ctx.arc(wx, 22, 12, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    dark = (0.035, 0.035, 0.035, 1); rim = (3, 0, (1, 0.7, 0.35, 0.8))
    for k, (x, s) in enumerate(((420, 1.1), (520, 1.05), (610, 1.12))):
        info = figure(ctx, x, gy + 40 + 6 * k, s, dark, face=1, lean=0.05, armF=(-1.45, -0.1), armB=(-1.1, -0.5),
                      legF=(0.32, -0.1), legB=(-0.28, 0.15), head="helmet", hold="rifle", hold_ang=-1.57 + 0.04, rim=rim)
        fx, fy = tip_point(info, 84)
        ph = (t * 2.2 + k * 0.37) % 1.0
        if ph < 0.12:
            a = 1 - ph / 0.12
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            glow_disc(ctx, fx + 10, fy, 40, 0.9 * a, (1, 0.8, 0.4))
            ctx.restore()
            ctx.set_source_rgba(1, 0.85, 0.5, 0.8 * a); ctx.set_line_width(2)
            ctx.move_to(fx + 20, fy); ctx.line_to(fx + 20 + 300 * (ph / 0.12), fy - 4); ctx.stroke()
    # settlers with torches near the house
    for k, x in enumerate((730, 930)):
        info = figure(ctx, x, gy + 50, 1.0, dark, face=-1 if k else 1, armF=(-2.8, 0.1), armB=(0.3, 0.4), legF=(0.2, 0), legB=(-0.15, 0.05),
                      head="cap", hold="torch", rim=(-3, 0, (1, 0.7, 0.35, 0.8)))
        tx, ty = tip_point(info, 44)
        flames(ctx, tx, ty + 6, 14, 0.25, t, 70 + k, n=10, height=80)

def render_world(fn, t, WW, HH, w, h, zoom=1.0, panx=0.0):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(surf)
    c.translate(w / 2, h / 2); s = w / WW * zoom; c.scale(s, s); c.translate(-WW / 2 + panx, -HH / 2)
    fn(c, t)
    surf.flush()
    return surf

_HOLO_ROWS = {}
def holo_treat(surf, t, alpha):
    w, h = surf.get_width(), surf.get_height()
    a = np.ndarray((h, surf.get_stride() // 4, 4), np.uint8, buffer=surf.get_data())[:, :w].astype(np.float32) / 255
    lum = a[..., 2] * 0.35 + a[..., 1] * 0.5 + a[..., 0] * 0.15
    lum = np.clip((lum - 0.03) * 2.0, 0, 1) ** 0.85
    if h not in _HOLO_ROWS:
        rows = np.arange(h)
        _HOLO_ROWS[h] = (0.72 + 0.28 * ((rows % 4) < 2)).astype(np.float32)[:, None]
    scan = _HOLO_ROWS[h]
    band = ((np.arange(h) - (t * 260) % (h + 200) + 100) / 60.0)
    band = np.exp(-band ** 2)[:, None].astype(np.float32)
    fl = 0.9 + 0.1 * math.sin(t * 37) * math.sin(t * 11)
    edge = np.minimum(1, np.minimum(np.arange(h) / 30, (h - np.arange(h)) / 80))[:, None].astype(np.float32)
    al = np.clip(0.10 + lum * 0.85 + band * 0.18, 0, 1) * scan * fl * edge * alpha
    r = np.clip(HL[0] * (0.22 + lum * 1.0) + lum ** 3 * 0.3 + band * 0.2, 0, 1)
    g_ = np.clip(HL[1] * (0.22 + lum * 1.0) + lum ** 3 * 0.3 + band * 0.16, 0, 1)
    b = np.clip(HL[2] * (0.22 + lum * 1.0) + lum ** 3 * 0.25 + band * 0.1, 0, 1)
    out = np.dstack([b * al, g_ * al, r * al, al])
    # horizontal glitch bands
    gi = int(t * FPS)
    if rnd(gi, 3) > 0.82:
        y0 = int(rnd(gi, 4) * (h - 30)); hh = 6 + int(rnd(gi, 5) * 20); dx = int((rnd(gi, 6) - 0.5) * 40)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], dx, axis=1)
    o = (out * 255).astype(np.uint8)
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = o.reshape(h, w * 4)
    return cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)

# ================================================================ SCENE 4: window + hundreds of injuries + last month
WX, WY, WWd, WHt = 100, 300, 880, 660
GRID4 = [(540 + (4.5 - c) * 86, 1218 + r * 88) for r in range(3) for c in range(10)]
CAL_T0, CAL_T1 = 16.4, 17.75

def draw_s4(ctx, t):
    op = eout(seg(t, 11.85, 12.3))
    cl = eio(seg(t, 17.65, 18.0))
    hgt = WHt * op * (1 - cl) + 3
    cy = WY + WHt / 2
    y0 = cy - hgt / 2
    if op > 0 and hgt > 4:
        # content
        p = seg(t, 11.85, 17.9)
        surf = render_world(window_scene, t, 1000, 750, WWd, WHt, zoom=1.0 + 0.10 * eio(p), panx=lerp(40, -60, eio(p)))
        ctx.save(); ctx.rectangle(WX, y0, WWd, hgt); ctx.clip()
        ctx.set_source_surface(surf, WX, WY); ctx.paint()
        # light scanlines + scanning bar
        ctx.set_source_rgba(0, 0, 0, 0.12)
        for yy in range(int(y0), int(y0 + hgt), 4): ctx.rectangle(WX, yy, WWd, 1.5)
        ctx.fill()
        sy = WY + (t * 180) % WHt
        g = cairo.LinearGradient(0, sy - 40, 0, sy)
        g.add_color_stop_rgba(0, *HL, 0); g.add_color_stop_rgba(1, *HL, 0.12)
        ctx.set_source(g); ctx.rectangle(WX, sy - 40, WWd, 40); ctx.fill()
        ctx.restore()
        ctx.set_source_rgba(*OLIVE, 1); ctx.set_line_width(2); ctx.rectangle(WX, y0, WWd, hgt); ctx.stroke()
        corner_frame(ctx, WX - 12, y0 - 12, WWd + 24, hgt + 24, 1.0, L=44, lw=4)
        # tick marks along the frame
        ctx.set_source_rgba(*HL, 0.6 * op)
        for k in range(1, 12):
            xx = WX + k * WWd / 12; ctx.rectangle(xx, y0 - 4, 1.5, 8); ctx.rectangle(xx, y0 + hgt - 4, 1.5, 8)
        ctx.fill()
    # settlers badge on the window edge
    ba = seg(t, 14.28, 14.55) * (1 - seg(t, 17.55, 17.75))
    if ba > 0:
        bw = 560; bx = 540 - bw / 2; by = WY + WHt - 30
        ctx.save(); ctx.translate(540, by + 30); ctx.scale(1, eout(ba)); ctx.translate(-540, -(by + 30))
        ctx.set_source_rgba(0.07, 0.07, 0.07, 0.95); ctx.rectangle(bx, by, bw, 64); ctx.fill()
        ctx.set_source_rgba(*HL, 1); ctx.rectangle(bx + bw - 70, by, 70, 64); ctx.fill()
        ctx.restore()
        draw_icon(ctx, icon_settler, bx + bw - 35, by + 32, 54 * eout(ba), (*DARK, 1), cut=HL)
        draw_text(ctx, "اعتداءات المستوطنين", "bold", 42, bx + bw - 90, by + 31, "right", alpha=ba, wipe=eout(seg(t, 14.3, 15.4)))
    # "hundreds of injuries"
    out = 1 - seg(t, 17.6, 17.95)
    a1 = seg(t, 12.15, 12.3) * out
    if a1 > 0:
        w1 = text_w("مئات", "heavy", 140); w2 = text_w("الإصابات", "bold", 84); gap = 30
        tot = w1 + gap + w2; xr = 540 + tot / 2
        draw_text(ctx, "مئات", "heavy", 140, xr, 1082, "right", alpha=a1, color=HL8,
                  scale=1 + 0.2 * (1 - eout(seg(t, 12.15, 12.45))))
        draw_text(ctx, "الإصابات", "bold", 84, xr - w1 - gap, 1094, "right", alpha=seg(t, 12.6, 12.75) * out, wipe=eout(seg(t, 12.6, 13.1)))
    for k, (x, y) in enumerate(GRID4):
        t0 = 12.62 + 1.5 * (k / 30) ** 1.2
        p = seg(t, t0, t0 + 0.2)
        if p <= 0: continue
        draw_icon(ctx, icon_injured, x, y, 68 * eback(p), (*HL, out), cut=CUT)
        if p < 1:
            ctx.set_source_rgba(1, 0.9, 0.7, 0.8 * (1 - p)); ctx.set_line_width(2); ctx.arc(x, y, 20 + 30 * p, 0, 2 * math.pi); ctx.stroke()
    ga = seg(t, 12.6, 12.9) * out
    corner_frame(ctx, GRID4[9][0] - 55, 1168, 10 * 86 + 24, 3 * 88 + 12, 0.6 * ga)
    # last month: calendar fills day by day
    ca = seg(t, 16.3, 16.55) * out
    if ca > 0:
        fill_n = int(30 * seg(t, CAL_T0, CAL_T1))
        cx_ = 870; cy_ = 1535
        glow_disc(ctx, cx_, cy_, 120, 0.25 * ca)
        draw_icon(ctx, icon_calendar, cx_, cy_, 140 * eback(seg(t, 16.3, 16.65)), (*HL, ca), fill_n=fill_n)
        draw_text(ctx, "خلال الشهر الماضي وحده", "bold", 58, 762, 1545, "right", alpha=ca, wipe=eout(seg(t, 16.35, 17.85)))

# ================================================================ SCENE 5: hologram, 3,400 attacks, categories
def count3400(t): return int(round(3400 * eout(seg(t, 19.25, 21.0)) / 10) * 10)
CATS = [("إحراق", "fire", 24.90), ("تخريب", "vandal", 25.38), ("سرقة الممتلكات", "theft", 26.00),
        ("المحاصيل", "crops", 27.95), ("إطلاق النار", "gun", 29.76), ("الضرب", "fist", 31.20)]
CW5, CH5 = 400, 230

def holo_layout(t):
    p = eio(seg(t, 24.4, 25.0))
    return dict(s=lerp(0.88, 0.47, p), cy=lerp(575, 445, p), p=p)

def draw_holo(ctx, t):
    on = seg(t, 18.0, 18.6)
    if on <= 0: return
    L = holo_layout(t)
    s = L["s"]
    ctx.save(); ctx.translate(540, L["cy"]); ctx.scale(s, s)
    hw, hh = 900, 600
    by = hh / 2 + 70  # projector base
    # base
    glow_disc(ctx, 0, by, 300, 0.5 * on, HL)
    ctx.save(); ctx.translate(0, by); ctx.scale(1, 0.18)
    ctx.set_source_rgba(0.06, 0.06, 0.06, on); ctx.arc(0, 0, 230, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*HL, on); ctx.set_line_width(5); ctx.arc(0, 0, 230, 0, 2 * math.pi); ctx.stroke()
    ctx.set_source_rgba(*OLIVE, on); ctx.set_line_width(3); ctx.arc(0, 0, 180, 0, 2 * math.pi); ctx.stroke()
    ctx.set_source_rgba(1, 0.9, 0.7, on * flick(t, 5)); ctx.arc(0, 0, 60, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # beam
    rise = eout(seg(t, 18.05, 18.55))
    top = by - (by + hh / 2) * rise
    g = cairo.LinearGradient(0, by, 0, top)
    g.add_color_stop_rgba(0, *HL, 0.35 * on); g.add_color_stop_rgba(1, *HL, 0.03 * on)
    ctx.set_source(g); ctx.move_to(-200, by); ctx.line_to(200, by); ctx.line_to(hw / 2, top + 20); ctx.line_to(-hw / 2, top + 20); ctx.close_path(); ctx.fill()
    # projected window
    ap = seg(t, 18.3, 18.7)
    if ap > 0:
        flk = 1.0 if ap >= 1 else (0.4 + 0.6 * (rnd(int(t * FPS), 8) > 0.35)) * ap
        p = seg(t, 18.3, 31.8)
        surf = render_world(holo_scene, t, 1000, 667, hw, hh, zoom=1.0 + 0.08 * eio(p), panx=lerp(-30, 40, eio(p)))
        hs = holo_treat(surf, t, flk)
        yy = -hh / 2
        ctx.save(); ctx.translate(-hw / 2, yy)
        ctx.set_source_surface(hs, 0, 0); ctx.paint()
        ctx.set_source_rgba(*HL, 0.8 * flk); ctx.set_line_width(2); ctx.rectangle(0, 0, hw, hh); ctx.stroke()
        corner_frame(ctx, -14, -14, hw + 28, hh + 28, flk, L=46, lw=4)
        ctx.restore()
    ctx.restore()

def actor_badge(ctx, x, y, t0, t, fn, lbl, sc_=1.0, alpha=1.0):
    p = seg(t, t0, t0 + 0.4)
    if p <= 0 or alpha <= 0: return
    s = eback(p) * sc_
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    ctx.push_group()
    ctx.set_source_rgba(0.085, 0.085, 0.085, 0.95); ctx.arc(0, 0, 86, 0, 2 * math.pi); ctx.fill()
    glow_disc(ctx, 0, 0, 86, 0.3)
    ctx.set_source_rgba(*HL, 1); ctx.set_line_width(2.5); ctx.arc(0, 0, 86, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eout(p)); ctx.stroke()
    pulse_rings(ctx, 0, 0, 90, t, 0.6, n=1, spread=40, speed=0.7)
    draw_icon(ctx, fn, 0, 4, 118, (*HL, 1))
    draw_text(ctx, lbl, "bold", 50, 0, 136, alpha=seg(t, t0 + 0.1, t0 + 0.3), wipe=eout(seg(t, t0 + 0.05, t0 + 0.6)))
    ctx.pop_group_to_source(); ctx.paint_with_alpha(alpha)
    ctx.restore()

def card_pos(j):
    r, c = divmod(j, 2)
    return (540 + 215 if c == 0 else 540 - 215), 905 + r * 270

def draw_cat_icon(ctx, kind, t, t0, x, y, sz):
    age = t - t0
    if kind == "fire":
        ctx.save(); ctx.translate(x, y); ctx.scale(sz / 100, sz / 100)
        icon_car(ctx, (*HL, 1)); ctx.restore()
        flames(ctx, x, y - sz * 0.05, sz * 0.7, 0.75, t, 81, n=24, height=sz * 1.3)
    elif kind == "vandal":
        sh = math.exp(-max(0, age) * 6) * 6 if age > 0 else 0
        draw_icon(ctx, icon_vandal, x + sh * math.sin(t * 80), y, sz, (*HL, 1))
        burst(ctx, x, y - 10, age - 0.1, 0.6, n=8)
    elif kind == "theft":
        draw_icon(ctx, icon_theft, x, y, sz, (*HL, 1))
    elif kind == "crops":
        draw_icon(ctx, icon_wheat, x - sz * 0.22, y + 6, sz * 0.9, (*HL, 1))
        draw_icon(ctx, icon_crate, x + sz * 0.26, y + 10, sz * 0.7, (*HL, 1))
    elif kind == "gun":
        draw_icon(ctx, icon_gun, x, y, sz, (*HL, 1))
        ph = (max(0, age) * 3.0) % 1.0
        if age > 0 and ph < 0.15:
            a = 1 - ph / 0.15
            mx = x - sz * 0.5
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); glow_disc(ctx, mx - 14, y - sz * 0.03, 40, a, (1, 0.8, 0.4)); ctx.restore()
            ctx.set_source_rgba(1, 0.9, 0.6, a); ctx.set_line_width(3)
            for k in range(3):
                ctx.move_to(mx - 20, y - 3 + (k - 1) * 8); ctx.line_to(mx - 20 - 60 * (ph / 0.15 + 0.3), y - 3 + (k - 1) * 16); ctx.stroke()
    elif kind == "fist":
        pun = math.sin(math.pi * clamp((age % 0.8) / 0.25)) if age > 0 else 0
        draw_icon(ctx, icon_fist, x - 14 * pun, y, sz * (1 + 0.08 * pun), (*HL, 1))
        if pun > 0.6:
            ctx.set_source_rgba(1, 0.9, 0.6, pun); ctx.set_line_width(3)
            for k in range(5):
                ang = math.pi * (0.7 + 0.15 * k)
                ctx.move_to(x - sz * 0.55 + math.cos(ang) * 12, y + math.sin(ang) * 12)
                ctx.line_to(x - sz * 0.55 + math.cos(ang) * 34, y + math.sin(ang) * 34); ctx.stroke()

def draw_s5(ctx, t):
    draw_holo(ctx, t)
    L = holo_layout(t)
    p = L["p"]
    # counter group
    ny = lerp(1112, 712, p); ns = lerp(1.0, 0.62, p)
    draw_text(ctx, "قرابة", "medium", 62, 540, lerp(985, 600, p) if p < 1 else 0, alpha=seg(t, 18.3, 18.5) * (1 - seg(t, 24.3, 24.6)),
              wipe=eout(seg(t, 18.3, 18.75)))
    if t >= 19.2:
        a = seg(t, 19.2, 19.35)
        dark_disc(ctx, 540, ny, 360 * ns, 0.45 * a)
        counter_text(ctx, count3400(t), 230, 540 - 120 * p, ny, a, scale=ns * (1 + 0.2 * (1 - eout(seg(t, 19.2, 19.5))) + bump(t, [21.0], 0.3, 0.06)))
    if t >= 20.98:
        if p < 1:
            draw_text(ctx, "اعتداء", "bold", 84, lerp(540, 790, p), lerp(1252, 712, p), alpha=seg(t, 20.98, 21.15),
                      scale=lerp(1, 0.85, p), wipe=eout(seg(t, 20.98, 21.4)))
        else:
            draw_text(ctx, "اعتداء", "bold", 84, 790, 712, scale=0.85)
    # actors
    aout = 1 - seg(t, 24.3, 24.65)
    for x, t0, fn, lbl in ((790, 22.25, icon_soldier, "جيش الاحتلال"), (290, 23.45, icon_settler, "المستوطنين")):
        cp = seg(t, t0 - 0.2, t0 + 0.2)
        if cp > 0 and aout > 0:
            ctx.set_source_rgba(*HL, 0.7 * aout); ctx.set_line_width(2)
            sx, sy = 540, 1300
            ctx.move_to(sx, sy); ctx.line_to(lerp(sx, x, eout(cp)), lerp(sy, 1430, eout(cp))); ctx.stroke()
            ctx.arc(sx, sy, 5, 0, 2 * math.pi); ctx.fill()
        actor_badge(ctx, x, 1440, t0, t, fn, lbl, alpha=aout)
    # categories
    for j, (lbl, kind, t0) in enumerate(CATS):
        q = seg(t, t0 - 0.12, t0 + 0.3)
        if q <= 0: continue
        x, y = card_pos(j)
        cur = (t0 - 0.1 <= t < (CATS[j + 1][2] - 0.1 if j + 1 < len(CATS) else 99))
        ctx.save(); ctx.translate(x, y); ctx.scale(eback(q), eback(q))
        panel(ctx, -CW5 / 2, -CH5 / 2, CW5, CH5, min(1, q * 1.5), glow=1.0 if cur else 0.3)
        if cur:
            ctx.set_source_rgba(*HL, 0.9); ctx.rectangle(CW5 / 2 - 6, -CH5 / 2, 6, CH5); ctx.fill()
        draw_cat_icon(ctx, kind, t, t0, 0, -24, 112)
        draw_text(ctx, lbl, "bold", 48, 0, 72, alpha=seg(t, t0, t0 + 0.2), wipe=eout(seg(t, t0, t0 + 0.45)))
        ctx.restore()
        # connector from counter
        cp = seg(t, t0 - 0.25, t0)
        if cp > 0:
            sx, sy = 540, 766
            ex, ey = x, y - CH5 / 2 - 8
            ctx.set_source_rgba(*HL, 0.35); ctx.set_line_width(1.5)
            ctx.move_to(sx, sy); ctx.line_to(sx, lerp(sy, 774, eout(cp))); ctx.line_to(lerp(sx, ex, eout(cp)), lerp(sy, 774, eout(cp)))
            if cp >= 1: ctx.line_to(ex, ey)
            ctx.stroke()

# ================================================================ background, compositing
def draw_bg(ctx, t):
    g = cairo.RadialGradient(W / 2, H * 0.45, 100, W / 2, H * 0.45, 1300)
    g.add_color_stop_rgb(0, 0.135, 0.135, 0.135); g.add_color_stop_rgb(1, *DARK)
    ctx.set_source(g); ctx.paint()
    off = (t * 8) % 60
    ctx.set_source_rgba(*HL, 0.06)
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

def drift(t): return 4 * math.sin(t * 0.7), 5 * math.sin(t * 0.53 + 1)

yy_, xx_ = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2)
VIG = np.clip(1.0 - 0.40 * np.clip(_d - 0.5, 0, None) ** 1.6, 0.45, 1.0).astype(np.float32)[..., None]
del yy_, xx_, _d
_rng = np.random.default_rng(7)
GRAIN = [_rng.normal(0, 2.2, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]

def surf_array(surf): return np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())

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
    if t < 12.0:
        draw_map(ctx, t)
    # scene 2
    if 2.6 <= t < 5.9:
        op = eio(seg(t, 5.2, 5.75))
        group(ctx, draw_s2, t, 1 - op, scale=1 - 0.12 * op, cx=540, cy=900)
    # scene 3
    if 5.4 <= t < 12.0:
        ip = eout(seg(t, 5.5, 6.0)); op = ein(seg(t, 11.2, 11.75))
        group(ctx, draw_s3, t, ip * (1 - op), scale=1 + 0.25 * op, cx=540, cy=600)
    # scene 4
    if 11.8 <= t < 18.1:
        group(ctx, draw_s4, t, 1.0)
    # scene 5
    if t >= 17.95:
        group(ctx, draw_s5, t, 1.0)
    # flashes on the big cuts
    for tf in (11.85, 17.98):
        fl = seg(t, tf - 0.08, tf) * (1 - seg(t, tf, tf + 0.4))
        if fl > 0:
            ctx.identity_matrix(); ctx.set_source_rgba(1, 0.85, 0.55, 0.3 * fl); ctx.paint()
    ctx.identity_matrix()
    surf.flush()
    bloom(surf)
    ha = 0.45 * seg(t, 0.2, 1.0) * (1 - seg(t, 31.7, 32.05))
    corner_frame(ctx, 34, 34, W - 68, H - 68, ha, L=50, lw=2)
    surf.flush()
    a = surf_array(surf)[..., :3].astype(np.float32)
    a *= VIG
    a *= seg(t, 0.0, 0.3) * (1 - seg(t, 31.75, 32.07))
    return np.clip(a, 0, 255).astype(np.uint8)[..., ::-1].tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        os.makedirs(f"{HERE}/stills", exist_ok=True)
        for ts in sys.argv[2:]:
            Image.frombytes("RGB", (W, H), render(int(round(float(ts) * FPS)))).save(f"{HERE}/stills/s_{float(ts):05.2f}.jpg", quality=88)
        print("stills ok")
    elif sys.argv[1] == "render":
        import subprocess
        from multiprocessing import Pool
        out = sys.argv[2]
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-preset", "slower", "-crf", "12", "-tune", "film", "-level", "5.1",
                               "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render, range(N), chunksize=2)):
                ff.stdin.write(fr)
                if k % 90 == 0: print("frame", k, flush=True)
        ff.stdin.close(); ff.wait()
        print("done")
