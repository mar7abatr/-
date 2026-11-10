"""Pre-extract every clip segment used in the edit as raw RGBA @30fps (aspect preserved)."""
import os, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))
A = '../.hoplite/attachments'
DRONE = f'{A}/art_upload_1e283b27cc964f6886ae3d320e7af82c/مشاهد لطائرة شاهد 136 بدون خلفية.webm'
K1 = f'{A}/art_upload_47b4d42f46ea45ceac89694534db6736/احتراق منشأة كورمور.MP4'
K2 = f'{A}/art_upload_b93d123af50448bbbd8ed6033dff34b6/احتراق منشأة كورمور 2.mp4'
LAUNCH = f'{A}/art_upload_b12dd9da1002468ba3cc2d29fecc87ce/drone luncher.mp4'
PM = f'{A}/art_upload_f5109238a1384c8285e7c1bcdd8f448b/PM_Ali_Zeidi.mp4'
KEY = 'colorkey=0x02E334:0.32:0.08,despill=type=green'
JOBS = [
    # Shahed drone on green screen: crop around the airframe at 16:9, then key out the green.
    ('drone_side', DRONE, 15.0, 5.5, f'crop=1500:844:1440:668,scale=960:540,{KEY}', 960, 540),
    ('drone_front', DRONE, 26.0, 4.5, f'crop=1100:619:1386:790,scale=960:540,{KEY}', 960, 540),
    ('k1', K1, 0, 5.37, 'scale=540:900', 540, 900),
    ('k2a', K2, 8, 3.5, 'scale=580:785', 580, 785),
    ('k2b', K2, 40, 3.0, 'scale=580:785', 580, 785),
    ('launch', LAUNCH, 6.0, 4.5, 'scale=1024:576', 1024, 576),
    ('pm1', PM, 0, 9.0, 'scale=1120:630', 1120, 630),
    ('pm2', PM, 3.5, 7.47, 'scale=1120:630', 1120, 630),
]
os.makedirs('media', exist_ok=True)
lines = []
for name, src, ss, dur, vf, w, h in JOBS:
    out = f'media/{name}.rgba'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(ss), '-t', str(dur), '-i', src, '-an',
                    '-vf', f'{vf},fps=30,format=rgba', '-f', 'rawvideo', '-pix_fmt', 'rgba', out], check=True)
    n = os.path.getsize(out) // (w * h * 4)
    lines.append(f'{name} {w} {h} {n}')
    print(lines[-1], flush=True)
open('media/index.txt', 'w').write('\n'.join(lines) + '\n')
