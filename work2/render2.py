"""Oslo areas A/B/C reel (13.4 s) in the same style as the settlers video. All content stays inside SAFE."""
import math, sys, os, pickle
import numpy as np
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "work"))
import render as R
from render import (W, H, FPS, OLIVE, DARK, HL, HL8, CUT, clamp, seg, eio, eout, ein, eback, lerp, rnd, bump,
                    draw_text, text_w, corner_frame, panel, glow_disc, dark_disc, pulse_rings, draw_icon,
                    icon_settler, icon_flame, flames, burst, ring_path)

DUR = 13.43
N = int(round(DUR * FPS))
SAFE = (90, 230, 990, 1640)  # x0, y0, x1, y1: nothing important outside this box
MAP = pickle.load(open(os.path.join(HERE, "geo", "map.pkl"), "rb"))
WBC = MAP["c"]
CA = (0.86, 0.68, 0.33)                # area A  bright gold (#C7973B lifted)
CB = OLIVE                             # area B  #896829
CC = (0.17, 0.17, 0.16)                # area C  near #1D1D1D, hatched

# ---------------------------------------------------------------- icons
def icon_shield(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(0, -46); ctx.curve_to(16, -36, 30, -34, 40, -34); ctx.curve_to(40, 4, 30, 30, 0, 48)
    ctx.curve_to(-30, 30, -40, 4, -40, -34); ctx.curve_to(-30, -34, -16, -36, 0, -46); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.set_line_width(7); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(-16, 0); ctx.line_to(-4, 13); ctx.line_to(18, -13); ctx.stroke()

def icon_civil(ctx, fg, cut=CUT):
    """public-services building with columns"""
    ctx.set_source_rgba(*fg)
    ctx.move_to(-46, -18); ctx.line_to(0, -46); ctx.line_to(46, -18); ctx.close_path(); ctx.fill()
    ctx.rectangle(-44, 34, 88, 10); ctx.fill(); ctx.rectangle(-40, -16, 80, 7); ctx.fill()
    for x in (-32, -12, 8, 28):
        ctx.rectangle(x - 1, -6, 7, 38); ctx.fill()
    ctx.set_source_rgba(*cut, 1); ctx.arc(0, -27, 5, 0, 2 * math.pi); ctx.fill()

def icon_document(ctx, fg, cut=CUT):
    ctx.set_source_rgba(*fg)
    ctx.move_to(-32, -46); ctx.line_to(16, -46); ctx.line_to(34, -28); ctx.line_to(34, 46); ctx.line_to(-32, 46); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    ctx.move_to(16, -46); ctx.line_to(16, -28); ctx.line_to(34, -28); ctx.close_path(); ctx.fill()
    for k, wl in enumerate((44, 50, 50, 36)):
        ctx.rectangle(-22, -24 + k * 13, wl, 5); ctx.fill()
    ctx.set_line_width(3.5); ctx.move_to(-20, 36); ctx.curve_to(-12, 24, -6, 42, 2, 32); ctx.curve_to(8, 26, 12, 36, 20, 34); ctx.stroke()

def icon_authority(ctx, fg, cut=CUT):
    """government building with a flag on the dome"""
    ctx.set_source_rgba(*fg)
    ctx.rectangle(-44, 4, 88, 40); ctx.fill()
    ctx.arc(0, 4, 22, math.pi, 2 * math.pi); ctx.fill()
    ctx.rectangle(-2, -42, 4, 26); ctx.fill()
    ctx.move_to(2, -42); ctx.line_to(30, -36); ctx.line_to(2, -28); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*cut, 1)
    for x in (-34, -18, 10, 26):
        ctx.rectangle(x, 14, 8, 14); ctx.fill()
    ctx.rectangle(-7, 22, 14, 22); ctx.fill()

# ---------------------------------------------------------------- camera / map
class View:
    def __init__(self, cx, cy, z, sx, sy):
        self.cx, self.cy, self.z, self.sx, self.sy = cx, cy, z, sx, sy
    def s(self, p): return (self.sx + (p[0] - self.cx) * self.z, self.sy + (p[1] - self.cy) * self.z)
    def apply(self, ctx):
        ctx.translate(self.sx, self.sy); ctx.scale(self.z, self.z); ctx.translate(-self.cx, -self.cy)

