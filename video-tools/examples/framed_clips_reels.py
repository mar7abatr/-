import math, sys, glob, pickle
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 8.0
N = int(DUR * FPS)
WORK = "/tmp/w4"

def hexc(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
OLIVE = hexc("896829"); DARK = hexc("1D1D1D"); HL = hexc("C7973B"); HL8 = (0xC7, 0x97, 0x3B)

def clamp(v, a=0.0, b=1.0): return a if v < a else b if v > b else v
def seg(t, a, b): return clamp((t - a) / (b - a))
def eio(p): return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
def eout(p): return 1 - (1 - p) ** 3
def ein(p): return p ** 3
def eback(p, s=1.6):
    p -= 1
    return 1 + p * p * ((s + 1) * p + s)
def lerp(a, b, p): return a + (b - a) * p
def rnd(i, k=0):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)

# ---------------------------------------------------------------- timeline
T_SWITCH = 3.9          # cut point between the two hospitals (covered by the transition)
TR0, TR1 = 3.55, 4.3    # transition window
EXPLOSION = 0.6         # Baptist clip flash lands here
STRIKE2 = 5.47          # strike inside the Nasser clip (source 29.57 s)
STRIKES = (EXPLOSION, STRIKE2)
SCENES = [
    dict(key="ahli", name="المستشفى المعمداني", city="مدينة غزة", geo=(34.46158, 31.50472), t0=0.0, t1=T_SWITCH, off=0.0, focus=(0.56, 0.5)),
    dict(key="nasser", name="مجمع ناصر الطبي", city="خان يونس", geo=(34.29229, 31.34703), t0=T_SWITCH, t1=DUR, off=0.0, focus=(0.5, 0.52)),
]

# ---------------------------------------------------------------- text
FONTS = {"black": "/tmp/work/fonts/black.otf", "bold": "/tmp/work/fonts/bold.ttf", "medium": "/tmp/work/fonts/medium.otf"}
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

def text_surface(s, font, size, color=(255, 255, 255)):
    key = (s, font, size, color)
    if key in _tc: return _tc[key]
    f = ImageFont.truetype(FONTS[font], size, layout_engine=ImageFont.Layout.RAQM)
    bbox = f.getbbox(s, direction="rtl", language="ar")
    pad = 10
    w = bbox[2] - bbox[0] + pad * 2; h = bbox[3] - bbox[1] + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bbox[0], pad - bbox[1]), s, font=f, fill=color + (255,), direction="rtl", language="ar")
    r = (pil_to_surface(im), w, h, pad); _tc[key] = r
    return r

def text_w(s, font, size):
    _, w, h, pad = text_surface(s, font, size); return w - 2 * pad

def draw_text(ctx, s, font, size, x, y, alpha=1.0, color=(255, 255, 255), wipe=1.0, dy=0.0):
    """right-aligned at x, vertically centred at y; wipe reveals right-to-left"""
    if alpha <= 0 or wipe <= 0: return
    surf, w, h, pad = text_surface(s, font, size, color)
    x0 = x - w + pad
    ctx.save()
    if wipe < 1:
        ctx.rectangle(x0 + w * (1 - wipe), y - h / 2 - 20, w * wipe + 5, h + 40); ctx.clip()
    ctx.set_source_surface(surf, x0, y - h / 2 + dy); ctx.paint_with_alpha(alpha)
    ctx.restore()

# ---------------------------------------------------------------- media
CLIPS = {k: sorted(glob.glob(f"{WORK}/clips/{k}/*.jpg")) for k in ("ahli", "nasser")}
_mc = {}
def load(path):
    if path in _mc: return _mc[path]
    if len(_mc) > 10: _mc.pop(next(iter(_mc)))
    a = np.asarray(Image.open(path).convert("RGB"))
    h, w = a.shape[:2]
    bgra = np.dstack([a[..., 2], a[..., 1], a[..., 0], np.full((h, w), 255, np.uint8)])
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
    r = (cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride), w, h, path)
    _mc[path] = r
    return r

