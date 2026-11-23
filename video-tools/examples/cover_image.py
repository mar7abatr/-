import math, pickle
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw, ImageFilter, ImageEnhance

W, H = 1080, 1920
OUT = "/tmp/w5"

def hexc(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
OLIVE = hexc("896829"); DARK = hexc("1D1D1D"); HL = hexc("C7973B"); HL8 = (0xC7, 0x97, 0x3B)
def rnd(i, k=0):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)

# ---------------------------------------------------------------- helpers
def to_surface(rgba):
    a = np.asarray(rgba).astype(np.float32)
    al = a[..., 3:4] / 255
    bgra = np.dstack([a[..., 2] * al[..., 0], a[..., 1] * al[..., 0], a[..., 0] * al[..., 0], a[..., 3]]).astype(np.uint8)
    h, w = bgra.shape[:2]
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8); buf[:, :w * 4] = bgra.reshape(h, w * 4)
    return cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)

FONTS = {"black": "/tmp/work/fonts/black.otf", "bold": "/tmp/work/fonts/bold.ttf", "medium": "/tmp/work/fonts/medium.otf"}
def text_img(s, font, size, color=(255, 255, 255)):
    f = ImageFont.truetype(FONTS[font], size, layout_engine=ImageFont.Layout.RAQM)
    b = f.getbbox(s, direction="rtl", language="ar")
    pad = 30
    im = Image.new("RGBA", (b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), s, font=f, fill=color + (255,), direction="rtl", language="ar")
    return im, pad

def draw_text(ctx, s, font, size, x, y, color=(255, 255, 255), align="right", shadow=0.75, glow=None):
    im, pad = text_img(s, font, size, color)
    w, h = im.size
    x0 = x - w + pad if align == "right" else x - w / 2
    y0 = y - h / 2
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)))
        ctx.set_source_surface(to_surface(sh), x0 + 3, y0 + 6); ctx.paint_with_alpha(shadow)
    if glow:
        gl = Image.new("RGBA", im.size, glow + (0,)); gl.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(16)))
        ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_surface(to_surface(gl), x0, y0); ctx.paint_with_alpha(0.55)
        ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.set_source_surface(to_surface(im), x0, y0); ctx.paint()
    return w - 2 * pad, h - 2 * pad

def grade(im, warm=1.0):
    """cinematic war grade: crushed blacks, warm amber highlights, slightly desaturated"""
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    lum = a @ np.array([0.3, 0.59, 0.11])
    a = a * 0.78 + lum[..., None] * 0.22
    a = np.clip((a - 0.06) / 0.92, 0, 1)
    a = a * a * (3 - 2 * a) * 0.55 + a * 0.45          # S-curve
    sh = np.array(DARK) * 0.9; hi = np.array([1.0, 0.82, 0.58])
    t = lum[..., None]
    a = a * (1 - 0.18 * warm) + (sh * (1 - t) + hi * t) * 0.18 * warm * 1.6
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def corner(ctx, x, y, w, h, L=34, lw=3, a=1.0):
    ctx.set_source_rgba(*HL, a); ctx.set_line_width(lw)
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        ctx.move_to(cx, cy + sy * L); ctx.line_to(cx, cy); ctx.line_to(cx + sx * L, cy); ctx.stroke()

# ---------------------------------------------------------------- canvas
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
ctx.set_source_rgb(*[c * 0.75 for c in DARK]); ctx.paint()

# lower atmosphere: Baptist-hospital night fire, blurred and graded
ah = Image.open(f"{OUT}/f/ahli.png").convert("RGB")
atm = ah.crop((0, 120, 480, 760)).resize((1080, 1440), Image.BICUBIC).filter(ImageFilter.GaussianBlur(22))
atm = ImageEnhance.Brightness(grade(ImageEnhance.Color(atm).enhance(0.25))).enhance(0.55)
ctx.set_source_surface(to_surface(atm.convert("RGBA")), 0, 620); ctx.paint_with_alpha(0.75)
g = cairo.LinearGradient(0, 600, 0, 1300)
g.add_color_stop_rgba(0, *[c * 0.75 for c in DARK], 1); g.add_color_stop_rgba(0.45, *[c * 0.75 for c in DARK], 0.55)
g.add_color_stop_rgba(1, *[c * 0.6 for c in DARK], 0.3)
ctx.set_source(g); ctx.rectangle(0, 600, W, H - 600); ctx.fill()

