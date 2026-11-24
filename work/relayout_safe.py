"""Re-layout of video 1 so all text/icons stay inside the social-media safe area (x 80..1000, y 285..1635)."""
import os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.py")
s = open(P).read()
REPS = [
    # scene 1/3 camera: map sits in y 313..1004
    ("(WBC[0], WBC[1], 6.4, 600, 1.0)", "(WBC[0], WBC[1], 5.1, 655, 1.0)"),
    ("(HUWARA[0], HUWARA[1], 70, 600, 0.0)", "(HUWARA[0], HUWARA[1], 70, 655, 0.0)"),
    # West Bank side label: inside the frame, left of the map
    ("""            ex, ey = v.s((MAP["wb_bounds"][0] + 4, WBC[1] - 30))
            lx, ly = 150, 230
            q = eout(seg(t, 5.8, 6.3))
            ctx.set_source_rgba(*HL, 0.8 * la); ctx.set_line_width(2)
            ctx.move_to(ex, ey); ctx.line_to(lerp(ex, lx, q), lerp(ey, ly + 40, q)); ctx.stroke()
            ctx.arc(ex, ey, 5, 0, 2 * math.pi); ctx.fill()
            draw_text(ctx, "الضفة الغربية", "bold", 46, lx + 120, ly, "right", alpha=la, wipe=eout(seg(t, 6.0, 6.5)))
            ctx.set_source_rgba(*HL, la); ctx.rectangle(lx - 116 + 236 * (1 - q), ly + 38, 236 * q, 3); ctx.fill()""",
     """            ex, ey = v.s((WBC[0] - 16, WBC[1] + 8))
            tw = text_w("الضفة الغربية", "bold", 42)
            lx, ly = 100 + tw / 2, 840
            q = eout(seg(t, 5.8, 6.3))
            ctx.set_source_rgba(*HL, 0.8 * la); ctx.set_line_width(2)
            ctx.move_to(ex, ey); ctx.line_to(lerp(ex, lx + tw / 2, q), lerp(ey, ly + 36, q)); ctx.stroke()
            ctx.arc(ex, ey, 5, 0, 2 * math.pi); ctx.fill()
            draw_text(ctx, "الضفة الغربية", "bold", 42, lx, ly, alpha=la, wipe=eout(seg(t, 6.0, 6.5)))
            ctx.set_source_rgba(*HL, la); ctx.rectangle(lx - tw / 2 + tw * (1 - q), ly + 34, tw * q, 3); ctx.fill()"""),
    # scene 2: trees
    ("GRID2.append((540 + (2.5 - c) * 150, 1430 + r * 135, (r + c) % 3 == 1))", "GRID2.append((540 + (2.5 - c) * 140, 1355 + r * 92, (r + c) % 3 == 1))"),
    ('"أكثر من", "medium", 70, 540, 330,', '"أكثر من", "medium", 70, 540, 350,'),
    ("        gy = 1250\n", "        gy = 1232\n"),
    ("        sz = 92 * (0.6 + 0.4 * eback(ap))", "        sz = 80 * (0.6 + 0.4 * eback(ap))"),
    ("corner_frame(ctx, 540 - 3 * 150 - 10, 1430 - 80, 6 * 150 + 20, 3 * 135 + 30, 0.6 * ga)",
     "corner_frame(ctx, 540 - 3 * 140 - 10, 1355 - 56, 6 * 140 + 20, 2 * 92 + 112, 0.6 * ga)"),
    # scene 3: crops
    ("CTR3 = (540, 1290)", "CTR3 = (540, 1200)"),
    ('((900, 470, 5.75, "سرقة", "thief"), (180, 470, 6.70, "إتلاف", "crops"))', '((875, 520, 5.75, "سرقة", "thief"), (205, 520, 6.70, "إتلاف", "crops"))'),
    ("ctx.rectangle(0, 1090, W, 560); ctx.fill()", "ctx.rectangle(0, 1035, W, 590); ctx.fill()"),
    ("ctx.rectangle(W - W * q, 1090, W * q, 3); ctx.fill()", "ctx.rectangle(W - W * q, 1035, W * q, 3); ctx.fill()"),
    ("ctx.rectangle(0, 1647, W * q, 2); ctx.fill()", "ctx.rectangle(0, 1622, W * q, 2); ctx.fill()"),
    ('"قرابة", "medium", 62, 540, 1160,', '"قرابة", "medium", 58, 540, 1090,'),
    ("counter_text(ctx, count25k(t), 210, 540, 1295,", "counter_text(ctx, count25k(t), 190, 540, 1200,"),
    ('"كيلوغرام", "bold", 74, 540, 1435,', '"كيلوغرام", "bold", 66, 540, 1318,'),
    ('"من المحاصيل الزراعية", "medium", 58, 540, 1550,', '"من المحاصيل الزراعية", "medium", 52, 540, 1402,'),
    ("x = 540 + (1.5 - j) * 190; y = 1760", "x = 540 + (1.5 - j) * 170; y = 1530"),
    ("ctx.arc(x, y, 72 * eback(p), 0, 2 * math.pi); ctx.fill()", "ctx.arc(x, y, 58 * eback(p), 0, 2 * math.pi); ctx.fill()"),
    ("ctx.arc(x, y, 72 * eback(p), 0, 2 * math.pi); ctx.stroke()", "ctx.arc(x, y, 58 * eback(p), 0, 2 * math.pi); ctx.stroke()"),
    ("y + 4 * math.sin(t * 2 + j), 92 * eback(p), (*HL, p))", "y + 4 * math.sin(t * 2 + j), 74 * eback(p), (*HL, p))"),
    # scene 4: window
    ("WX, WY, WWd, WHt = 60, 170, 960, 720", "WX, WY, WWd, WHt = 100, 300, 880, 660"),
    ("GRID4 = [(540 + (4.5 - c) * 94, 1250 + r * 100) for r in range(3) for c in range(10)]",
     "GRID4 = [(540 + (4.5 - c) * 86, 1218 + r * 88) for r in range(3) for c in range(10)]"),
    ('"مئات", "heavy", 150, xr, 1060,', '"مئات", "heavy", 140, xr, 1082,'),
    ('xr - w1 - gap, 1072, "right"', 'xr - w1 - gap, 1094, "right"'),
    ('w1 = text_w("مئات", "heavy", 150)', 'w1 = text_w("مئات", "heavy", 140)'),
    ("draw_icon(ctx, icon_injured, x, y, 74 * eback(p)", "draw_icon(ctx, icon_injured, x, y, 68 * eback(p)"),
    ("corner_frame(ctx, GRID4[9][0] - 60, 1190, 10 * 94 + 26, 3 * 100 + 22, 0.6 * ga)",
     "corner_frame(ctx, GRID4[9][0] - 55, 1168, 10 * 86 + 24, 3 * 88 + 12, 0.6 * ga)"),
    ("cx_ = 880; cy_ = 1680", "cx_ = 870; cy_ = 1535"),
    ('"خلال الشهر الماضي وحده", "bold", 62, 770, 1690,', '"خلال الشهر الماضي وحده", "bold", 58, 762, 1545,'),
    # scene 5: hologram + cards
    ("CW5, CH5 = 450, 250", "CW5, CH5 = 400, 230"),
    ("return dict(s=lerp(1.0, 0.56, p), cy=lerp(510, 330, p), p=p)", "return dict(s=lerp(0.88, 0.47, p), cy=lerp(575, 445, p), p=p)"),
    ("ny = lerp(1115, 700, p)", "ny = lerp(1112, 712, p)"),
    ("lerp(975, 560, p) if p < 1 else 0", "lerp(985, 600, p) if p < 1 else 0"),
    ("lerp(540, 790, p), lerp(1262, 700, p)", "lerp(540, 790, p), lerp(1252, 712, p)"),
    ('draw_text(ctx, "اعتداء", "bold", 84, 790, 700, scale=0.85)', 'draw_text(ctx, "اعتداء", "bold", 84, 790, 712, scale=0.85)'),
    ("            sx, sy = 540, 1325\n", "            sx, sy = 540, 1300\n"),
    ("lerp(sy, 1500, eout(cp))", "lerp(sy, 1430, eout(cp))"),
    ("actor_badge(ctx, x, 1510, t0", "actor_badge(ctx, x, 1440, t0"),
    ("return (540 + 240 if c == 0 else 540 - 240), 1010 + r * 290", "return (540 + 215 if c == 0 else 540 - 215), 905 + r * 270"),
    ("draw_cat_icon(ctx, kind, t, t0, 0, -28, 120)", "draw_cat_icon(ctx, kind, t, t0, 0, -24, 112)"),
    ('draw_text(ctx, lbl, "bold", 50, 0, 80, alpha=seg(t, t0, t0 + 0.2)', 'draw_text(ctx, lbl, "bold", 48, 0, 72, alpha=seg(t, t0, t0 + 0.2)'),
    ("            sx, sy = 540, 760\n", "            sx, sy = 540, 766\n"),
    ("ctx.line_to(sx, lerp(sy, 840, eout(cp))); ctx.line_to(lerp(sx, ex, eout(cp)), lerp(sy, 840, eout(cp)))",
     "ctx.line_to(sx, lerp(sy, 774, eout(cp))); ctx.line_to(lerp(sx, ex, eout(cp)), lerp(sy, 774, eout(cp)))"),
]
for a, b in REPS:
    n = s.count(a)
    if n != 1:
        raise SystemExit(f"expected 1 match, got {n}: {a[:70]}")
    s = s.replace(a, b)
open(P, "w").write(s)
print("applied", len(REPS))
