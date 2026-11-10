"""Khor Mor news report renderer: 2D infographic map + connector-linked media frames, synced to the VO."""
import json, math, os, subprocess, sys
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape, Point
from shapely.ops import unary_union

os.chdir(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1920, 1080, 30
T0 = 1.5                 # silent visual intro before the recording starts
SPEECH_END = 75.30       # end of narration (audio time)
HOLD = 3.0
DUR = T0 + SPEECH_END + HOLD
NFRAMES = int(round(DUR * FPS))
COSL = math.cos(math.radians(34.0))

# ---------------------------------------------------------------- palette
def col(r, g, b, a=1.0):
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), r, g, b)
CYAN = (54, 197, 255)
AMBER = (255, 178, 46)
RED = (255, 64, 58)
ORANGE = (255, 120, 40)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eio(p): p = clamp(p); return 4 * p * p * p if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def eout(p): p = clamp(p); return 1 - (1 - p) ** 3
def ein(p): p = clamp(p); return p * p * p
def eback(p):
    p = clamp(p); c1 = 1.4; c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
def lerp(a, b, p): return a + (b - a) * p
def env(t, tin, tout, fin=0.45, fout=0.4):
    """0..1 visibility envelope; tout is when the element is fully gone."""
    if t < tin or t >= tout: return 0.0
    return eout((t - tin) / fin) * (1 - ein((t - (tout - fout)) / fout))

# ---------------------------------------------------------------- projection / camera
def mp(lon, lat): return ((lon - 44.0) * COSL, -(lat - 34.0))

class Camera:
    def __init__(self, keys):
        # key: (t, dur, lon, lat, s, sx, sy) => (lon,lat) lands at screen (sx,sy) with s px/deg
        self.keys = []
        for t, d, lon, lat, s, sx, sy in keys:
            mx, my = mp(lon, lat)
            self.keys.append((t, d, mx - (sx - W / 2) / s, my - (sy - H / 2) / s, math.log(s)))
        self.starts = [None] * len(self.keys)
        st = self.keys[0][2:]
        for i, k in enumerate(self.keys):
            self.starts[i] = self._eval(k[0], i, st) if i else st
    def _eval(self, t, upto, st0):
        st = st0
        for i in range(upto):
            k = self.keys[i]
            if t < k[0]: break
            p = eio((t - k[0]) / k[1])
            s0 = self.starts[i]
            st = tuple(lerp(a, b, p) for a, b in zip(s0, k[2:]))
        return st
    def at(self, t):
        cx, cy, ls = self._eval(t, len(self.keys), self.keys[0][2:])
        return cx, cy, math.exp(ls)

class View:
    def __init__(self, cx, cy, s):
        self.cx, self.cy, self.s = cx, cy, s
    def scr(self, lonlat):
        mx, my = mp(*lonlat)
        return (W / 2 + (mx - self.cx) * self.s, H / 2 + (my - self.cy) * self.s)
    def matrix(self):
        m = skia.Matrix()
        m.setScaleTranslate(self.s, self.s, W / 2 - self.cx * self.s, H / 2 - self.cy * self.s)
        return m

# ---------------------------------------------------------------- places (lon, lat)
KM = (44.8215, 35.1347)          # Khor Mor gas field
CHAM = (44.830, 35.533)          # Chamchamal
ERBIL = (44.009, 36.191)
SUL = (45.435, 35.557)
BAGHDAD = (44.366, 33.315)
KRG_CITIES = [ERBIL, SUL, (42.988, 36.867), (45.986, 35.177), (44.628, 36.083), (44.883, 36.255),
              (44.544, 36.653), (42.687, 37.144), (43.893, 36.741), (45.322, 34.629), (44.30, 36.40),
              (45.70, 35.80), (43.40, 36.95)]
SD_LAUNCH = (44.38, 34.78)
SD_PTS = [(44.38, 34.78), (44.05, 34.62), (44.60, 34.98)]
KIR_PTS = [(44.15, 35.30), (43.90, 35.62), (44.45, 35.40)]
ARMED_PTS = [(44.25, 34.62), (43.85, 34.72), (44.55, 34.85), (43.75, 34.45), (44.10, 34.35)]
IRAN_PT = (46.9, 33.9)

# ---------------------------------------------------------------- geo
def to_path(geom):
    p = skia.Path()
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    for poly in polys:
        for ring in [poly.exterior] + list(poly.interiors):
            cs = list(ring.coords)
            x, y = mp(*cs[0]); p.moveTo(x, y)
            for c in cs[1:]:
                x, y = mp(*c); p.lineTo(x, y)
            p.close()
    return p

countries = {f['properties']['ADM0_A3']: shape(f['geometry']) for f in json.load(open('geo/countries.json'))['features']}
gov = {f['properties']['name']: shape(f['geometry']) for f in json.load(open('geo/irq_adm1.json'))['features']}
rivers = [shape(f['geometry']) for f in json.load(open('geo/rivers_sel.json'))['features']]
IRQ = countries['IRQ']
KRG = unary_union([gov['Dihok'], gov['Arbil'], gov['As-Sulaymaniyah']])
for pt in SD_PTS + ARMED_PTS: assert gov['Sala ad-Din'].contains(Point(pt)), pt
for pt in KIR_PTS: assert gov["At-Ta'mim"].contains(Point(pt)), pt
assert gov['As-Sulaymaniyah'].contains(Point(KM))

P_NEIGH = {k: to_path(g.simplify(0.01)) for k, g in countries.items() if k != 'IRQ'}
P_IRQ = to_path(IRQ.simplify(0.003))
P_GOV = {k: to_path(g.simplify(0.003)) for k, g in gov.items()}
P_KRG = to_path(KRG.simplify(0.003))
P_RIV = skia.Path()
for r in rivers:
    for ln in ([r] if r.geom_type == 'LineString' else list(r.geoms)):
        cs = list(ln.simplify(0.005).coords)
        x, y = mp(*cs[0]); P_RIV.moveTo(x, y)
        for c in cs[1:]:
            x, y = mp(*c); P_RIV.lineTo(x, y)
# dot-matrix texture inside Iraq
_d = []
irq_s = IRQ.simplify(0.01)
for lat in np.arange(29.0, 37.5, 0.12):
    for lon in np.arange(38.7, 48.7, 0.12 / COSL):
        if irq_s.contains(Point(lon, lat)): _d.append(skia.Point(*mp(lon, lat)))
IRQ_DOTS = _d
P_GRAT = skia.Path()
for lon in range(20, 70):
    a, b = mp(lon, 20), mp(lon, 45); P_GRAT.moveTo(*a); P_GRAT.lineTo(*b)
for lat in range(20, 46):
    a, b = mp(20, lat), mp(70, lat); P_GRAT.moveTo(*a); P_GRAT.lineTo(*b)

# ---------------------------------------------------------------- text
FONTS = {'L': 'fonts/din-light.otf', 'R': 'fonts/din-regular.ttf', 'M': 'fonts/din-medium.ttf',
         'B': 'fonts/din-bold2.ttf', 'K': 'fonts/din-black.ttf'}