# ---------------------------------------------------------------- hero: strike at Nasser Medical Complex
src = Image.open(f"{OUT}/f/d_29.56.png").convert("RGB")
crop = src.crop((300, 100, 1380, 800))                     # avoids channel bug, live tag and ticker
# soften residual interlace combing before grading
hero = crop.filter(ImageFilter.GaussianBlur(1.1)).resize((int(crop.width * 1.04), int(crop.height * 1.04)), Image.LANCZOS)
hero = hero.filter(ImageFilter.UnsharpMask(radius=1.5, percent=45, threshold=3))
hero = ImageEnhance.Contrast(ImageEnhance.Brightness(hero).enhance(0.72)).enhance(1.32)
hero = grade(hero)
hx = (W - hero.width) // 2 + 20; hy = 150
# feathered edges
mask = Image.new("L", hero.size, 255)
m = np.asarray(mask).astype(np.float32)
yy = np.linspace(0, 1, hero.height)[:, None]; xx = np.linspace(0, 1, hero.width)[None, :]
fade = np.clip(yy / 0.14, 0, 1) * np.clip((1 - yy) / 0.30, 0, 1)
fade = fade * np.clip(xx / 0.06, 0, 1) * np.clip((1 - xx) / 0.06, 0, 1)
hero_rgba = hero.convert("RGBA"); hero_rgba.putalpha(Image.fromarray((fade ** 1.2 * 255).astype(np.uint8)))
ctx.set_source_surface(to_surface(hero_rgba), hx, hy); ctx.paint()

# anamorphic flare across the fireball
fx, fy = hx + int((470 - 300) * 1.04), hy + int((330 - 100) * 1.04)
ctx.set_operator(cairo.OPERATOR_ADD)
g = cairo.RadialGradient(fx, fy, 0, fx, fy, 340)
g.add_color_stop_rgba(0, 1, 0.75, 0.4, 0.32); g.add_color_stop_rgba(0.4, 1, 0.5, 0.15, 0.1); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
ctx.set_source(g); ctx.arc(fx, fy, 380, 0, 2 * math.pi); ctx.fill()
g = cairo.LinearGradient(fx - 700, fy, fx + 700, fy)
g.add_color_stop_rgba(0, 1, 0.6, 0.2, 0); g.add_color_stop_rgba(0.5, 1, 0.85, 0.6, 0.55); g.add_color_stop_rgba(1, 1, 0.6, 0.2, 0)
ctx.set_source(g); ctx.rectangle(fx - 700, fy - 2.5, 1400, 5); ctx.fill()
g = cairo.LinearGradient(fx - 500, fy, fx + 500, fy)
g.add_color_stop_rgba(0, 1, 0.6, 0.2, 0); g.add_color_stop_rgba(0.5, 1, 0.7, 0.35, 0.18); g.add_color_stop_rgba(1, 1, 0.6, 0.2, 0)
ctx.set_source(g); ctx.rectangle(fx - 500, fy - 16, 1000, 32); ctx.fill()
ctx.set_operator(cairo.OPERATOR_OVER)

# targeting reticle on the strike point
def reticle(cx, cy, r, a=1.0):
    ctx.set_source_rgba(*HL, a); ctx.set_line_width(2.5)
    L = r * 0.42
    for i in range(4):
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(i * math.pi / 2)
        ctx.move_to(r, r - L); ctx.line_to(r, r); ctx.line_to(r - L, r); ctx.stroke(); ctx.restore()
    ctx.set_line_width(1.5)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ctx.move_to(cx + dx * r * 0.3, cy + dy * r * 0.3); ctx.line_to(cx + dx * r * 0.62, cy + dy * r * 0.62); ctx.stroke()
    ctx.arc(cx, cy, 3.5, 0, 2 * math.pi); ctx.fill()
reticle(fx, fy, 92, 0.9)

# ---------------------------------------------------------------- headline
TY = 985
# headline removed at the user's request

# ---------------------------------------------------------------- map
MAP = pickle.load(open("/tmp/work/geo/map.pkl", "rb"))
LAT0, LON0 = 31.42, 34.38
KX = math.cos(math.radians(LAT0)) * 111.32; KY = 110.57
def P(lon, lat): return ((lon - LON0) * KX, -(lat - LAT0) * KY)
S, C, MC = 17.0, (1.25, 1.15), (700, 1545)
def mp(p): return (MC[0] + (p[0] - C[0]) * S, MC[1] + (p[1] - C[1]) * S)

ctx.push_group()
# grid
ctx.set_source_rgba(*HL, 0.07); ctx.set_line_width(1)
for k in range(-30, 31, 5):
    x, _ = mp((k, 0)); ctx.move_to(x, 1180); ctx.line_to(x, H)
    _, y = mp((0, k)); ctx.move_to(0, y); ctx.line_to(W, y)
