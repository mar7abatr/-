"""Verifies every tool the video workflow needs. Prints OK/FAIL per item; exit code 1 if anything is missing."""
import glob, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
fails = []

def report(name, ok, detail=""):
    print(f"  [{'OK  ' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)

print("Video toolkit check")

ff = shutil.which("ffmpeg")
report("ffmpeg", bool(ff), ff or "not on PATH")
if ff:
    enc = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    report("H.264 encoder (libx264)", "libx264" in enc)
    report("AAC encoder", " aac " in enc)
report("ffprobe", bool(shutil.which("ffprobe")))

try:
    import cairo
    report("pycairo (vector motion graphics)", True, cairo.version)
except Exception as e:
    report("pycairo (vector motion graphics)", False, str(e))

try:
    from PIL import Image, ImageDraw, ImageFont, features
    import PIL
    raqm = features.check("raqm")
    report("Pillow", True, PIL.__version__)
    report("Arabic shaping (raqm + fribidi)", raqm, "" if raqm else "install fribidi/libraqm (see README)")
    fonts = sorted(glob.glob(os.path.join(HERE, "fonts", "*.[ot]tf")))
    if raqm and fonts:
        f = ImageFont.truetype(fonts[0], 60, layout_engine=ImageFont.Layout.RAQM)
        w = f.getlength("مستشفى", direction="rtl", language="ar")
        report("DIN Next font renders Arabic", w > 0, os.path.basename(fonts[0]))
    elif not fonts:
        # fonts are licensed and kept out of the repo; a missing font must not block tool installation
        print("  [WARN] fonts/ folder is empty - attach or copy your DIN Next .otf/.ttf files into video-tools/fonts/")
except Exception as e:
    report("Pillow", False, str(e))

for mod, label in (("numpy", "numpy"), ("scipy", "scipy (sound design)"), ("shapely", "shapely (map geometry)"),
                   ("faster_whisper", "faster-whisper (voice-over transcription)"),
                   ("rembg", "rembg (person cut-out)"), ("torch", "PyTorch"),
                   ("simple_lama_inpainting", "LaMa (text/object removal)")):
    try:
        m = __import__(mod)
        report(label, True, getattr(m, "__version__", ""))
    except Exception as e:
        report(label, False, str(e).splitlines()[0])

print()
if fails:
    print(f"{len(fails)} item(s) missing: {', '.join(fails)}")
    sys.exit(1)
print("All tools are ready.")
