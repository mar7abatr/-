from faster_whisper import WhisperModel
import json,sys
m=WhisperModel(sys.argv[1],device="cpu",compute_type="int8",cpu_threads=2)
import numpy as np
segs,info=m.transcribe(np.fromfile("work/a16.raw",dtype=np.float32),language="ar",word_timestamps=True,beam_size=5)
out=[]
for s in segs:
    out.append({"start":s.start,"end":s.end,"text":s.text,"words":[[w.start,w.end,w.word] for w in s.words]})
    print(f"{s.start:6.2f}-{s.end:6.2f} {s.text}",flush=True)
json.dump(out,open(f"work/transcript_{sys.argv[1]}.json","w"),ensure_ascii=False,indent=1)
