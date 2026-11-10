import numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=2)
a = np.fromfile("a16.raw", dtype=np.float32)
for (s, e) in [(21.5, 29.0), (58.4, 65.0)]:
    seg = a[int(s * 16000):int(e * 16000)]
    for prompt in [None, "تقرير إخباري عن حقل كورمور الغازي في جمجمال ودانة غاز ووزارة الكهرباء في إقليم كردستان، الأرقام بالكلمات"]:
        r, _ = m.transcribe(seg, language="ar", beam_size=8, initial_prompt=prompt, temperature=0)
        print(s, e, prompt is not None, ' '.join(x.text for x in r), flush=True)
