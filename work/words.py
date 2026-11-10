import json
d = json.load(open('transcript_large-v3.json'))
for s in d:
    print(f"--- {s['start']:.2f}-{s['end']:.2f}")
    print('  '.join(f"{w[0]:.2f}:{w[2].strip()}" for w in s['words']))