_fcache, _tcache = {}, {}
def text_img(s, size, weight='M', color=WHITE, rtl=True):
    key = (s, size, weight, color, rtl)
    if key in _tcache: return _tcache[key]
    fk = (weight, size)
    if fk not in _fcache: _fcache[fk] = ImageFont.truetype(FONTS[weight], size, layout_engine=ImageFont.Layout.RAQM)
    f = _fcache[fk]
    kw = dict(direction='rtl', language='ar') if rtl else dict(direction='ltr')
    l, t_, r, b = f.getbbox(s, **kw)
    pad = 6
    im = Image.new('RGBA', (r - l + 2 * pad, b - t_ + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t_), s, font=f, fill=color + (255,), **kw)
    img = skia.Image.fromarray(np.ascontiguousarray(np.array(im)), colorType=skia.ColorType.kRGBA_8888_ColorType,
                               alphaType=skia.AlphaType.kUnpremul_AlphaType)
    _tcache[key] = img
    return img

def draw_text(c, s, size, x, y, weight='M', color=WHITE, alpha=1.0, anchor='rc', rtl=True, glow=0):
    """anchor: r/c/l horizontally + c/t/b vertically; (x,y) in screen px."""
    if alpha <= 0.003: return 0, 0
    img = text_img(s, size, weight, color, rtl)
    w, h = img.width(), img.height()
    ax = {'r': x - w, 'c': x - w / 2, 'l': x}[anchor[0]]
    ay = {'c': y - h / 2, 't': y, 'b': y - h}[anchor[1]]
    if glow:
        gp = skia.Paint(AntiAlias=True, Alphaf=alpha * 0.6,
                        ImageFilter=skia.ImageFilters.Blur(glow, glow))
        c.drawImage(img, ax, ay, skia.SamplingOptions(skia.FilterMode.kLinear), gp)
    c.drawImage(img, ax, ay, skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(Alphaf=alpha))
    return w, h

# ---------------------------------------------------------------- media
class Clip:
    def __init__(self, name):
        idx = {l.split()[0]: l.split()[1:] for l in open('media/index.txt').read().split('\n') if l}
        w, h, n = map(int, idx[name])
        self.w, self.h, self.n = w, h, n
        self.mm = np.memmap(f'media/{name}.rgba', np.uint8, 'r', shape=(n, h, w, 4))
        self.aspect = w / h
        self._last = (None, None)
    def image(self, local_t):
        i = int(clamp(local_t * FPS, 0, self.n - 1))
        if self._last[0] == i: return self._last[1]
        img = skia.Image.fromarray(np.ascontiguousarray(self.mm[i]), colorType=skia.ColorType.kRGBA_8888_ColorType,
                                   alphaType=skia.AlphaType.kUnpremul_AlphaType)
        self._last = (i, img)
        return img

class Still:
    def __init__(self, path):
        im = Image.open(path).convert('RGBA')
        self.w, self.h = im.size
        self.aspect = self.w / self.h
        self.img = skia.Image.fromarray(np.ascontiguousarray(np.array(im)), colorType=skia.ColorType.kRGBA_8888_ColorType,
                                        alphaType=skia.AlphaType.kUnpremul_AlphaType)
    def image(self, local_t): return self.img

ATT = '../.hoplite/attachments'
M = {k: Clip(k) for k in ['drone_side', 'drone_front', 'k1', 'k2b', 'launch', 'pm1', 'pm2']}
DANA = Still(f'{ATT}/art_upload_3905745e826249c6a20d3e9bde545f49/5447370299729975987.jpg')
MOE = Still(f'{ATT}/art_upload_3e074e55e43442dfb2de35bb557dc394/5447370299729975986.jpg')

# ---------------------------------------------------------------- primitives
def glow_line_paint(color, a, width, blur=0):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width,
                   Color=col(*color, a), StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p

def radial_glow(c, x, y, r, color, a):
    if a <= 0.003: return
    sh = skia.GradientShader.MakeRadial(skia.Point(x, y), r, [col(*color, a), col(*color, a * 0.35), col(*color, 0)],
                                        [0, 0.35, 1])
    c.drawCircle(x, y, r, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kPlus))

def marker(c, x, y, t, color, a, big=False, t0=0.0):
    if a <= 0.003: return
    radial_glow(c, x, y, 70 if big else 45, color, 0.55 * a)
    for k in range(3 if big else 2):
        ph = ((t - t0) / 1.8 + k / 3) % 1.0
        r = 8 + ph * (70 if big else 46)
        c.drawCircle(x, y, r, glow_line_paint(color, a * (1 - ph) * 0.9, 2.2))
    if big:
        c.save(); c.translate(x, y); c.rotate((t * 25) % 360)
        p = glow_line_paint(color, a * 0.95, 2.5)
        rr = 26
        for k in range(4):
            c.drawArc(skia.Rect(-rr, -rr, rr, rr), k * 90 + 12, 66, False, p)
        c.restore()
        p = glow_line_paint(WHITE, a * 0.7, 1.6)
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            c.drawLine(x + dx * 33, y + dy * 33, x + dx * 44, y + dy * 44, p)
    c.drawCircle(x, y, 9 if big else 7, skia.Paint(AntiAlias=True, Color=col(*color, a)))
    c.drawCircle(x, y, 4 if big else 3, skia.Paint(AntiAlias=True, Color=col(255, 255, 255, a)))

def label_pill(c, text, x, y, a, size=30, weight='M', accent=CYAN, side='r', dy=0, sub=False):
    """Map label to the side of anchor (x,y). side='r' puts the pill to the right of the point."""
    if a <= 0.003: return
    img = text_img(text, size, weight)
    tw, th = img.width(), img.height()
    pw, ph = tw + 30, th + 10
    gap = 26
    px = x + gap if side == 'r' else x - gap - pw
    py = y - ph / 2 + dy
    reveal = eout(a)
    c.save()
    c.clipRect(skia.Rect(px, py - 4, px + pw * reveal + 1, py + ph + 4) if side == 'r'
               else skia.Rect(px + pw * (1 - reveal), py - 4, px + pw + 1, py + ph + 4))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(px, py, px + pw, py + ph), 4, 4),
                skia.Paint(AntiAlias=True, Color=col(4, 14, 26, 0.82 * a)))
    c.drawRect(skia.Rect(px + pw - 5, py, px + pw, py + ph), skia.Paint(Color=col(*accent, a)))
    c.drawImage(img, px + 12, py + 5, skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(Alphaf=a))
    c.restore()
    lx = px if side == 'r' else px + pw
    c.drawLine(x + (10 if side == 'r' else -10), y, lx, py + ph / 2, glow_line_paint(accent, a * 0.8, 1.6))