ctx.stroke()
# neighbouring land + borders
for r in MAP["land"]:
    for ring in r:
        ctx.move_to(*mp(ring[0]))
        for p in ring[1:]: ctx.line_to(*mp(p))
        ctx.close_path()
ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); ctx.set_source_rgba(0.12, 0.11, 0.1, 0.75); ctx.fill()
for ln in MAP["borders"]:
    ctx.move_to(*mp(ln[0]))
    for p in ln[1:]: ctx.line_to(*mp(p))
ctx.set_source_rgba(*HL, 0.3); ctx.set_line_width(1.5); ctx.stroke()
# strip
ring = MAP["strip"][0][0]
ctx.move_to(*mp(ring[0]))
for p in ring[1:]: ctx.line_to(*mp(p))
ctx.close_path(); strip = ctx.copy_path()
ctx.set_source_rgba(*OLIVE, 0.42); ctx.fill()
ctx.save(); ctx.append_path(strip); ctx.clip()
for kind, pts in MAP["roads"]:
    ctx.move_to(*mp(pts[0]))
    for p in pts[1:]: ctx.line_to(*mp(p))
ctx.set_source_rgba(*HL, 0.22); ctx.set_line_width(1); ctx.stroke()
for gv in MAP["gov"]:
    ctx.move_to(*mp(gv[0]))
    for p in gv[1:]: ctx.line_to(*mp(p))
    ctx.close_path()
ctx.set_source_rgba(*HL, 0.4); ctx.set_dash([4, 4]); ctx.set_line_width(1.2); ctx.stroke(); ctx.set_dash([])
ctx.restore()
# glowing outline
for lw, a in ((16, 0.10), (8, 0.22), (3, 1.0)):
    ctx.append_path(strip); ctx.set_source_rgba(*HL, a); ctx.set_line_width(lw); ctx.stroke()
# soft top edge: the map dissolves into the headline area instead of a hard band
ctx.pop_group_to_source()
mg = cairo.LinearGradient(0, 1150, 0, 1330)
mg.add_color_stop_rgba(0, 0, 0, 0, 0); mg.add_color_stop_rgba(1, 0, 0, 0, 1)
ctx.mask(mg)
# the strip itself must stay fully visible above the fade
ctx.save(); ctx.rectangle(0, 1150, W, 200); ctx.clip()
ring = MAP["strip"][0][0]
ctx.move_to(*mp(ring[0]))
for p in ring[1:]: ctx.line_to(*mp(p))
ctx.close_path()
ctx.set_source_rgba(*OLIVE, 0.42); ctx.fill_preserve()
ctx.set_source_rgba(*HL, 1); ctx.set_line_width(3); ctx.stroke()
ctx.restore()

# struck hospitals (others)
def burst(x, y, r, a=1.0):
    ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, 0, x, y, r * 3.2)
    g.add_color_stop_rgba(0, 1, 0.7, 0.3, 0.75 * a); g.add_color_stop_rgba(0.35, 1, 0.45, 0.1, 0.3 * a); g.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
    ctx.set_source(g); ctx.arc(x, y, r * 3.2, 0, 2 * math.pi); ctx.fill()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.set_source_rgba(1, 0.85, 0.55, a)
    n = 10
    ctx.move_to(x + r, y)
    for k in range(1, 2 * n + 1):
        ang = k * math.pi / n; rr = r if k % 2 == 0 else r * 0.45
        ctx.line_to(x + math.cos(ang) * rr, y + math.sin(ang) * rr)
    ctx.close_path(); ctx.fill()
for k in ("shifa", "kamal", "o_indonesian", "o_aqsa", "o_european", "o_rantisi", "o_awda_nus", "o_quds"):
    x, y = mp(MAP["hosp"][k]); burst(x, y, 9, 0.85)

# main markers
def marker(x, y):
    burst(x, y, 16)
    for r, a in ((34, 0.8), (54, 0.45), (76, 0.22)):
        ctx.set_source_rgba(*HL, a); ctx.set_line_width(2); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.stroke()
    ctx.set_source_rgba(*DARK, 1); ctx.arc(x, y, 11, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*HL, 1); ctx.arc(x, y, 8, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 1); ctx.rectangle(x - 1.6, y - 5, 3.2, 10); ctx.rectangle(x - 5, y - 1.6, 10, 3.2); ctx.fill()

bx, by = mp(P(34.46158, 31.50472))     # Al-Ahli Baptist
nx, ny = mp(P(34.29229, 31.34703))     # Nasser
marker(bx, by); marker(nx, ny)