MAP_SX, MAP_SY = 390, 870
def camera(t):
    p = eio(seg(t, 0.0, 1.7))
    z = math.exp(lerp(math.log(2.2), math.log(6.7), p))
    sx = lerp(540, MAP_SX, p)
    z *= 1 + 0.03 * seg(t, 1.7, 6.3) + 0.04 * eio(seg(t, 6.3, 7.0)) + 0.02 * seg(t, 7.0, 13.4)
    return View(WBC[0], WBC[1], z, sx, MAP_SY)

def draw_grid(ctx, v, alpha):
    for step, a in ((5, 0.05), (25, 0.09)):
        px = step * v.z
        if px < 26: continue
        fa = alpha * a * clamp((px - 26) / 60)
        x0 = v.cx - (v.sx + 20) / v.z; x1 = v.cx + (W - v.sx + 20) / v.z
        y0 = v.cy - (v.sy + 20) / v.z; y1 = v.cy + (H - v.sy + 20) / v.z
        ctx.set_source_rgba(*HL, fa); ctx.set_line_width(1)
        gx = math.floor(x0 / step) * step
        while gx <= x1:
            sx = v.s((gx, 0))[0]; ctx.move_to(round(sx) + .5, 0); ctx.line_to(round(sx) + .5, H); gx += step
        gy = math.floor(y0 / step) * step
        while gy <= y1:
            sy = v.s((0, gy))[1]; ctx.move_to(0, round(sy) + .5); ctx.line_to(W, round(sy) + .5); gy += step
        ctx.stroke()

def zone_path(ctx, v, key):
    ctx.save(); v.apply(ctx)
    for r in MAP[key]:
        for ring in r: ring_path(ctx, ring)
    ctx.restore()

def hatch(ctx, v, alpha):
    ctx.set_source_rgba(*HL, alpha); ctx.set_line_width(1.2)
    for k in range(-60, 60):
        x = 540 + k * 18
        ctx.move_to(x, 0); ctx.line_to(x + H * 0.6, H)
    ctx.stroke()

# zone reveal times (scan from north to south) and focus on A
REV = {"A": 5.00, "B": 5.30, "C": 5.60}
A_FOCUS = 6.36
def zone_reveal(key, t): return eio(seg(t, REV[key], REV[key] + 0.75))
def dimmed(t): return eio(seg(t, A_FOCUS, A_FOCUS + 0.4))

def reveal_clip(ctx, v, p):
    b = MAP["bounds"]
    y0 = v.s((0, b[1] - 2))[1]; y1 = v.s((0, b[3] + 2))[1]
    yy = lerp(y0, y1, p)
    ctx.rectangle(0, 0, W, yy); ctx.clip()
    return yy

