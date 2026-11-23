from faster_whisper import WhisperModel
m=WhisperModel("large-v3",device="cpu",compute_type="int8")
import wave,numpy as np
w=wave.open("/tmp/work/src/vo16.wav");a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
segs,_=m.transcribe(a,language="ar",word_timestamps=True,beam_size=5)
for s in segs:
    print(f"[{s.start:.2f}-{s.end:.2f}] {s.text}")
    for w in s.words: print(f"   {w.start:.2f}-{w.end:.2f} {w.word}")