def clip_frame(sc, t):
    fr = CLIPS[sc["key"]]
    i = int(round((t - sc["t0"] + sc["off"]) * FPS))
    return load(fr[clamp(i, 0, len(fr) - 1)])

def scene_at(t):
    return SCENES[0] if t < T_SWITCH else SCENES[1]

# ---------------------------------------------------------------- locator (Gaza strip outline)
MAP = pickle.load(open("/tmp/work/geo/map.pkl", "rb"))
LAT0, LON0 = 31.42, 34.38
KX = math.cos(math.radians(LAT0)) * 111.32; KY = 110.57
def P(lon, lat): return ((lon - LON0) * KX, -(lat - LAT0) * KY)
INS_C = (150, 245); INS_S = 5.0     # inset centre (px) and px/km
STRIP_C = (1.2, 1.1)
def ins(p):
    return (INS_C[0] + (p[0] - STRIP_C[0]) * INS_S, INS_C[1] + (p[1] - STRIP_C[1]) * INS_S)
STRIP_PX = [[ins(p) for p in r[0]] for r in MAP["strip"]]
STRIP_LEN = [sum(math.dist(a, b) for a, b in zip(r, r[1:])) for r in STRIP_PX]
PIN = [ins(P(*sc["geo"])) for sc in SCENES]

def pin_pos(t):
    p = eio(seg(t, TR0 + 0.1, TR1 - 0.05))
    a, b = PIN
    # gentle arc while travelling south along the strip
    mx, my = (a[0] + b[0]) / 2 + 28, (a[1] + b[1]) / 2
    return ((1 - p) ** 2 * a[0] + 2 * (1 - p) * p * mx + p * p * b[0], (1 - p) ** 2 * a[1] + 2 * (1 - p) * p * my + p * p * b[1])

def draw_locator(ctx, t):
    a = seg(t, 0.15, 0.7) * (1 - seg(t, 7.55, 7.95))
    if a <= 0: return
    draw_p = eout(seg(t, 0.15, 1.0))
    # soft panel
    g = cairo.RadialGradient(INS_C[0], INS_C[1], 10, INS_C[0], INS_C[1], 170)
    g.add_color_stop_rgba(0, *OLIVE, 0.16 * a); g.add_color_stop_rgba(1, *OLIVE, 0)
    ctx.set_source(g); ctx.arc(INS_C[0], INS_C[1], 170, 0, 2 * math.pi); ctx.fill()
    for r, Lr in zip(STRIP_PX, STRIP_LEN):
        ctx.move_to(*r[0])
        for p in r[1:]: ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgba(*OLIVE, 0.35 * a * draw_p); ctx.fill_preserve()
        ctx.set_dash([max(0.01, Lr * draw_p), Lr + 10])
        ctx.set_source_rgba(*HL, 0.95 * a); ctx.set_line_width(2.2); ctx.stroke(); ctx.set_dash([])
    # rotating range ring
    ctx.save(); ctx.translate(*INS_C); ctx.rotate(t * 0.4)
    ctx.set_source_rgba(*HL, 0.35 * a); ctx.set_line_width(1.5); ctx.set_dash([4, 9])
    ctx.arc(0, 0, 140, 0, 2 * math.pi * draw_p); ctx.stroke(); ctx.set_dash([]); ctx.restore()
    # trail between the two hospitals during the transition
    tp = seg(t, TR0 + 0.1, TR1 - 0.05)
    if tp > 0:
        ctx.set_source_rgba(*HL, 0.6 * a); ctx.set_line_width(2); ctx.set_dash([5, 5])
        ctx.move_to(*PIN[0])
        for k in range(1, 21):
            ctx.line_to(*pin_pos(lerp(TR0 + 0.1, TR1 - 0.05, tp * k / 20)))
        ctx.stroke(); ctx.set_dash([])
        ctx.set_source_rgba(*HL, 0.5 * a); ctx.arc(*PIN[0], 4, 0, 2 * math.pi); ctx.fill()
    # pin
    pa = seg(t, 0.75, 1.0)
    if pa > 0:
        x, y = pin_pos(t)
        for ph in (0, 0.5):
            q = (t * 0.9 + ph) % 1
            ctx.set_source_rgba(*HL, 0.7 * (1 - q) * a); ctx.set_line_width(2); ctx.arc(x, y, 7 + 30 * q, 0, 2 * math.pi); ctx.stroke()
        g = cairo.RadialGradient(x, y, 0, x, y, 26)
        g.add_color_stop_rgba(0, 1, 0.95, 0.8, 0.9 * a); g.add_color_stop_rgba(1, *HL, 0)
        ctx.set_source(g); ctx.arc(x, y, 26, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*DARK, a); ctx.arc(x, y, 8 * eback(pa), 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*HL, a); ctx.arc(x, y, 6 * eback(pa), 0, 2 * math.pi); ctx.fill()