def draw_map(ctx, t):
    v = camera(t)
    draw_grid(ctx, v, 1.0)
    reveal = eout(seg(t, 0.0, 1.2))
    ctx.save(); v.apply(ctx)
    for r in MAP["land"]:
        for ring in r: ring_path(ctx, ring)
    ctx.restore()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.set_source_rgba(0.15, 0.145, 0.135, 0.5 + 0.5 * reveal); ctx.fill()
    for ring in MAP["borders"]:
        ctx.save(); v.apply(ctx); ctx.move_to(*ring[0])
        for p in ring[1:]: ctx.line_to(*p)
        ctx.restore()
    ctx.set_source_rgba(*HL, 0.2 * reveal); ctx.set_line_width(1.2); ctx.stroke()
    # West Bank base
    wp = eout(seg(t, 0.3, 1.6))
    zone_path(ctx, v, "wb")
    ctx.set_source_rgba(*OLIVE, 0.20 * wp); ctx.fill()
    dm = dimmed(t)
    # zones
    for key, col in (("C", CC), ("B", CB), ("A", CA)):
        p = zone_reveal(key, t)
        if p <= 0: continue
        ctx.save()
        yy = reveal_clip(ctx, v, p)
        a = 1.0 if key == "A" else lerp(1.0, 0.62, dm)
        zone_path(ctx, v, key)
        if key == "A":
            fa = 0.92 + 0.08 * math.sin(t * 5) * dm
            ctx.set_source_rgba(*col, fa); ctx.fill_preserve()
            ctx.set_source_rgba(1, 0.93, 0.75, 0.9); ctx.set_line_width(1.0 + 0.8 * dm); ctx.stroke()
        elif key == "B":
            ctx.set_source_rgba(*col, 0.95 * a); ctx.fill_preserve()
            ctx.set_source_rgba(*HL, 0.45 * a); ctx.set_line_width(0.8); ctx.stroke()
        else:
            ctx.set_source_rgba(*col, 0.95 * a); ctx.fill_preserve()
            ctx.save(); ctx.clip(); hatch(ctx, v, 0.10 * a); ctx.restore()
        ctx.restore()
        if 0 < p < 1:
            ctx.set_source_rgba(*HL, 0.9 * math.sin(math.pi * p)); ctx.rectangle(v.s((MAP["bounds"][0] - 4, 0))[0], yy - 1.5,
                                                                                  (MAP["bounds"][2] - MAP["bounds"][0] + 8) * v.z, 3); ctx.fill()
    # A glow when focused
    if dm > 0:
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        zone_path(ctx, v, "A")
        ctx.set_source_rgba(*HL, 0.25 * dm * (0.7 + 0.3 * math.sin(t * 4))); ctx.set_line_width(7); ctx.stroke()
        ctx.restore()
    # East Jerusalem: neutral, outlined
    if zone_reveal("C", t) > 0:
        zone_path(ctx, v, "EJ")
        ctx.set_source_rgba(0.12, 0.12, 0.12, zone_reveal("C", t)); ctx.fill_preserve()
        ctx.set_source_rgba(*HL, 0.5 * zone_reveal("C", t)); ctx.set_line_width(1); ctx.stroke()
    # WB outline drawn on
    for r in MAP["wb"]:
        L = sum(math.dist(a, b) for a, b in zip(r[0], r[0][1:])) * v.z
        for lw, a in ((10, 0.12), (5, 0.25), (2.4, 1.0)):
            zone_path_ring = r[0]
            ctx.save(); v.apply(ctx); ring_path(ctx, zone_path_ring); ctx.restore()
            ctx.set_dash([max(0.01, L * wp), L + 10]); ctx.set_source_rgba(*HL, a * wp); ctx.set_line_width(lw); ctx.stroke()
    ctx.set_dash([])
    return v

# ---------------------------------------------------------------- attack markers
SPOTS = [(p, True) for p in MAP["spotsA"]] + [(p, False) for p in MAP["spotsO"]]
SPOT_T = {k: 1.10 + 0.07 * i for i, k in enumerate(sorted(range(len(SPOTS)), key=lambda k: rnd(k, 31)))}

def draw_markers(ctx, v, t):
    dm = dimmed(t)
    for k, (p, inA) in enumerate(SPOTS):
        t0 = SPOT_T[k]
        a = seg(t, t0, t0 + 0.3)
        if a <= 0: continue
        x, y = v.s(p)
        foc = inA * dm
        al = a * (1 - 0.65 * dm * (not inA))
        r = (17 + 7 * foc) * eback(a)
        if a < 1:
            ctx.set_source_rgba(1, 0.85, 0.55, 0.9 * (1 - a)); ctx.set_line_width(2.5); ctx.arc(x, y, r + 34 * a, 0, 2 * math.pi); ctx.stroke()
        burst(ctx, x, y, t - t0, 0.4, n=6)
        if foc > 0:
            glow_disc(ctx, x, y, 80, 0.4 * foc, HL)
            pulse_rings(ctx, x, y, r + 4, t + rnd(k, 2), foc, n=2, spread=36)
        # flashing on "الاعتداءات"
        fl = math.exp(-max(0, t - 2.10 - 0.04 * k) * 5) if t >= 2.10 + 0.04 * k else 0
        ctx.set_source_rgba(0.07, 0.07, 0.07, 0.95 * al); ctx.arc(x, y, r + 3, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*HL, al); ctx.set_line_width(2); ctx.arc(x, y, r + 3, 0, 2 * math.pi); ctx.stroke()
        draw_icon(ctx, icon_flame, x, y, r * 1.55, (lerp(HL[0], 1, fl), lerp(HL[1], 0.9, fl), lerp(HL[2], 0.7, fl), al))

