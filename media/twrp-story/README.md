# From Black Screen to TWRP

An original two-character animated recap of the Xiaomi 17 Ultra recovery work
through commit `d50eb53`. Nezha, a talking phone, and Patch, a robot engineer,
explain the failed boot attempts, the user-supplied working recovery, the touch
latency improvements, and the verified `working76` baseline.

The film is an illustration, not device footage. Its 2,475-test count refers to
the offline workspace suite at that milestone. Data decryption, restored
SELinux enforcement, Magisk and a completed ROM are not claimed. The factual
sources are [the bring-up notes](../../docs/twrp-bringup.md),
[the original installation](../../research/twrp-installed-recovery.json), and
[the working derivative](../../research/twrp-working-defaults.json).

## Editable sources

- `story.json`: dialogue, scene order, pronunciation overrides and factual limits.
- `DESIGN.md`: palette, typography, characters and motion direction.
- `characters.js`: original SVG rigs, with no external character assets.
- `styles.css` and `motion.js`: layout, transitions, acting and audio-driven mouths.
- `generate_audio.py`: local synthetic voices and measured audio timing.
- `compose.mjs`: builds the self-contained scene markup in `index.html`.

The dialogue is 119.975750 seconds, with two distinct Kokoro voices, 16
utterances and eight scenes. Mouth animation uses measured 60 ms RMS windows.
Captions use phrase timings estimated inside each measured utterance; they
are not word-level forced alignment. The voices are synthetic stock voices,
not clones of any real participant. No phone files or credentials are used.

## Reproduce locally

Node 22 or newer, FFmpeg, and Python 3.11 are needed. Install the locked Node
dependencies, then create a Python environment for speech synthesis:

```sh
npm ci
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python kokoro-onnx==0.6.1 soundfile==0.14.0
```

Download `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the public release URL
declared in `generate_audio.py` into `~/.cache/hyperframes/tts/`. The generator
checks both exact SHA-256 hashes before using them. The model files are not
committed. Generate the voices, composition and final export:

```sh
.venv/bin/python generate_audio.py
npm run compose
npm run check
npm run render
```

Use `generate_audio.py --reuse` to regenerate timing and captions without
resynthesizing matching cached utterances. A mismatched text, voice, speed or
audio hash is rejected. Generated audio, timing, screenshots, HTML and video
remain ignored; retain them locally with the final export.

`npm run dev` starts the local Studio in the background. Use the project URL
reported by the CLI, and stop it with `npx hyperframes preview --stop` when done.
There is no publish step in this project.

## Validation notes

Hyperframes `0.8.18` is pinned in `package-lock.json`; npm identifies its source
commit as `bddc9e9bba977c4c777fcec246ecfb6ae43286ec`. GSAP `3.14.2` and both
Fontsource packages at `5.3.0` are pinned too. The initial environment check
found Node, FFmpeg, Chrome and sufficient disk/memory. Speech runs in the local
virtual environment rather than the system Python inspected by the CLI.

The visual check covers runtime errors, layout and contrast. Repeated labels
and headlines explicitly allow overlap during the opaque scene wipes; diagram
text and captions retain ordinary overlap checks. The generated HTML can
trigger a file-length advisory; its editable sources are split above. Mouths
and eyes explicitly use SVG view-box origins, preventing the displaced-face
bug that CSS fill-box scaling produced in the first preview.

The audio validation checks exact stitching, silent gaps, timing bounds and
clipping. A local speech-recognition spot check is supplementary and is not
represented as human listening. Final rendered media must also be checked
with FFprobe and sampled frames; those checks are separate from the repository's
offline unit tests. Local production reports live under `reports/twrp-video/`.