def bezier_pts(p0, p1, bend=0.22, n=64):
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bend, my + dx * bend
    ts = np.linspace(0, 1, n)
    xs = (1 - ts) ** 2 * x0 + 2 * (1 - ts) * ts * cx + ts ** 2 * x1
    ys = (1 - ts) ** 2 * y0 + 2 * (1 - ts) * ts * cy + ts ** 2 * y1
    return list(zip(xs, ys))

def poly_path(pts, upto=1.0):
    pts = list(pts)
    if upto <= 0 or len(pts) < 2: return None, pts[0]
    seg = np.array([math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])
    L = seg.sum() * upto
    p = skia.Path(); p.moveTo(*pts[0]); acc = 0; end = pts[0]
    for i, d in enumerate(seg):
        if acc + d >= L:
            f = (L - acc) / d if d else 0
            end = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)
            p.lineTo(*end); return p, end
        p.lineTo(*pts[i + 1]); acc += d; end = pts[i + 1]
    return p, end

def arc(c, p0, p1, prog, a, color, t, dashed=True, width=3.0, head=True, bend=0.22):
    if a <= 0.003 or prog <= 0: return None
    path, end = poly_path(bezier_pts(p0, p1, bend), prog)
    if path is None: return None
    c.drawPath(path, glow_line_paint(color, a * 0.55, width * 3, blur=5))
    p = glow_line_paint(color, a, width)
    if dashed: p.setPathEffect(skia.DashPathEffect.Make([14, 9], -t * 60))
    c.drawPath(path, p)
    if head and prog < 1:
        radial_glow(c, end[0], end[1], 26, WHITE, a * 0.9)
        c.drawCircle(end[0], end[1], 4.5, skia.Paint(AntiAlias=True, Color=col(255, 255, 255, a)))
    return end

# ---------------------------------------------------------------- media frames
class Frame:
    """Floating media window linked to a map anchor by an animated elbow connector."""
    def __init__(self, src, tin, tout, rects, anchor=None, conn_t=None, caption=None, cap_t=None, media_t0=None,
                 card=False, keyed=False, accent=CYAN, freeze_after=None):
        self.src, self.tin, self.tout = src, tin, tout
        self.rects = rects          # [(t, cx, cy, w)] keyframes in screen space
        self.anchor, self.conn_t = anchor, (conn_t if conn_t is not None else tin)
        self.caption, self.cap_t = caption, (cap_t if cap_t is not None else tin + 0.5)
        self.media_t0 = media_t0 if media_t0 is not None else tin
        self.card, self.keyed, self.accent = card, keyed, accent
    def rect_at(self, t):
        r = self.rects
        if t <= r[0][0]: cx, cy, w = r[0][1:]
        else:
            cx, cy, w = r[-1][1:]
            for (ta, *A), (tb, *B) in zip(r, r[1:]):
                if ta <= t < tb:
                    p = eio((t - ta) / min(1.0, tb - ta)) if tb - ta > 0 else 1
                    cx, cy, w = (lerp(a, b, p) for a, b in zip(A, B)); break
        h = w / self.src.aspect
        if self.card:
            h = w / self.src.aspect
        return cx, cy, w, h
    def draw(self, c, t, view):
        if t < min(self.tin, self.conn_t) or t >= self.tout: return
        cx, cy, w, h = self.rect_at(t)
        fl = math.sin(t * 0.9 + self.tin) * 5
        cy += fl
        pad = 18 if self.card else 0
        L, T, R, B = cx - w / 2 - pad, cy - h / 2 - pad, cx + w / 2 + pad, cy + h / 2 + pad
        out = clamp((t - (self.tout - 0.4)) / 0.4)
        # connector
        if self.anchor is not None and t >= self.conn_t:
            ax, ay = view.scr(self.anchor)
            cp = eout((t - self.conn_t) / 0.45) * (1 - eio(out))
            ex = L if ax < L else R if ax > R else cx
            ey = clamp(ay, T + 30, B - 30) if ex != cx else (T if ay < T else B)
            if ex != cx:
                kx = ex - 70 if ex == L else ex + 70
                pts = [(ax, ay), (kx, ey), (ex, ey)]
            else:
                pts = [(ax, ay), (ex, ey)]
            path, end = poly_path(pts, cp)
            if path is not None:
                c.drawPath(path, glow_line_paint(self.accent, 0.5 * (1 - out), 7, blur=5))
                c.drawPath(path, glow_line_paint(self.accent, 1 - out, 2.4))
                c.drawCircle(ax, ay, 5, skia.Paint(AntiAlias=True, Color=col(*self.accent, 1 - out)))
                c.drawCircle(end[0], end[1], 5, skia.Paint(AntiAlias=True, Color=col(255, 255, 255, 1 - out)))
                if cp >= 1:   # data pulse travelling along the connector
                    ph = ((t - self.conn_t) * 0.8) % 1.0
                    _, pe = poly_path(pts, ph)
                    radial_glow(c, pe[0], pe[1], 16, WHITE, 0.8 * (1 - out))
        if t < self.tin: return
        # window open / close
        op = eback((t - self.tin) / 0.5)
        a = clamp((t - self.tin) / 0.25) * (1 - eio(out))
        sc = lerp(0.6, 1.0, clamp(op, 0, 1.2)) * lerp(1, 0.85, eio(out))
        if a <= 0.003: return
        c.save()
        c.translate(cx, cy); c.scale(sc, sc); c.translate(-cx, -cy)
        rr = skia.Rect(L, T, R, B)
        # shadow
        c.drawRRect(skia.RRect.MakeRectXY(rr.makeOffset(0, 14), 8, 8),
                    skia.Paint(AntiAlias=True, Color=col(0, 0, 0, 0.6 * a),
                               MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22)))
        c.saveLayerAlpha(None, int(255 * a))
        if self.card:
            c.drawRRect(skia.RRect.MakeRectXY(rr, 8, 8), skia.Paint(AntiAlias=True, Color=col(255, 255, 255)))
        elif self.keyed:
            sh = skia.GradientShader.MakeRadial(skia.Point(cx, cy), w * 0.7, [col(22, 52, 84), col(6, 16, 30)])
            c.drawRRect(skia.RRect.MakeRectXY(rr, 6, 6), skia.Paint(AntiAlias=True, Shader=sh))
            gp = glow_line_paint(CYAN, 0.10, 1)
            c.save(); c.clipRect(rr)
            off = (t * 140) % 48
            for gx in np.arange(L - 48 + (48 - off), R + 48, 48): c.drawLine(gx, T, gx, B, gp)
            for gy in np.arange(T, B, 48): c.drawLine(L, gy, R, gy, gp)
            # speed streaks behind the airframe
            for k in range(7):
                sy = T + h * (0.18 + 0.1 * k)
                sx = R - ((t * 900 + k * 233) % (w * 1.6))
                c.drawLine(sx, sy, sx + 120, sy, glow_line_paint(WHITE, 0.10, 1.4))
            c.restore()
        else:
            c.drawRRect(skia.RRect.MakeRectXY(rr, 6, 6), skia.Paint(AntiAlias=True, Color=col(0, 0, 0)))
        img = self.src.image(t - self.media_t0)
        ir = skia.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if self.keyed:   # gentle flight motion of the cut-out airframe
            c.save(); c.translate(cx, cy); c.rotate(math.sin(t * 1.3) * 1.6); c.translate(-cx, -cy + math.sin(t * 2.1) * 6)
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(rr, 6, 6), skia.ClipOp.kIntersect, True)
        c.drawImageRect(img, ir, skia.SamplingOptions(skia.CubicResampler.Mitchell()))
        c.restore()
        if self.keyed: c.restore()
        c.restore()  # layer
        # border, corner brackets
        c.drawRRect(skia.RRect.MakeRectXY(rr, 6, 6), glow_line_paint(self.accent, 0.45 * a, 6, blur=6))
        c.drawRRect(skia.RRect.MakeRectXY(rr, 6, 6), glow_line_paint(self.accent, 0.9 * a, 1.6))
        bl = 26
        bp = glow_line_paint(WHITE, a, 3.5)
        for (x, y, sx, sy) in [(L, T, 1, 1), (R, T, -1, 1), (L, B, 1, -1), (R, B, -1, -1)]:
            x -= sx * 7; y -= sy * 7
            c.drawLine(x, y, x + sx * bl, y, bp); c.drawLine(x, y, x, y + sy * bl, bp)
        # light sweep on open
        sw = clamp((t - self.tin - 0.15) / 0.7)
        if 0 < sw < 1:
            c.save(); c.clipRRect(skia.RRect.MakeRectXY(rr, 6, 6), skia.ClipOp.kIntersect, True)
            sxp = lerp(L - w * 0.4, R + w * 0.4, eio(sw))
            sh = skia.GradientShader.MakeLinear([skia.Point(sxp - 90, T), skia.Point(sxp + 90, B)],
                                               [col(255, 255, 255, 0), col(255, 255, 255, 0.28), col(255, 255, 255, 0)])
            c.drawRect(rr, skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kPlus))
            c.restore()
        c.restore()
        # caption bar (screen space so it never scales oddly)
        if self.caption and t >= self.cap_t:
            ca = eout((t - self.cap_t) / 0.4) * (1 - eio(out))
            img = text_img(self.caption, 30, 'B')
            bw = max(img.width() + 44, 0)
            bh = 54
            bx1 = cx + (w / 2 + pad) * sc
            bx0 = bx1 - bw * eout((t - self.cap_t) / 0.45)
            by = cy + (h / 2 + pad) * sc + 12
            c.save(); c.clipRect(skia.Rect(bx0, by, bx1, by + bh))
            c.drawRect(skia.Rect(bx1 - bw, by, bx1, by + bh), skia.Paint(Color=col(4, 14, 26, 0.9 * ca)))
            c.drawRect(skia.Rect(bx1 - 7, by, bx1, by + bh), skia.Paint(Color=col(*AMBER, ca)))
            c.drawImage(img, bx1 - 20 - img.width(), by + (bh - img.height()) / 2,
                        skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(Alphaf=ca))
            c.restore()