# ---------------------------------------------------------------- right column
COLX = 800  # centre of the right column (cards 650..950)
CARD_W, CARD_H = 300, 136
LEG = [("A", "مناطق (أ)", CA, 545), ("B", "مناطق (ب)", CB, 720), ("C", "مناطق (ج)", CC, 895)]

def draw_settlers(ctx, v, t):
    p = seg(t, 3.04, 3.4)
    out = 1 - seg(t, 4.55, 4.9)
    if p <= 0 or out <= 0: return
    bx, by = COLX, 430
    # connectors to markers
    lp = eout(seg(t, 3.2, 3.9))
    ctx.set_source_rgba(*HL, 0.45 * out); ctx.set_line_width(1.5)
    for k, (sp, inA) in enumerate(SPOTS[:10]):
        sx, sy = v.s(sp)
        ctx.move_to(bx - 70, by); ctx.line_to(lerp(bx - 70, sx, lp), lerp(by, sy, lp))
    ctx.stroke()
    ctx.save(); ctx.translate(bx, by); s = eback(p); ctx.scale(s, s)
    ctx.push_group()
    ctx.set_source_rgba(0.085, 0.085, 0.085, 0.95); ctx.arc(0, 0, 82, 0, 2 * math.pi); ctx.fill()
    glow_disc(ctx, 0, 0, 82, 0.3)
    ctx.set_source_rgba(*HL, 1); ctx.set_line_width(2.5); ctx.arc(0, 0, 82, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eout(p)); ctx.stroke()
    pulse_rings(ctx, 0, 0, 86, t, 0.6, n=1, spread=36, speed=0.7)
    draw_icon(ctx, icon_settler, 0, 4, 112, (*HL, 1))
    draw_text(ctx, "المستوطنون", "bold", 48, 0, 128, alpha=seg(t, 3.54, 3.75), wipe=eout(seg(t, 3.54, 4.1)))
    ctx.pop_group_to_source(); ctx.paint_with_alpha(out)
    ctx.restore()

def draw_legend(ctx, v, t):
    dm = dimmed(t)
    # header rule
    ha = seg(t, 4.95, 5.2)
    if ha > 0:
        q = eout(ha)
        ctx.set_source_rgba(*HL, 0.9 * ha); ctx.rectangle(COLX + CARD_W / 2 - CARD_W * q, 455, CARD_W * q, 2.5); ctx.fill()
    for key, lbl, col, y in LEG:
        p = seg(t, REV[key], REV[key] + 0.35)
        if p <= 0: continue
        foc = dm if key == "A" else 0
        a = 1 - 0.4 * dm * (key != "A")
        sc = eback(p) * (1 + 0.08 * foc) * (1 + bump(t, [A_FOCUS], 0.35, 0.08) * (key == "A"))
        ctx.save(); ctx.translate(COLX, y); ctx.scale(sc, sc)
        ctx.push_group()
        panel(ctx, -CARD_W / 2, -CARD_H / 2, CARD_W, CARD_H, 1.0, glow=foc)
        if foc > 0:
            ctx.set_source_rgba(*HL, foc); ctx.rectangle(CARD_W / 2 - 6, -CARD_H / 2, 6, CARD_H); ctx.fill()
        # swatch
        sw = 58
        ctx.set_source_rgba(*col, 1); ctx.rectangle(CARD_W / 2 - 26 - sw, -sw / 2, sw, sw); ctx.fill()
        if key == "C":
            ctx.save(); ctx.rectangle(CARD_W / 2 - 26 - sw, -sw / 2, sw, sw); ctx.clip()
            ctx.set_source_rgba(*HL, 0.35); ctx.set_line_width(1.2)
            for k in range(-6, 8):
                ctx.move_to(CARD_W / 2 - 26 - sw + k * 10, -sw / 2); ctx.line_to(CARD_W / 2 - 26 - sw + k * 10 + sw, sw / 2)
            ctx.stroke(); ctx.restore()
        ctx.set_source_rgba(1, 1, 1, 0.5); ctx.set_line_width(1); ctx.rectangle(CARD_W / 2 - 26 - sw, -sw / 2, sw, sw); ctx.stroke()
        draw_text(ctx, lbl, "bold", 42, CARD_W / 2 - 26 - sw - 18, 0, "right", alpha=seg(t, REV[key] + 0.1, REV[key] + 0.3),
                  wipe=eout(seg(t, REV[key] + 0.05, REV[key] + 0.5)), color=HL8 if foc > 0.5 else (255, 255, 255))
        ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
        ctx.restore()
        # leader line from card to a zone of that colour
        lp = eout(seg(t, REV[key] + 0.25, REV[key] + 0.7))
        if lp > 0:
            tgt = {"A": MAP["spotsA"][0], "B": MAP["repB"], "C": MAP["repC"]}[key]
            tx, ty = v.s(tgt)
            sx_ = COLX - CARD_W / 2 - 10
            ctx.set_source_rgba(*HL, 0.75 * a); ctx.set_line_width(1.8)
            mx = lerp(sx_, tx, 0.35)
            ctx.move_to(sx_, y); ctx.line_to(lerp(sx_, mx, min(1, lp * 2)), y)
            if lp > 0.5: ctx.line_to(lerp(mx, tx, (lp - 0.5) * 2), lerp(y, ty, (lp - 0.5) * 2))
            ctx.stroke()
            ctx.arc(sx_, y, 4, 0, 2 * math.pi); ctx.fill()
            if lp >= 1: ctx.arc(tx, ty, 5, 0, 2 * math.pi); ctx.fill()