# ---------------------------------------------------------------- name plate + connector
NAME_R = W - 70
NAME_Y, CITY_Y = 200, 286
def plate_state(t):
    """returns (scene, in_p, out_p) for the name plate currently on screen"""
    if t < T_SWITCH:
        return SCENES[0], seg(t, 0.95, 1.6), seg(t, TR0, TR0 + 0.3)
    return SCENES[1], seg(t, TR1 - 0.15, TR1 + 0.5), seg(t, 7.5, 7.85)

def draw_plate(ctx, t):
    sc, pin_, pout = plate_state(t)
    if pin_ <= 0 or pout >= 1: return
    a = 1 - pout
    nw = text_w(sc["name"], "black", 66)
    cw = text_w(sc["city"], "medium", 40)
    e = eout(pin_)
    # accent bar
    ctx.set_source_rgba(*OLIVE, a); ctx.rectangle(NAME_R + 14, NAME_Y - 44, 8, 150 * e); ctx.fill()
    draw_text(ctx, sc["name"], "black", 66, NAME_R, NAME_Y, alpha=a * seg(pin_, 0.05, 0.4), wipe=eout(seg(pin_, 0, 0.75)),
              dy=10 * (1 - e))
    # city line with marker dot
    ca = a * seg(pin_, 0.35, 0.7)
    draw_text(ctx, sc["city"], "medium", 40, NAME_R - 34, CITY_Y, alpha=ca, color=HL8, wipe=eout(seg(pin_, 0.3, 0.9)))
    ctx.set_source_rgba(*HL, ca); ctx.arc(NAME_R - 12, CITY_Y + 2, 7, 0, 2 * math.pi); ctx.fill()
    # connector: pin -> elbow -> underline below the name
    lp = eio(seg(pin_, 0.15, 0.85)) * a
    if lp > 0:
        px, py = pin_pos(t)
        ux = NAME_R - max(nw, cw + 34) - 20
        uy = CITY_Y + 44
        pts = [(px + 10, py), (px + 60, py), (px + 60 + (uy - py) * -0.0, uy), (NAME_R + 22, uy)]
        pts = [(px + 10, py), (min(ux, px + 120), uy), (NAME_R + 22, uy)]
        L = [math.dist(p, q) for p, q in zip(pts, pts[1:])]
        tot = sum(L); target = tot * eio(seg(pin_, 0.15, 0.85)); out = [pts[0]]
        for (p, q), l in zip(zip(pts, pts[1:]), L):
            if target >= l: out.append(q); target -= l
            else:
                f = target / l; out.append((p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)); break
        ctx.move_to(*out[0])
        for p in out[1:]: ctx.line_to(*p)
        ctx.set_source_rgba(*HL, 0.9 * a); ctx.set_line_width(2.2); ctx.stroke()
        ctx.arc(*out[-1], 4, 0, 2 * math.pi); ctx.fill()
        if seg(pin_, 0.15, 0.85) >= 1:
            q = (t * 0.8) % 1
            tot_d = tot * q; qq = pts[0]
            for (p, r), l in zip(zip(pts, pts[1:]), L):
                if tot_d <= l: qq = (p[0] + (r[0] - p[0]) * tot_d / l, p[1] + (r[1] - p[1]) * tot_d / l); break
                tot_d -= l
            g = cairo.RadialGradient(qq[0], qq[1], 0, qq[0], qq[1], 14)
            g.add_color_stop_rgba(0, 1, 1, 1, 0.9 * a); g.add_color_stop_rgba(1, *HL, 0)
            ctx.set_source(g); ctx.arc(qq[0], qq[1], 14, 0, 2 * math.pi); ctx.fill()