# Baptist inset frame (left), linked to its marker
ins = grade(ah.crop((0, 230, 480, 610)), warm=0.6).resize((396, 314), Image.LANCZOS)
IX, IY = 56, 1240
ctx.set_source_rgba(0, 0, 0, 0.6); ctx.rectangle(IX - 4, IY + 8, ins.width + 16, ins.height + 16); ctx.fill()
ctx.set_source_surface(to_surface(ins.convert("RGBA")), IX, IY); ctx.paint()
ctx.set_source_rgba(*OLIVE, 1); ctx.set_line_width(3); ctx.rectangle(IX - 1.5, IY - 1.5, ins.width + 3, ins.height + 3); ctx.stroke()
corner(ctx, IX - 14, IY - 14, ins.width + 28, ins.height + 28)
ctx.set_source_rgba(*HL, 0.95); ctx.set_line_width(2.6)
ax, ay = IX + ins.width + 14, IY + ins.height * 0.35
ctx.move_to(bx - 36, by); ctx.line_to(ax + 30, by); ctx.line_to(ax, ay); ctx.stroke()
ctx.arc(ax, ay, 5, 0, 2 * math.pi); ctx.fill()
# label under the inset
ly = IY + ins.height + 58
bw_ = 382 + 50
ctx.set_source_rgba(*DARK, 0.92); ctx.rectangle(IX - 1.5, ly - 34, bw_, 68); ctx.fill()
ctx.set_source_rgba(*OLIVE, 1); ctx.rectangle(IX - 1.5 + bw_ - 7.5, ly - 34, 7.5, 68); ctx.fill()
draw_text(ctx, "المستشفى المعمداني", "bold", 42, IX + bw_ - 24, ly, shadow=0)

# Nasser label (right), linked to its marker and up to the hero image
NLX, NLY = W - 38, 1712
lw_ = 318 + 50
ctx.set_source_rgba(*DARK, 0.92); ctx.rectangle(NLX - lw_, NLY - 34, lw_, 68); ctx.fill()
ctx.set_source_rgba(*OLIVE, 1); ctx.rectangle(NLX - 7.5, NLY - 34, 7.5, 68); ctx.fill()
draw_text(ctx, "مجمع ناصر الطبي", "bold", 46, NLX - 24, NLY, shadow=0)
ctx.set_source_rgba(*HL, 0.95); ctx.set_line_width(2.6)
ctx.move_to(nx + 36, ny); ctx.line_to(nx + 110, ny); ctx.line_to(NLX - lw_ - 30, NLY); ctx.line_to(NLX - lw_, NLY); ctx.stroke()
ctx.arc(NLX - lw_, NLY, 5, 0, 2 * math.pi); ctx.fill()

# ---------------------------------------------------------------- atmosphere: smoke, embers, frame
for i in range(26):
    x = rnd(i, 1) * W; y = 600 + rnd(i, 2) * 1300; r = 120 + 260 * rnd(i, 3)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, 0.1, 0.09, 0.08, 0.16 * rnd(i, 4)); g.add_color_stop_rgba(1, 0.1, 0.09, 0.08, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()
ctx.set_operator(cairo.OPERATOR_ADD)
for i in range(90):
    x = rnd(i, 11) * W; y = rnd(i, 12) * H; r = 1.2 + 3.2 * rnd(i, 13) ** 2
    a = 0.35 + 0.65 * rnd(i, 14)
    if 960 < y < 1200 and x > 300: a *= 0.25   # keep the headline clean
    g = cairo.RadialGradient(x, y, 0, x, y, r * 4)
    g.add_color_stop_rgba(0, 1, 0.78, 0.45, a); g.add_color_stop_rgba(1, 1, 0.45, 0.1, 0)
    ctx.set_source(g); ctx.arc(x, y, r * 4, 0, 2 * math.pi); ctx.fill()
    # motion streak on larger embers
    if r > 3:
        ctx.set_source_rgba(1, 0.7, 0.35, a * 0.5); ctx.set_line_width(r * 0.8)
        ctx.move_to(x, y); ctx.line_to(x - 14, y + 26); ctx.stroke()
ctx.set_operator(cairo.OPERATOR_OVER)
corner(ctx, 34, 34, W - 68, H - 68, L=60, lw=2, a=0.55)

surf.flush()
a = np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())[..., :3][..., ::-1].astype(np.float32)
# vignette + grain
yy, xx = np.mgrid[0:H, 0:W]
d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.48) / (H / 2)) ** 2)
a *= np.clip(1 - 0.55 * np.clip(d - 0.45, 0, None) ** 1.5, 0.3, 1)[..., None]
a += np.random.default_rng(3).normal(0, 4.0, (H, W, 1))
img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
# gentle bloom
bl = img.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(8)).resize((W, H))
b = np.asarray(bl).astype(np.float32); b = np.clip(b - 140, 0, None) * 0.6
img = Image.fromarray(np.clip(np.asarray(img).astype(np.float32) + b, 0, 255).astype(np.uint8))
img.save(f"{OUT}/cover.png", optimize=True)
img.resize((540, 960), Image.LANCZOS).save(f"{OUT}/cover_small.png")
print("ok")