# ---------------------------------------------------------------- timeline (audio-time seconds)
CAM = Camera([
    (-1.5, 0.1, 44.0, 33.2, 62, W / 2, H / 2),
    (-1.4, 2.4, 44.2, 33.9, 80, W / 2, H / 2),
    (0.4, 2.0, 44.6, 34.9, 125, W / 2, H / 2),
    (2.5, 1.5, *KM, 430, 840, 600),
    (5.3, 1.3, 45.05, 35.45, 255, 900, 540),
    (6.5, 1.3, *KM, 380, 700, 560),
    (10.4, 2.0, *KM, 330, 760, 570),
    (12.5, 1.6, 44.6, 35.95, 238, 1130, 540),
    (17.4, 1.4, *KM, 400, 1200, 620),
    (21.7, 1.6, *ERBIL, 300, 1000, 430),
    (28.7, 1.6, 44.6, 35.95, 238, 1000, 540),
    (33.1, 1.5, *KM, 270, 1060, 540),
    (35.9, 2.0, 44.3, 34.7, 180, 1030, 560),
    (44.2, 1.4, 45.7, 34.3, 118, W / 2, H / 2),
    (45.2, 1.8, *BAGHDAD, 172, 700, 820),
    (55.4, 1.6, *KM, 380, W / 2, 540),
    (58.6, 1.2, *KM, 450, 1000, 560),
    (64.8, 1.8, 44.4, 35.05, 215, W / 2, 560),
    (69.5, 2.2, 43.75, 33.25, 108, 780, 560),
])

FRAMES = [
    Frame(M['drone_side'], 0.75, 4.5, [(0, 1450, 330, 560)], anchor=KM, conn_t=2.75, keyed=True, accent=RED),
    Frame(M['k1'], 6.9, 12.3, [(6.9, 1330, 560, 330), (8.0, 1330, 540, 430), (10.3, 1330, 540, 430),
                               (11.3, 1330, 560, 330)], anchor=KM, conn_t=6.6, media_t0=6.9, accent=ORANGE),
    Frame(DANA, 17.75, 21.8, [(0, 560, 430, 250)], anchor=KM, conn_t=17.55, card=True, caption='دانة غاز',
          cap_t=18.3),
    Frame(MOE, 22.3, 28.75, [(0, 470, 320, 400)], anchor=ERBIL, conn_t=22.0, card=True,
          caption='وزارة الكهرباء - إقليم كردستان', cap_t=22.9),
    Frame(M['launch'], 38.7, 42.4, [(0, 440, 300, 500)], anchor=SD_LAUNCH, conn_t=38.5, media_t0=38.7,
          accent=AMBER),
    Frame(M['pm1'], 47.0, 55.45, [(47.0, 1390, 470, 760), (48.4, 1360, 470, 840), (52.6, 1360, 470, 840),
                                  (53.6, 1390, 470, 780)], anchor=BAGHDAD, conn_t=46.7,
          caption='رئيس الوزراء علي الزيدي', cap_t=47.95, media_t0=47.0),
    Frame(M['k2b'], 60.3, 62.4, [(0, 1450, 520, 330)], anchor=KM, conn_t=60.1, media_t0=60.3, accent=ORANGE),
    Frame(M['drone_front'], 62.2, 64.95, [(0, 1420, 520, 580)], anchor=KM, conn_t=62.2, keyed=True, accent=RED),
    Frame(M['pm2'], 71.4, 999, [(0, 1500, 300, 600)], anchor=BAGHDAD, conn_t=71.2, caption='حكومة الزيدي',
          cap_t=71.8, media_t0=71.4),
]