# ---------------------------------------------------------------- frame
FX, FY, FW, FH = 140, 420, 800, 1240

def frame_xform(t):
    """scale and offset of the whole media frame (digital camera)"""
    intro = eout(seg(t, 0.05, 0.75))
    s = lerp(0.9, 1.0, intro)
    # punch-in through the transition, settle after
    s *= 1 + 0.07 * math.sin(math.pi * seg(t, TR0, TR1))
    s *= 1 + 0.015 * seg(t, TR1, 7.6)
    s *= lerp(1.0, 0.94, eio(seg(t, 7.45, 8.0)))
    rot = 0.012 * math.sin(math.pi * seg(t, TR0, TR1)) * (1 if t < T_SWITCH else -1)
    sx = sy = 0.0
    for te, amp in zip(STRIKES, (14, 18)):
        a = t - te
        if 0 <= a < 0.8:
            e = math.exp(-a * 6) * amp; sx += e * math.sin(a * 70 + te); sy += e * math.cos(a * 55 + te)
    dx = 4 * math.sin(t * 0.8); dy = 5 * math.sin(t * 0.6 + 1)
    return s, rot, sx + dx, sy + dy

def content_zoom(sc, t):
    p = seg(t, sc["t0"], sc["t1"])
    if sc["key"] == "ahli":
        return 1.0 + 0.10 * eio(p) + 0.04 * math.exp(-max(0, t - EXPLOSION) * 3) * (t > EXPLOSION)
    punch = 0.06 * math.exp(-max(0, t - STRIKE2) * 2.5) * (t > STRIKE2)
    return lerp(1.14, 1.02, eout(seg(t, T_SWITCH, T_SWITCH + 0.9))) + 0.05 * eio(seg(t, T_SWITCH + 0.9, DUR)) + punch

