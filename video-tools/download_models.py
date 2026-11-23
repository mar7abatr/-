"""Downloads the AI models once so the first real job does not stall (about 4 GB in total)."""
print("1/3 Whisper large-v3 (Arabic transcription, ~3 GB)...", flush=True)
from faster_whisper import WhisperModel
WhisperModel("large-v3", device="cpu", compute_type="int8")

print("2/3 BiRefNet portrait (person cut-out, ~1 GB)...", flush=True)
from rembg import new_session
new_session("birefnet-portrait")

print("3/3 LaMa (text removal, ~200 MB)...", flush=True)
from simple_lama_inpainting import SimpleLama
SimpleLama()

print("All models downloaded.")
