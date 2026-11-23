# Video production toolkit — instructions for Claude Code

This folder is a news motion-graphics production kit. The user is a video specialist producing Arabic digital-news videos (Reels and 16:9). Every job ends with a real exported file, not a plan or code.

## Environment

- Python tools live in `.venv/`. Always run scripts with `.venv/bin/python` (Windows: run inside WSL Ubuntu).
- Run `.venv/bin/python check_tools.py` first if anything fails to import.
- `fonts/` holds the user's DIN Next Arabic fonts (Black, Bold, Medium, Light). They are licensed and are not committed; in Hoplite, `.hoplite/setup.sh` copies them from the conversation's attachments. If `fonts/` is empty, ask the user to attach them. Load them with Pillow using `layout_engine=ImageFont.Layout.RAQM`, `direction="rtl"`, `language="ar"`. Without RAQM, Arabic letters render disconnected — never ship that.
- `examples/` holds the complete renderers from earlier finished projects. Reuse their structure. Paths inside them point to the original working folders and must be updated.

## Default brand (unless the brief says otherwise)

- Colours: olive `#896829`, dark `#1D1D1D`, highlight tint `#C7973B`.
- Font: DIN Next Arabic.
- Style: dark digital-news motion graphics — animated connector lines, corner brackets, soft glow, gentle digital camera drift, light film grain and vignette.

## Output specs

- Reels: 1080x1920. Wide: 1920x1080. 30 fps.
- Video: H.264 High, yuv420p, `-preset slow`, about 15–18 Mb/s, `-movflags +faststart`.
- Audio: AAC 320k, 48 kHz, integrated loudness about -15 LUFS, true peak no higher than -1 dB.
- Keep files under 50 MB when they will be shared through chat.

## Workflow

1. Inspect every input: `ffprobe` for size, fps and duration, plus `ffmpeg -vf fps=1,scale=240:-1,tile=8x2` contact sheets to see the content. Detect letterboxing with `cropdetect`.
2. Voice-over: transcribe with faster-whisper `large-v3`, `language="ar"`, `word_timestamps=True`. Build a timeline that maps each spoken word to its visual event. Whisper can mishear names (for example "كما العدوان" means "كمال عدوان"), so correct names from the brief.
3. Render frames in Python with pycairo (vectors) and Pillow (Arabic text, media), then pipe raw RGB frames straight into ffmpeg (see `examples/`). Use multiprocessing for speed.
4. Sound: keep the original voice-over complete and unaltered. Add subtle synthesized effects (whooshes, low hits, ticks, drone) with numpy/scipy. Mute source clips that contain other channels' presenters or reporters unless asked otherwise.
5. Verify before delivering: extract frames at each key sentence from the final MP4 and look at them. Check duration, codec and loudness with `ffprobe` and `ebur128`.

## Editorial rules from the user's briefs

- Never show a media item before the narrator mentions its subject.
- Use only the supplied media — no random internet images and no AI-generated replacements.
- Preserve aspect ratios: crop, never stretch.
- No TV-channel logos, tickers, "live" bugs or watermarks. Crop them out of source clips.
- No extra titles or text that the narrator does not say, unless the user asks for them.
- Map videos: a flat 2D infographic map (not satellite or 3D). Real coordinates come from OpenStreetMap via the Overpass API and boundaries from Natural Earth / geoBoundaries (see `examples/prep_geo.py`).

## Useful recipes

- Person cut-out: `rembg` with session `birefnet-portrait` (best for people).
- Remove text from an image: build a mask of the text pixels, run `SimpleLama()(image, mask)`, then repeat on leftovers with a tighter mask.
- Vertical crop of a 16:9 clip: `crop=w=ih*9/16*0.92:h=ih:x='...':y=0` with a slow pan in `x` that follows the action, then scale to the frame size.
- Interlaced TV sources: deinterlace with `bwdif` before grabbing stills.