def paint_media(ctx, sc, t, x, y, w, h, alpha=1.0):
    surf, sw, sh, _ = clip_frame(sc, t)
    z = content_zoom(sc, t)
    sc_ = max(w / sw, h / sh) * z
    fx, fy = sc["focus"]
    ctx.save(); ctx.rectangle(x, y, w, h); ctx.clip()
    ctx.translate(x + w / 2, y + h / 2); ctx.scale(sc_, sc_)
    ctx.translate(-sw * fx, -sh * fy)
    ctx.set_source_surface(surf, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()

def draw_frame(ctx, t):
    s, rot, ox, oy = frame_xform(t)
    cx, cy = FX + FW / 2, FY + FH / 2
    ctx.save()
    ctx.translate(cx + ox, cy + oy); ctx.rotate(rot); ctx.scale(s, s); ctx.translate(-cx, -cy)
    reveal = eout(seg(t, 0.1, 0.75))
    # shadow
    for i in range(10):
        ctx.set_source_rgba(0, 0, 0, 0.06 * reveal)
        ctx.rectangle(FX - 6 - i * 4, FY - 6 - i * 4 + 14, FW + 12 + i * 8, FH + 12 + i * 8); ctx.fill()
    # reveal: grows from the centre line outwards
    rh = FH * reveal
    ry = FY + (FH - rh) / 2
    ctx.save(); ctx.rectangle(FX - 10, ry - 10, FW + 20, rh + 20); ctx.clip()
    ctx.set_source_rgba(*DARK, 1); ctx.rectangle(FX - 8, FY - 8, FW + 16, FH + 16); ctx.fill()
    sc = scene_at(t)
    paint_media(ctx, sc, t, FX, FY, FW, FH)
    # digital slice glitch around the cut
    gp = 1 - abs(t - T_SWITCH) / 0.22
    if gp > 0:
        other = SCENES[0] if sc is SCENES[1] else SCENES[1]
        for k in range(9):
            if rnd(k, int(t * 30)) < 0.45: continue
            by = FY + FH * rnd(k, int(t * 30) + 3); bh = 20 + 90 * rnd(k, int(t * 30) + 7)
            dxk = (rnd(k, int(t * 30) + 11) - 0.5) * 120 * gp
            ctx.save(); ctx.rectangle(FX, by, FW, bh); ctx.clip(); ctx.translate(dxk, 0)
            paint_media(ctx, other if rnd(k, 5) > 0.5 else sc, t, FX, FY, FW, FH, alpha=0.9)
            ctx.restore()
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*HL, 0.35 * gp); ctx.rectangle(FX, FY, FW, FH); ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
    # light sweep across the glass
    for t0 in (0.75, TR1 - 0.1):
        q = seg(t, t0, t0 + 0.9)
        if 0 < q < 1:
            xx = FX - 300 + (FW + 600) * eio(q)
            g = cairo.LinearGradient(xx - 160, FY, xx + 160, FY + 260)
            g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(0.5, 1, 0.95, 0.85, 0.16); g.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(g); ctx.rectangle(FX, FY, FW, FH); ctx.fill(); ctx.set_operator(cairo.OPERATOR_OVER)
    # inner vignette
    g = cairo.LinearGradient(0, FY + FH - 260, 0, FY + FH)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.45)
    ctx.set_source(g); ctx.rectangle(FX, FY + FH - 260, FW, 260); ctx.fill()
    ctx.restore()
    # border + corner brackets
    ctx.set_source_rgba(*OLIVE, reveal); ctx.set_line_width(3); ctx.rectangle(FX - 1.5, ry - 1.5, FW + 3, rh + 3); ctx.stroke()
    L, o = 46, 18
    ctx.set_source_rgba(*HL, reveal); ctx.set_line_width(4)
    for cx_, cy_, sx_, sy_ in ((FX - o, FY - o, 1, 1), (FX + FW + o, FY - o, -1, 1), (FX - o, FY + FH + o, 1, -1), (FX + FW + o, FY + FH + o, -1, -1)):
        ctx.move_to(cx_, cy_ + sy_ * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx_ * L, cy_); ctx.stroke()
    # side ticks (scanner rail)
    for k in range(24):
        yy = FY + 30 + k * (FH - 60) / 23
        ln = 14 if k % 4 == 0 else 7
        ctx.set_source_rgba(*HL, 0.45 * reveal); ctx.set_line_width(1.5)
        ctx.move_to(FX + FW + 34, yy); ctx.line_to(FX + FW + 34 + ln, yy); ctx.stroke()
    # moving marker on the rail
    my = FY + 30 + (FH - 60) * (0.5 + 0.5 * math.sin(t * 1.4))
    ctx.set_source_rgba(*HL, reveal); ctx.move_to(FX + FW + 30, my); ctx.line_to(FX + FW + 18, my - 7); ctx.line_to(FX + FW + 18, my + 7); ctx.close_path(); ctx.fill()
    # live dot in the frame corner
    da = reveal * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 6)))
    ctx.set_source_rgba(*HL, da); ctx.arc(FX + FW - 30, FY + 30, 7, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

# ---------------------------------------------------------------- background + bottom rail
def draw_bg(ctx, t):
    ctx.set_source_rgb(*[c * 0.8 for c in DARK]); ctx.paint()
    sc = scene_at(t)
    surf, sw, sh, path = clip_frame(sc, t)
    key = ("blur", path)
    if key not in _mc:
        im = Image.open(path).convert("RGB").resize((sw // 8, sh // 8)).filter(ImageFilter.GaussianBlur(6))
        a = np.asarray(im)
        h, w = a.shape[:2]
        bgra = np.dstack([a[..., 2], a[..., 1], a[..., 0], np.full((h, w), 255, np.uint8)])
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
        buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
        _mc[key] = cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)
        if len(_mc) > 14: _mc.pop(next(iter(_mc)))
    bs = _mc[key]
    z = max(W / bs.get_width(), H / bs.get_height()) * 1.15
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-bs.get_width() / 2, -bs.get_height() / 2)
    ctx.set_source_surface(bs, 0, 0); ctx.get_source().set_filter(cairo.FILTER_BILINEAR); ctx.paint_with_alpha(0.55)
    ctx.restore()
    ctx.set_source_rgba(*DARK, 0.55); ctx.paint()
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgba(0, *OLIVE, 0.10); g.add_color_stop_rgba(0.5, 0, 0, 0, 0); g.add_color_stop_rgba(1, *OLIVE, 0.12)
    ctx.set_source(g); ctx.paint()
    off = (t * 10) % 60
    ctx.set_source_rgba(*HL, 0.06)
    for yy in range(-60, H + 60, 60):
        for xx in range(0, W + 60, 60):
            ctx.rectangle(xx, yy + off, 2, 2)
    ctx.fill()

def draw_rail(ctx, t):
    a = seg(t, 0.5, 1.0) * (1 - seg(t, 7.55, 7.95))
    if a <= 0: return
    y = 1760; x0, x1 = 140, 940
    ctx.set_source_rgba(*OLIVE, 0.5 * a); ctx.rectangle(x0, y - 1, x1 - x0, 2); ctx.fill()
    prog = clamp(t / DUR)
    # RTL progress: fills from the right
    ctx.set_source_rgba(*HL, a); ctx.rectangle(x1 - (x1 - x0) * prog, y - 2, (x1 - x0) * prog, 4); ctx.fill()
    for k, xx in enumerate((x1 - 8, x0 + (x1 - x0) * (1 - T_SWITCH / DUR))):
        on = (t >= SCENES[k]["t0"])
        ctx.set_source_rgba(*DARK, a); ctx.arc(xx, y, 11, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*(HL if on else OLIVE), a); ctx.set_line_width(2.5); ctx.arc(xx, y, 11, 0, 2 * math.pi); ctx.stroke()
        if on:
            ctx.arc(xx, y, 5, 0, 2 * math.pi); ctx.fill()

def corner_frame(ctx, alpha):
    ctx.set_source_rgba(*HL, alpha); ctx.set_line_width(2)
    x, y, w, h, L = 34, 34, W - 68, H - 68, 50
    for cx_, cy_, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        ctx.move_to(cx_, cy_ + sy * L); ctx.line_to(cx_, cy_); ctx.line_to(cx_ + sx * L, cy_); ctx.stroke()

# ---------------------------------------------------------------- post
yy_, xx_ = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2)
VIG = np.clip(1.0 - 0.45 * np.clip(_d - 0.5, 0, None) ** 1.6, 0.45, 1.0).astype(np.float32)[..., None]
del yy_, xx_, _d
_rng = np.random.default_rng(7)
GRAIN = [_rng.normal(0, 2.0, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]

def surf_array(surf):
    return np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())