def draw_big_A(ctx, t):
    """big letter badge on "ألف" beside the map"""
    p = seg(t, A_FOCUS, A_FOCUS + 0.35)
    if p <= 0: return
    x, y = COLX, 1135
    ctx.save(); ctx.translate(x, y); ctx.scale(eback(p), eback(p))
    glow_disc(ctx, 0, 0, 130, 0.45)
    ctx.set_source_rgba(0.085, 0.085, 0.085, 0.95); ctx.arc(0, 0, 92, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*HL, 1); ctx.set_line_width(3); ctx.arc(0, 0, 92, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eout(p)); ctx.stroke()
    ctx.save(); ctx.rotate(t * 0.5); ctx.set_dash([10, 8]); ctx.set_source_rgba(*OLIVE, 0.9); ctx.set_line_width(2)
    ctx.arc(0, 0, 106, 0, 2 * math.pi); ctx.stroke(); ctx.set_dash([]); ctx.restore()
    draw_text(ctx, "أ", "heavy", 130, 0, -6, color=HL8)
    ctx.restore()

# ---------------------------------------------------------------- bottom strip
BOT_Y = 1490
ITEMS = [("أمنياً", icon_shield, 9.80, 790), ("مدنياً", icon_civil, 10.28, 548), ("السلطة الفلسطينية", icon_authority, 11.28, 305)]