# ---------------------------------------------------------------- frame render
_noise = [skia.Image.fromarray(np.ascontiguousarray(np.dstack([np.random.RandomState(i).randint(0, 255, (H // 2, W // 2), np.uint8)] * 3 +
                               [np.full((H // 2, W // 2), 255, np.uint8)])), colorType=skia.ColorType.kRGBA_8888_ColorType)
          for i in range(4)]

def vignette(c):
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.72,
                                        [col(0, 0, 0, 0), col(0, 0, 0, 0.18), col(0, 0, 0, 0.72)], [0.45, 0.7, 1.0])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))

def gov_fill(c, view, name_or_path, color, a, outline=True):
    if a <= 0.003: return
    path = P_GOV[name_or_path] if isinstance(name_or_path, str) else name_or_path
    s = view.s
    c.save(); c.concat(view.matrix())
    c.drawPath(path, skia.Paint(AntiAlias=True, Color=col(*color, 0.22 * a)))
    if outline:
        c.drawPath(path, glow_line_paint(color, 0.6 * a, 6 / s, blur=5 / s))
        c.drawPath(path, glow_line_paint(color, 0.95 * a, 2.0 / s))
    c.restore()

def render(fi, c):
    t = fi / FPS - T0                          # audio time
    tc = min(t, SPEECH_END)                    # camera frozen during the final hold
    cx, cy, s = CAM.at(tc)
    drift = 1 + 0.012 * math.sin(tc * 0.33)
    v = View(cx + 0.35 * math.sin(tc * 0.21) / s, cy + 0.25 * math.cos(tc * 0.17) / s, s * drift)
    intro = eout((t + 1.5) / 1.4)

    # background
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=col(3, 8, 15)))
    sh = skia.GradientShader.MakeRadial(skia.Point(W * 0.55, H * 0.45), W * 0.8, [col(14, 34, 58), col(3, 8, 15)])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh, Alphaf=intro))

    c.save(); c.concat(v.matrix())
    S = v.s
    c.drawPath(P_GRAT, glow_line_paint((70, 130, 190), 0.10 * intro, 1.0 / S))
    # neighbours
    for k, p in P_NEIGH.items():
        c.drawPath(p, skia.Paint(AntiAlias=True, Color=col(13, 28, 45, intro)))
        c.drawPath(p, glow_line_paint((48, 88, 128), 0.85 * intro, 1.2 / S))
    # Iran accent ("loyal to Iran")
    ia = env(t, 44.56, 45.6, 0.5, 0.5)
    if ia:
        c.drawPath(P_NEIGH['IRN'], skia.Paint(AntiAlias=True, Color=col(*RED, 0.09 * ia)))
        c.drawPath(P_NEIGH['IRN'], glow_line_paint(RED, 0.8 * ia, 2.0 / S))
    # Iraq
    c.drawPath(P_IRQ, skia.Paint(AntiAlias=True, Color=col(16, 42, 68, intro)))
    c.drawPoints(skia.Canvas.kPoints_PointMode, IRQ_DOTS,
                 skia.Paint(AntiAlias=True, Color=col(90, 170, 230, 0.16 * intro), StrokeWidth=2.2 / S,
                            StrokeCap=skia.Paint.kRound_Cap))
    for k, p in P_GOV.items():
        c.drawPath(p, glow_line_paint((70, 140, 200), 0.32 * intro, 1.0 / S))
    c.drawPath(P_RIV, glow_line_paint((40, 120, 200), 0.55 * intro, 1.6 / S))
    krg_a = 0.35 * intro
    c.drawPath(P_KRG, skia.Paint(AntiAlias=True, Color=col(30, 90, 120, 0.25 * intro)))
    # Iraq border: draw-on during intro, brighter at the end
    trim = eio((t + 1.3) / 1.9)
    end_glow = env(t, 69.6, 1e9, 1.5)
    bp = glow_line_paint(CYAN, (0.55 + 0.4 * end_glow) * intro, (8 + 6 * end_glow) / S, blur=(6 + 4 * end_glow) / S)
    bp2 = glow_line_paint(CYAN, intro, 2.2 / S)
    if trim < 1:
        bp.setPathEffect(skia.TrimPathEffect.Make(0, trim)); bp2.setPathEffect(skia.TrimPathEffect.Make(0, trim))
    c.drawPath(P_IRQ, bp); c.drawPath(P_IRQ, bp2)
    c.restore()

    # region highlights
    gov_fill(c, v, 'As-Sulaymaniyah', AMBER, env(t, 5.76, 6.9, 0.5, 0.6))
    krg = max(env(t, 16.42, 17.9, 0.5, 0.5), 0.6 * env(t, 23.3, 33.2, 0.6, 0.8), env(t, 52.2, 55.5, 0.5, 0.5))
    gov_fill(c, v, P_KRG, CYAN, krg)
    sd = max(env(t, 38.7, 45.3, 0.5, 0.6), env(t, 68.34, 69.9, 0.4, 0.6))
    gov_fill(c, v, 'Sala ad-Din', ORANGE, sd)
    gov_fill(c, v, "At-Ta'mim", AMBER, env(t, 67.76, 69.9, 0.4, 0.6))
    if t >= 30.26:   # blackout: the region dims
        dim = env(t, 30.26, 33.3, 1.2, 0.6)
        c.save(); c.concat(v.matrix())
        c.drawPath(P_KRG, skia.Paint(AntiAlias=True, Color=col(0, 0, 0, 0.45 * dim)))
        c.restore()

    # country labels (subtle)
    ca = intro * (1 - 0.6 * clamp((v.s - 120) / 120))
    for name, ll in [('إيران', (48.6, 32.9)), ('تركيا', (38.5, 38.4)), ('سوريا', (38.7, 35.1)),
                     ('السعودية', (43.0, 28.0)), ('الأردن', (37.0, 31.0)), ('الكويت', (47.7, 29.3))]:
        x, y = v.scr(ll)
        aa = ca * (0.42 + 0.58 * (name == 'إيران') * ia)
        draw_text(c, name, 34 if not (name == 'إيران' and ia) else 44, x, y, 'M',
                  (255, 160, 150) if (name == 'إيران' and ia) else (150, 180, 210), aa, 'cc')
    x, y = v.scr((43.4, 32.6))
    draw_text(c, 'العراق', 40, x, y, 'B', (170, 205, 235), 0.5 * intro * (1 - env(t, 69.0, 1e9, 1.0))
              * (1 - clamp((v.s - 100) / 60)), 'cc')

    # ---------------- energy network (Khor Mor feeds ~80% of KRG power)
    kx, ky = v.scr(KM)
    net_a = max(env(t, 13.24, 17.7, 0.4, 0.5), env(t, 22.4, 33.2, 0.6, 0.6))
    if net_a:
        lost = clamp((t - 24.84) / 1.2) if t > 22 else 0
        for i, cty in enumerate(KRG_CITIES):
            x, y = v.scr(cty)
            grow = clamp((t - (13.24 if t < 20 else 22.4) - i * 0.08) / 0.8)
            colr = tuple(int(lerp(a, b, lost)) for a, b in zip(AMBER, RED))
            flick = 1.0
            if lost > 0: flick = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 40 + i * 3)) ** 4 * (1 - lost) + 0.25 * (1 - lost)
            arc(c, (kx, ky), (x, y), eout(grow), net_a * flick * (1 - 0.6 * lost), colr, t, dashed=True, width=2.2,
                head=True, bend=0.12)
        for i, cty in enumerate(KRG_CITIES):
            x, y = v.scr(cty)
            on = 1.0
            if t >= 30.26:
                k = (t - 30.26) * 6 + i * 1.7
                on = 0 if (t - 30.26) > 0.25 + (i % 5) * 0.28 else (1 if math.sin(k * 7) > 0 else 0.2)
            ap = net_a * clamp((t - (13.6 if t < 20 else 22.6) - i * 0.08) / 0.4)
            radial_glow(c, x, y, 30, (255, 220, 120), 0.7 * ap * on)
            c.drawCircle(x, y, 5, skia.Paint(AntiAlias=True, Color=col(255, 236, 170, ap * (0.25 + 0.75 * on))))
            if on == 0:
                c.drawCircle(x, y, 9, glow_line_paint(RED, ap * 0.8, 1.6))

    # 80% card
    pa = env(t, 13.86, 17.6, 0.5, 0.45)
    if pa:
        bx, by, bw, bh = 140, 360, 420, 330
        ex, ey = bx + bw, by + bh / 2
        cp = eout((t - 13.6) / 0.45) * (1 - ein(clamp((t - 17.2) / 0.4)))
        path, end = poly_path([(kx, ky), (ex + 70, ey), (ex, ey)], cp)
        if path is not None:
            c.drawPath(path, glow_line_paint(CYAN, 0.5 * pa, 7, blur=5)); c.drawPath(path, glow_line_paint(CYAN, pa, 2.4))
        c.save(); c.translate(bx + bw / 2, by + bh / 2); sc = lerp(0.8, 1, eback((t - 13.86) / 0.5)); c.scale(sc, sc)
        c.translate(-(bx + bw / 2), -(by + bh / 2))
        r = skia.Rect(bx, by, bx + bw, by + bh)
        c.drawRRect(skia.RRect.MakeRectXY(r, 10, 10), skia.Paint(AntiAlias=True, Color=col(4, 14, 26, 0.88 * pa)))
        c.drawRRect(skia.RRect.MakeRectXY(r, 10, 10), glow_line_paint(CYAN, 0.8 * pa, 1.6))
        gx, gy, gr = bx + bw / 2, by + 140, 100
        c.drawArc(skia.Rect(gx - gr, gy - gr, gx + gr, gy + gr), 0, 360, False, glow_line_paint((40, 70, 100), pa, 16))
        val = 80 * eio((t - 13.86) / 1.1)
        c.drawArc(skia.Rect(gx - gr, gy - gr, gx + gr, gy + gr), -90, 360 * val / 100, False,
                  glow_line_paint(AMBER, 0.5 * pa, 26, blur=8))
        c.drawArc(skia.Rect(gx - gr, gy - gr, gx + gr, gy + gr), -90, 360 * val / 100, False, glow_line_paint(AMBER, pa, 16))
        draw_text(c, f'{int(round(val))}%', 64, gx, gy, 'B', WHITE, pa, 'cc', rtl=False)
        sa = pa * eout((t - 15.0) / 0.5)
        draw_text(c, 'من إنتاج الكهرباء', 30, gx, by + 268, 'M', WHITE, sa, 'cc')
        draw_text(c, 'في إقليم كردستان', 30, gx, by + 304, 'B', AMBER, pa * eout((t - 16.42) / 0.5), 'cc')
        c.restore()

    # Dana Gas: production suspended
    da = env(t, 19.1, 21.8, 0.4, 0.4)
    if da:
        img = text_img('تعليق الإنتاج', 28, 'B')
        cw = img.width() + 66
        x1 = 560 + 125 + 18
        x0 = x1 - cw * eout((t - 19.1) / 0.4)
        yy = 655
        c.save(); c.clipRect(skia.Rect(x0, yy, x1, yy + 50))
        rr = skia.Rect(x1 - cw, yy, x1, yy + 50)
        c.drawRRect(skia.RRect.MakeRectXY(rr, 25, 25), skia.Paint(AntiAlias=True, Color=col(60, 8, 8, 0.9 * da)))
        c.drawRRect(skia.RRect.MakeRectXY(rr, 25, 25), glow_line_paint(RED, da, 1.8))
        bl = 0.5 + 0.5 * math.sin(t * 6)
        for k in range(2):
            c.drawRect(skia.Rect(x1 - 38 + k * 10, yy + 15, x1 - 32 + k * 10, yy + 35),
                       skia.Paint(Color=col(*RED, da * (0.6 + 0.4 * bl))))
        c.drawImage(img, x1 - 52 - img.width(), yy + (50 - img.height()) / 2,
                    skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(Alphaf=da))
        c.restore()

    # power-loss gauge under the ministry card
    ga = env(t, 24.6, 28.75, 0.4, 0.4)
    if ga:
        bx, by, bw = 270, 560, 400
        drop = eio((t - 24.84) / 1.4)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx - 12, by - 12, bx + bw + 12, by + 44), 8, 8),
                    skia.Paint(AntiAlias=True, Color=col(4, 14, 26, 0.88 * ga)))
        c.drawRect(skia.Rect(bx, by, bx + bw, by + 32), skia.Paint(Color=col(40, 60, 80, ga)))
        fillw = bw * lerp(1.0, 0.22, drop)
        colr = tuple(int(lerp(a, b, drop)) for a, b in zip(AMBER, RED))
        c.drawRect(skia.Rect(bx + bw - fillw, by, bx + bw, by + 32), skia.Paint(Color=col(*colr, ga)))
        radial_glow(c, bx + bw - fillw, by + 16, 40, colr, 0.6 * ga)
        # lightning glyph
        p = skia.Path(); ox, oy = bx - 50, by - 6
        for i, (x, y) in enumerate([(14, 0), (2, 24), (12, 24), (6, 44), (24, 16), (13, 16), (20, 0)]):
            (p.moveTo if i == 0 else p.lineTo)(ox + x, oy + y)
        p.close()
        c.drawPath(p, skia.Paint(AntiAlias=True, Color=col(*colr, ga)))

    # radar sweep: "where did the drone come from?"
    ra = env(t, 33.3, 36.4, 0.5, 0.6)
    if ra:
        R = 260
        for k in (0.35, 0.7, 1.0):
            c.drawCircle(kx, ky, R * k, glow_line_paint(CYAN, 0.35 * ra, 1.2))
        c.drawLine(kx - R, ky, kx + R, ky, glow_line_paint(CYAN, 0.2 * ra, 1))
        c.drawLine(kx, ky - R, kx, ky + R, glow_line_paint(CYAN, 0.2 * ra, 1))
        ang = (t * 160) % 360
        sh = skia.GradientShader.MakeSweep(kx, ky, [col(*CYAN, 0), col(*CYAN, 0), col(*CYAN, 0.45)], [0, 0.82, 1.0])
        c.save(); c.translate(kx, ky); c.rotate(ang); c.translate(-kx, -ky)
        c.drawCircle(kx, ky, R, skia.Paint(AntiAlias=True, Shader=sh, Alphaf=ra))
        c.restore()

    # launch trajectory from Salah al-Din (media reports)
    def strike(p_from, t_start, dur, colr, a_env, bend=0.25):
        x0, y0 = v.scr(p_from)
        prog = eio((t - t_start) / dur)
        end = arc(c, (x0, y0), (kx, ky), prog, a_env, colr, t, dashed=True, width=3, head=True, bend=bend)
        c.drawCircle(x0, y0, 6, skia.Paint(AntiAlias=True, Color=col(*colr, a_env * clamp((t - t_start) / 0.3))))
        if prog >= 1:
            hit = (t - t_start - dur)
            if hit < 0.8:
                radial_glow(c, kx, ky, 40 + hit * 160, (255, 200, 120), (1 - hit / 0.8) * a_env)
                c.drawCircle(kx, ky, 20 + hit * 120, glow_line_paint(WHITE, (1 - hit / 0.8) * a_env, 3))
    tra = env(t, 39.6, 45.4, 0.3, 0.6)
    if tra: strike(SD_LAUNCH, 39.7, 1.3, ORANGE, tra, bend=-0.3)

    # armed groups, loyal to Iran
    ga2 = env(t, 42.28, 45.4, 0.4, 0.6)
    if ga2:
        for i, pt in enumerate(ARMED_PTS):
            x, y = v.scr(pt)
            ap = ga2 * clamp((t - 42.28 - i * 0.12) / 0.3)
            ph = ((t + i * 0.37) / 1.2) % 1
            c.drawCircle(x, y, 6 + ph * 22, glow_line_paint(RED, ap * (1 - ph), 2))
            c.drawRect(skia.Rect(x - 5, y - 5, x + 5, y + 5), skia.Paint(AntiAlias=True, Color=col(*RED, ap)))
        x, y = v.scr((43.75, 34.45))
        label_pill(c, 'جماعات مسلحة', x, y, ga2, 32, 'B', RED, side='l')
        if ia:
            x0, y0 = v.scr(IRAN_PT); x1, y1 = v.scr((44.25, 34.62))
            arc(c, (x0, y0), (x1, y1), eio((t - 44.6) / 0.8), ia * 0.9, RED, t, dashed=True, width=2.4, head=True,
                bend=0.2)

    # joint investigation committee: Baghdad <-> KRG
    ja = env(t, 50.0, 55.5, 0.4, 0.5)
    if ja:
        bx_, by_ = v.scr(BAGHDAD); ex_, ey_ = v.scr(ERBIL)
        arc(c, (bx_, by_), (ex_, ey_), eio((t - 50.1) / 1.0), ja, CYAN, t, dashed=True, width=3, head=True, bend=0.18)
        arc(c, (ex_, ey_), (bx_, by_), eio((t - 50.6) / 1.0), ja * 0.8, AMBER, -t, dashed=True, width=2,
            head=True, bend=0.18)
        marker(c, ex_, ey_, t, CYAN, ja * clamp((t - 51.0) / 0.3))

    # 12+ attacks
    ca12 = env(t, 59.3, 65.0, 0.45, 0.45)
    if ca12:
        n = int(clamp((t - 59.3) / 1.2) * 12)
        rs = np.random.RandomState(7)
        for i in range(12):
            ang = rs.uniform(0, 2 * math.pi); rd = rs.uniform(30, 120)
            x, y = kx + math.cos(ang) * rd, ky + math.sin(ang) * rd * 0.8
            ti = 59.3 + i * 0.1
            if t < ti: continue
            hit = t - ti
            if hit < 0.6:
                radial_glow(c, x, y, 20 + hit * 80, (255, 190, 110), (1 - hit / 0.6) * ca12)
            xa = ca12 * 0.9
            p = glow_line_paint(RED, xa, 2.6)
            c.drawLine(x - 7, y - 7, x + 7, y + 7, p); c.drawLine(x - 7, y + 7, x + 7, y - 7, p)
        bx, by, bw, bh = 160, 330, 400, 380
        ex, ey = bx + bw, by + bh / 2
        cp = eout((t - 59.1) / 0.45) * (1 - ein(clamp((t - 64.6) / 0.4)))
        path, end = poly_path([(kx, ky), (ex + 80, ey), (ex, ey)], cp)
        if path is not None:
            c.drawPath(path, glow_line_paint(RED, 0.5 * ca12, 7, blur=5)); c.drawPath(path, glow_line_paint(RED, ca12, 2.4))
        r = skia.Rect(bx, by, bx + bw, by + bh)
        c.drawRRect(skia.RRect.MakeRectXY(r, 10, 10), skia.Paint(AntiAlias=True, Color=col(4, 14, 26, 0.9 * ca12)))
        c.drawRRect(skia.RRect.MakeRectXY(r, 10, 10), glow_line_paint(RED, 0.8 * ca12, 1.6))
        draw_text(c, 'أكثر من', 32, bx + bw / 2, by + 52, 'M', (200, 215, 230), ca12, 'cc')
        draw_text(c, f'{n}', 120, bx + bw / 2, by + 145, 'K', WHITE, ca12, 'cc', rtl=False, glow=10)
        draw_text(c, 'هجوماً', 38, bx + bw / 2, by + 228, 'B', AMBER, ca12 * eout((t - 60.28) / 0.4), 'cc')
        for i, (txt, tt) in enumerate([('صواريخ', 61.18), ('طائرات مسيّرة', 62.16)]):
            a_ = ca12 * eout((t - tt) / 0.4)
            if a_ <= 0: continue
            img = text_img(txt, 28, 'M')
            cw = img.width() + 30
            cx_ = bx + bw / 2 + (cw / 2 + 8 if i == 0 else -cw / 2 - 8) if False else bx + bw / 2
            yy = by + 285 + i * 0
            if i == 0: x0 = bx + bw - 30 - cw
            else: x0 = bx + 30
            rr = skia.Rect(x0, yy, x0 + cw, yy + 48)
            c.drawRRect(skia.RRect.MakeRectXY(rr, 24, 24), skia.Paint(AntiAlias=True, Color=col(*RED, 0.22 * a_)))
            c.drawRRect(skia.RRect.MakeRectXY(rr, 24, 24), glow_line_paint(RED, a_, 1.6))
            c.drawImage(img, x0 + 15, yy + (48 - img.height()) / 2, skia.SamplingOptions(skia.FilterMode.kLinear),
                        skia.Paint(Alphaf=a_))
        if t >= 63.28:   # "over past years" timeline ticks
            ya = ca12 * eout((t - 63.28) / 0.5)
            for i in range(6):
                xx = bx + 40 + i * (bw - 80) / 5
                c.drawCircle(xx, by + bh + 26, 5, skia.Paint(AntiAlias=True, Color=col(*AMBER, ya)))
            c.drawLine(bx + 40, by + bh + 26, bx + 40 + (bw - 80) * eio((t - 63.28) / 0.9), by + bh + 26,
                       glow_line_paint(AMBER, ya, 2))

    # launches from Kirkuk and Salah al-Din
    ma = env(t, 67.8, 70.6, 0.3, 0.8)
    if ma:
        for i, pt in enumerate(KIR_PTS): strike(pt, 67.9 + i * 0.15, 0.9, AMBER, ma, bend=0.25 - 0.1 * i)
        for i, pt in enumerate(SD_PTS): strike(pt, 68.45 + i * 0.15, 0.9, ORANGE, ma, bend=-0.25 + 0.1 * i)

    # energy-protection shield
    sa_ = env(t, 72.36, 1e9, 0.8)
    if sa_:
        R = 70
        p = skia.Path()
        for k in range(6):
            ang = math.radians(60 * k + t * 12)
            (p.moveTo if k == 0 else p.lineTo)(kx + R * math.cos(ang), ky + R * math.sin(ang))
        p.close()
        c.drawPath(p, skia.Paint(AntiAlias=True, Color=col(*CYAN, 0.12 * sa_)))
        c.drawPath(p, glow_line_paint(CYAN, 0.6 * sa_, 8, blur=6)); c.drawPath(p, glow_line_paint(CYAN, sa_, 2.2))

    # ---------------- markers & labels
    fire = env(t, 6.5, 12.6, 0.5, 0.8)
    if fire:
        fl = 0.75 + 0.25 * math.sin(t * 23) * math.sin(t * 7.3)
        radial_glow(c, kx, ky, 150, (255, 110, 30), 0.55 * fire * fl)
        radial_glow(c, kx, ky, 60, (255, 220, 140), 0.6 * fire * fl)
    km_a = clamp((t - 2.6) / 0.35) * (1 - env(t, 45.4, 55.7, 0.5, 0.6))
    km_col = RED if (t < 13 or 58 < t < 70.5 or 33 < t < 45.5) else AMBER
    marker(c, kx, ky, t, km_col, km_a, big=True, t0=2.6)
    lab_a = km_a * (1 - env(t, 13.3, 17.5, 0.4, 0.4) * 0.0)
    km_side = 'l' if kx > 1300 or (12.5 < t < 21.5) or (58.5 < t < 65) else 'r'
    if 33.2 < t < 46: km_side = 'r'
    label_pill(c, 'حقل كورمور', kx, ky, lab_a * (1 - env(t, 12.6, 17.6, 0.4, 0.4) * 0.0), 32, 'B', km_col,
               side=km_side, dy=-58 if km_side == 'r' else -58)
    cha = env(t, 4.3, 6.6, 0.4, 0.4)
    if cha:
        x, y = v.scr(CHAM)
        marker(c, x, y, t, AMBER, cha)
        label_pill(c, 'جمجمال', x, y, cha, 28, 'M', AMBER, side='r')
    sla = env(t, 5.76, 6.9, 0.4, 0.5)
    if sla:
        x, y = v.scr((45.55, 35.95))
        draw_text(c, 'محافظة السليمانية', 40, x, y, 'B', (255, 220, 160), sla, 'cc', glow=8)
    kra = max(env(t, 16.42, 17.7, 0.4, 0.4), env(t, 52.2, 55.5, 0.4, 0.4))
    if kra:
        x, y = v.scr((44.2, 36.75))
        draw_text(c, 'إقليم كردستان', 42, x, y, 'B', (180, 235, 255), kra, 'cc', glow=8)
    era = env(t, 22.0, 28.8, 0.35, 0.4)
    if era:
        x, y = v.scr(ERBIL); marker(c, x, y, t, CYAN, era)
    sda = env(t, 38.5, 45.3, 0.35, 0.5)
    if sda:
        x, y = v.scr(SD_LAUNCH); marker(c, x, y, t, ORANGE, sda)
        x, y = v.scr((43.55, 34.15))
        draw_text(c, 'محافظة صلاح الدين', 38, x, y, 'B', (255, 200, 150), sda * clamp((t - 38.7) / 0.4), 'cc', glow=8)
    kka = env(t, 67.76, 70.0, 0.4, 0.6)
    if kka:
        x, y = v.scr((44.0, 35.85)); draw_text(c, 'كركوك', 40, x, y, 'B', (255, 220, 150), kka, 'cc', glow=8)
    s2 = env(t, 68.34, 70.0, 0.4, 0.6)
    if s2:
        x, y = v.scr((43.55, 34.2)); draw_text(c, 'صلاح الدين', 40, x, y, 'B', (255, 200, 150), s2, 'cc', glow=8)
    bga = max(env(t, 46.1, 55.5, 0.4, 0.5), env(t, 71.2, 1e9, 0.4))
    if bga:
        x, y = v.scr(BAGHDAD); marker(c, x, y, t, CYAN, bga)
        label_pill(c, 'بغداد', x, y, max(env(t, 46.1, 55.5, 0.4, 0.5), env(t, 71.2, 1e9, 0.4)), 32, 'B', CYAN,
                   side='l')
    iqa = env(t, 74.52, 1e9, 0.6)
    if iqa:
        x, y = v.scr((41.4, 33.0))
        draw_text(c, 'العراق', 76, x, y, 'K', (210, 240, 255), iqa, 'cc', glow=14)

    # ---------------- media frames
    for f in FRAMES: f.draw(c, t, v)

    # ---------------- finishing
    vignette(c)
    c.drawImageRect(_noise[fi % 4], skia.Rect(0, 0, W, H), skia.SamplingOptions(),
                    skia.Paint(Alphaf=0.035, BlendMode=skia.BlendMode.kOverlay))
    if t < -1.0:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=col(0, 0, 0, 1 - (t + 1.5) / 0.5)))


def stills(times):
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    os.makedirs('stills', exist_ok=True)
    import time
    for ts in times:
        fi = int(round((float(ts) + T0) * FPS))
        t0 = time.time()
        with surf as c: render(fi, c)
        Image.fromarray(arr[..., :3].copy()).save(f'stills/s_{ts}.png')
        print(ts, f'{time.time() - t0:.2f}s', flush=True)


def main():
    if sys.argv[1] == 'stills':
        return stills(sys.argv[2:])
    f0, f1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    f1 = min(f1, NFRAMES)
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    if out.endswith('.png'):
        with surf as c: render(f0, c)
        Image.fromarray(arr[..., :3].copy()).save(out); return
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14',
                           '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709',
                           '-color_trc', 'bt709', '-vf', 'scale=out_color_matrix=bt709', out], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        with surf as c: render(fi, c)
        ff.stdin.write(arr.tobytes())
        if fi % 60 == 0: print(out, fi, flush=True)
    ff.stdin.close(); ff.wait()

if __name__ == '__main__':
    main()