def render(i):
    t = i / FPS
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    draw_bg(ctx, t)
    draw_frame(ctx, t)
    draw_locator(ctx, t)
    draw_plate(ctx, t)
    draw_rail(ctx, t)
    corner_frame(ctx, 0.45 * seg(t, 0.2, 0.9) * (1 - seg(t, 7.5, 7.9)))
    # explosion light spill + transition flash
    fl = 0.0
    for te, amp in zip(STRIKES, (0.28, 0.24)):
        ex = t - te
        if 0 <= ex < 0.6: fl += amp * math.exp(-ex * 6)
    fl += 0.22 * max(0.0, 1 - abs(t - T_SWITCH) / 0.15)
    if fl > 0:
        ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_rgba(1, 0.62, 0.25, fl); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)
    surf.flush()
    a = surf_array(surf)[..., :3].astype(np.float32)
    a *= VIG
    a += np.repeat(np.repeat(GRAIN[i % 6], 2, axis=0), 2, axis=1)
    a *= seg(t, 0.0, 0.25) * (1 - seg(t, 7.7, 8.0))
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
                               "-i", "-", "-c:v", "libx264", "-preset", "slow", "-b:v", "18M", "-maxrate", "24M", "-bufsize", "36M",
                               "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", sys.argv[2]], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render, range(N), chunksize=3)):
                ff.stdin.write(fr)
        ff.stdin.close(); ff.wait(); print("done")