def draw_bottom(ctx, v, t):
    pa = seg(t, 6.74, 7.0)
    if pa <= 0: return
    # panel band
    q = eout(pa)
    ctx.set_source_rgba(0.075, 0.075, 0.075, 0.92 * pa); ctx.rectangle(120, 1382, 840, 228); ctx.fill()
    ctx.set_source_rgba(*HL, pa); ctx.rectangle(960 - 840 * q, 1382, 840 * q, 3); ctx.fill()
    ctx.set_source_rgba(*OLIVE, pa); ctx.rectangle(120, 1607, 840 * q, 2); ctx.fill()
    corner_frame(ctx, 110, 1372, 860, 248, 0.8 * pa, L=26, lw=3)
    # Oslo agreement badge (fades when the explanation starts)
    oa = seg(t, 7.35, 7.6) * (1 - seg(t, 9.45, 9.75))
    if oa > 0:
        s = eback(seg(t, 7.35, 7.75))
        ctx.save(); ctx.translate(785, BOT_Y); ctx.scale(s, s)
        glow_disc(ctx, 0, 0, 110, 0.3 * oa)
        draw_icon(ctx, icon_document, 0, 0, 150, (*HL, oa))
        ctx.restore()
        draw_text(ctx, "اتفاقية أوسلو", "heavy", 80, 680, BOT_Y - 4, "right", alpha=oa, wipe=eout(seg(t, 7.40, 8.2)))
        # small handshake-like connector dots
        ctx.set_source_rgba(*HL, 0.6 * oa)
        for k in range(5):
            ctx.arc(690 - k * 22, BOT_Y + 62, 3, 0, 2 * math.pi)
        ctx.fill()
    # explanation items
    for j, (lbl, fn, t0, x) in enumerate(ITEMS):
        p = seg(t, t0, t0 + 0.35)
        if p <= 0: continue
        s = eback(p)
        ctx.save(); ctx.translate(x, BOT_Y - 30); ctx.scale(s, s)
        glow_disc(ctx, 0, 0, 90, 0.35)
        ctx.set_source_rgba(0.085, 0.085, 0.085, 0.95); ctx.arc(0, 0, 62, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*HL, 1); ctx.set_line_width(2.5); ctx.arc(0, 0, 62, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eout(p)); ctx.stroke()
        draw_icon(ctx, fn, 0, 2, 82, (*HL, 1))
        ctx.restore()
        draw_text(ctx, lbl, "bold", 44 if j < 2 else 40, x, BOT_Y + 75, alpha=seg(t, t0 + 0.05, t0 + 0.25), wipe=eout(seg(t, t0 + 0.05, t0 + 0.55)))
        if j > 0:
            cp = eout(seg(t, t0 - 0.2, t0 + 0.1))
            x0 = ITEMS[j - 1][3] - 80; x1 = x + 80
            ctx.set_source_rgba(*HL, 0.7); ctx.set_line_width(2)
            if j == 2:
                ctx.set_dash([6, 6])
            ctx.move_to(x0, BOT_Y - 30); ctx.line_to(lerp(x0, x1, cp), BOT_Y - 30); ctx.stroke(); ctx.set_dash([])
            if j == 2 and cp >= 1:
                ctx.move_to(x1 + 12, BOT_Y - 40); ctx.line_to(x1, BOT_Y - 30); ctx.line_to(x1 + 12, BOT_Y - 20); ctx.stroke()
    # link from A card down to the explanation
    lp = eout(seg(t, 9.6, 10.0))
    if lp > 0:
        ctx.set_source_rgba(*HL, 0.6); ctx.set_line_width(2); ctx.set_dash([4, 6])
        ctx.move_to(COLX, 1230); ctx.line_to(COLX, lerp(1230, 1382, lp)); ctx.stroke(); ctx.set_dash([])

# ---------------------------------------------------------------- frame
def render(i):
    t = i / FPS
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    R.draw_bg(ctx, t)
    dx, dy = R.drift(t)
    ctx.translate(dx * 0.6, dy * 0.6)
    v = draw_map(ctx, t)
    draw_markers(ctx, v, t)
    draw_settlers(ctx, v, t)
    draw_legend(ctx, v, t)
    draw_big_A(ctx, t)
    draw_bottom(ctx, v, t)
    ctx.identity_matrix()
    surf.flush()
    R.bloom(surf, 0.4)
    ha = 0.45 * seg(t, 0.2, 1.0) * (1 - seg(t, 13.1, 13.4))
    corner_frame(ctx, 50, 50, W - 100, H - 100, ha, L=50, lw=2)
    surf.flush()
    a = R.surf_array(surf)[..., :3].astype(np.float32)
    a *= R.VIG
    a *= seg(t, 0.0, 0.3) * (1 - seg(t, 13.15, 13.43))
    return np.clip(a, 0, 255).astype(np.uint8)[..., ::-1].tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "stills":
        os.makedirs(f"{HERE}/stills", exist_ok=True)
        for ts in sys.argv[2:]:
            Image.frombytes("RGB", (W, H), render(int(round(float(ts) * FPS)))).save(f"{HERE}/stills/s_{float(ts):05.2f}.jpg", quality=90)
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
