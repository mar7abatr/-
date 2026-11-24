"""Measure every text and icon drawn in each frame against the social-media safe area.
usage: check_safe.py <module_dir> <module_name> [step]"""
import sys, os, importlib, math
d, name = sys.argv[1], sys.argv[2]
step = int(sys.argv[3]) if len(sys.argv) > 3 else 3
sys.argv = ["x", "none"]
sys.path.insert(0, os.path.abspath(d)); sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "work")))
import render as base
mod = importlib.import_module(name)
X0, Y0, X1, Y1 = 80, 285, 1000, 1635
hits = {}
CUR = [0.0]

def rec(ctx, kind, label, pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    over = max(X0 - bx0, bx1 - X1, Y0 - by0, by1 - Y1)
    if over > 2:
        k = (kind, label)
        h = hits.setdefault(k, [CUR[0], CUR[0], 0, (bx0, by0, bx1, by1)])
        h[1] = CUR[0]
        if over > h[2]: h[2] = over; h[3] = (round(bx0), round(by0), round(bx1), round(by1))

orig_text = base.draw_text
def draw_text(ctx, s, font, size, x, y, align="center", alpha=1.0, color=(255, 255, 255), scale=1.0, ltr=False, wipe=1.0):
    if alpha > 0.15 and wipe > 0.2:
        _, w, h, pad = base.text_surface(s, font, size, color, ltr)
        x0 = -w + pad if align == "right" else (-pad if align == "left" else -w / 2)
        ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale)
        pts = [ctx.user_to_device(px, py) for px in (x0 + pad, x0 + w - pad) for py in (-h / 2 + pad, h / 2 - pad)]
        ctx.restore()
        rec(ctx, "text", s, pts)
    return orig_text(ctx, s, font, size, x, y, align, alpha, color, scale, ltr, wipe)

orig_icon = base.draw_icon
def draw_icon(ctx, fn, x, y, size, fg, cut=base.CUT, rot=0.0, **kw):
    if (fg[3] if len(fg) > 3 else 1) > 0.15:
        ctx.save(); ctx.translate(x, y); ctx.rotate(rot)
        r = size * 0.48
        pts = [ctx.user_to_device(px, py) for px in (-r, r) for py in (-r, r)]
        ctx.restore()
        rec(ctx, "icon", fn.__name__, pts)
    return orig_icon(ctx, fn, x, y, size, fg, cut, rot, **kw)

for m in {base, mod}:
    m.draw_text = draw_text; m.draw_icon = draw_icon
for i in range(0, mod.N, step):
    CUR[0] = i / mod.FPS
    mod.render(i)
if not hits:
    print("OK: nothing outside the safe area")
for (kind, label), (a, b, over, bb) in sorted(hits.items(), key=lambda kv: kv[1][0]):
    print(f"{a:6.2f}-{b:6.2f}s  {kind:4s} {label!s:28s} over={over:5.0f}px  bbox={bb}")
