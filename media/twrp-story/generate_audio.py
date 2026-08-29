#!/usr/bin/env python3
"""Synthesize the TWRP dialogue locally and derive its animation timeline.

Run with the project's virtual environment after installing kokoro-onnx==0.6.1
and soundfile==0.14.0. Public model assets live in the Hyperframes TTS cache;
this script never uses a speech API or reads device evidence or credentials.
Use --reuse to rebuild timing and captions from the already generated WAVs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re


MODEL_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
MODEL_FILES = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
CAPTION_METHOD = (
    "Estimated phrase boundaries within each measured utterance: weighted display "
    "words are distributed over the observed speech span. Not forced word alignment."
)
SPEED = 1.06
OPENING_LEAD = 1.10
SPEAKER_GAP = 0.20
SCENE_GAP = 0.55
FINAL_HOLD = 2.0
MOUTH_INTERVAL = 0.06


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def caption_chunks(text: str) -> list[str]:
    """Prefer 6–10 word phrases, with punctuation and short last cues respected."""
    words = text.split()
    chunks = []
    while words:
        if len(words) <= 10:
            chunks.append(" ".join(words))
            break
        stop = 8
        punctuated = [
            index for index in range(5, min(10, len(words)) + 1)
            if re.search(r"[.!?;:,]$", words[index - 1])
        ]
        if punctuated:
            stop = min(punctuated, key=lambda count: abs(count - 8))
        if len(words) - stop < 4:
            stop = max(5, len(words) // 2)
        chunks.append(" ".join(words[:stop]))
        words = words[stop:]
    return chunks


def phrase_weight(text: str) -> float:
    """A conservative reading-time estimate, not an asserted word alignment."""
    return sum(
        max(1.0, len(re.sub(r"\W", "", word)) / 4.0)
        + (0.65 if re.search(r"[.!?;:]$", word) else 0.0)
        for word in text.split()
    )


def subtitle_timestamp(seconds: float, separator: str = ",") -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{milliseconds:03}"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/hyperframes/tts")
    parser.add_argument("--reuse", action="store_true", help="Reuse matching existing line audio.")
    args = parser.parse_args()

    import numpy as np
    import soundfile as sf

    project = args.project.resolve()
    story_path = project / "story.json"
    story = json.loads(story_path.read_text())
    audio_dir = project / "audio"
    audio_dir.mkdir(exist_ok=True)
    for filename, expected in MODEL_FILES.items():
        candidate = args.cache / filename
        if not candidate.is_file() or sha256(candidate) != expected:
            raise SystemExit(f"Missing or unexpected public TTS model: {filename}")

    synthesizer = None
    if not args.reuse:
        from kokoro_onnx import Kokoro
        synthesizer = Kokoro(
            str(args.cache / "kokoro-v1.0.onnx"),
            str(args.cache / "voices-v1.0.bin"),
        )

    sample_rate = 24000
    pieces = [np.zeros(round(OPENING_LEAD * sample_rate), dtype=np.float32)]
    cursor = len(pieces[0])
    lines, scenes, captions, mouth, manifest_lines = [], [], [], [], []
    for speaker in story["characters"]:
        mouth.append({"time": 0.0, "speaker": speaker, "value": 0.0})

    line_index = 0
    for scene_index, scene in enumerate(story["scenes"]):
        scene_start = 0 if scene_index == 0 else cursor / sample_rate - SCENE_GAP / 2
        for in_scene_index, line in enumerate(scene["lines"]):
            line_index += 1
            speaker = line["speaker"]
            voice = story["characters"][speaker]["voice"]
            speech = line.get("speech", line["text"])
            filename = f"{line_index:02}-{scene['id']}-{speaker}.wav"
            path = audio_dir / filename
            line_meta_path = path.with_suffix(".json")
            synthesis_identity = {"speech": speech, "voice": voice, "speed": SPEED}
            if args.reuse:
                line_meta = json.loads(line_meta_path.read_text())
                if line_meta["synthesis"] != synthesis_identity:
                    raise SystemExit(f"Cached utterance does not match story: {filename}")
                if sha256(path) != line_meta["sha256"]:
                    raise SystemExit(f"Cached utterance hash differs: {filename}")
                samples, produced_rate = sf.read(path, dtype="float32")
            else:
                samples, produced_rate = synthesizer.create(
                    speech, voice=voice, speed=SPEED, lang="en-us",
                    sentence_pause=0.22, clause_pause=0.075,
                )
                if not len(samples) or not np.isfinite(samples).all():
                    raise SystemExit(f"Invalid synthesized utterance: {filename}")
                rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
                peak = float(np.max(np.abs(samples)))
                if rms < 1e-5:
                    raise SystemExit(f"Silent synthesized utterance: {filename}")
                gain = min(0.105 / rms, 0.82 / peak)
                samples = np.asarray(samples * gain, dtype=np.float32)
                fade = min(round(produced_rate * 0.004), len(samples) // 2)
                samples[:fade] *= np.linspace(0, 1, fade)
                samples[-fade:] *= np.linspace(1, 0, fade)
                sf.write(path, samples, produced_rate, subtype="PCM_16")
                samples, produced_rate = sf.read(path, dtype="float32")
                line_meta = {
                    "synthesis": synthesis_identity,
                    "normalization": {"targetRms": 0.105, "peakLimit": 0.82, "gain": gain},
                    "sha256": sha256(path),
                }
                write_json(line_meta_path, line_meta)
            if produced_rate != sample_rate or samples.ndim != 1:
                raise SystemExit("All utterances must be 24 kHz mono audio")

            start = cursor / sample_rate
            duration = len(samples) / sample_rate
            end = start + duration
            peak = float(np.max(np.abs(samples)))
            rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
            if not 0.001 < rms < 0.3 or not peak < 0.99:
                raise SystemExit(f"Audio quality check failed: {filename}")
            relative_audio = f"audio/{filename}"
            line_entry = {
                "id": line_index, "sceneId": scene["id"], "speaker": speaker,
                "text": line["text"], "start": round(start, 6),
                "end": round(end, 6), "audio": relative_audio,
            }
            lines.append(line_entry)
            manifest_lines.append({
                **line_entry, "voice": voice, "spokenText": speech,
                "frames": len(samples), "duration": duration, "sampleRate": sample_rate,
                "sha256": sha256(path), "peak": peak, "rms": rms,
                "clippedSamples": int(np.count_nonzero(np.abs(samples) >= 0.999)),
            })
            pieces.append(samples)
            cursor += len(samples)

            hop = round(MOUTH_INTERVAL * sample_rate)
            envelope = [float(np.sqrt(np.mean(samples[offset:offset + hop] ** 2)))
                        for offset in range(0, len(samples), hop)]
            reference = max(float(np.percentile(envelope, 90)), 0.0025)
            gate = max(0.0025, reference * 0.055)
            mouth.append({"time": round(start, 6), "speaker": speaker, "value": 0.0})
            for index, amplitude in enumerate(envelope):
                value = 0.0 if amplitude <= gate else min(1.0, (amplitude - gate) / (reference - gate)) ** 0.65
                at = min(end, start + (index + 0.5) * MOUTH_INTERVAL)
                mouth.append({"time": round(at, 6), "speaker": speaker, "value": round(value, 4)})
            mouth.append({"time": round(end, 6), "speaker": speaker, "value": 0.0})

            active = np.flatnonzero(np.abs(samples) > max(0.0025, peak * 0.013))
            speech_start = start + max(0, int(active[0]) - round(0.04 * sample_rate)) / sample_rate
            speech_end = start + min(len(samples), int(active[-1]) + round(0.08 * sample_rate)) / sample_rate
            chunks = caption_chunks(line["text"])
            weights = [phrase_weight(chunk) for chunk in chunks]
            consumed_weight = 0.0
            total_weight = sum(weights)
            for chunk, weight in zip(chunks, weights):
                cue_start = speech_start + (speech_end - speech_start) * consumed_weight / total_weight
                consumed_weight += weight
                cue_end = speech_start + (speech_end - speech_start) * consumed_weight / total_weight
                captions.append({"text": chunk, "speaker": speaker,
                                 "start": round(cue_start, 6), "end": round(cue_end, 6)})
            print(f"{line_index:02}/16 {speaker:5} {duration:6.2f}s peak={peak:.3f} {filename}", flush=True)

            if in_scene_index < len(scene["lines"]) - 1:
                gap = np.zeros(round(SPEAKER_GAP * sample_rate), dtype=np.float32)
                pieces.append(gap)
                cursor += len(gap)

        last_scene = scene_index == len(story["scenes"]) - 1
        gap_seconds = FINAL_HOLD if last_scene else SCENE_GAP
        scene_end = cursor / sample_rate + (FINAL_HOLD if last_scene else SCENE_GAP / 2)
        scenes.append({"id": scene["id"], "start": round(scene_start, 6),
                       "end": round(scene_end, 6), "duration": round(scene_end - scene_start, 6)})
        gap = np.zeros(round(gap_seconds * sample_rate), dtype=np.float32)
        pieces.append(gap)
        cursor += len(gap)

    dialogue = np.concatenate(pieces)
    duration = len(dialogue) / sample_rate
    for speaker in story["characters"]:
        mouth.append({"time": round(duration, 6), "speaker": speaker, "value": 0.0})
    mouth.sort(key=lambda item: (item["time"], item["speaker"]))
    # A final partial window can share the utterance's exact end; silence wins.
    unique_mouth = {(item["speaker"], item["time"]): item for item in mouth}
    mouth = sorted(unique_mouth.values(), key=lambda item: (item["time"], item["speaker"]))
    dialogue_path = audio_dir / "dialogue.wav"
    sf.write(dialogue_path, dialogue, sample_rate, subtype="PCM_16")
    timing = {
        "duration": round(duration, 6), "scenes": scenes, "lines": lines,
        "mouth": mouth, "captions": captions, "sampleRate": sample_rate,
        "captionTimingMethod": CAPTION_METHOD,
        "mouthTimingMethod": "60 ms RMS windows measured from each utterance; normalized per line with a silence gate.",
        "openingLead": OPENING_LEAD, "speakerGap": SPEAKER_GAP,
        "sceneGap": SCENE_GAP, "finalHold": FINAL_HOLD,
    }
    write_json(project / "timing.json", timing)
    (project / "timing.js").write_text(
        "window.TWRP_TIMING = " + json.dumps(timing, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )
    srt, vtt = [], ["WEBVTT", "", "NOTE " + CAPTION_METHOD, ""]
    for index, cue in enumerate(captions, 1):
        speaker_name = story["characters"][cue["speaker"]]["name"]
        srt.extend([str(index), f"{subtitle_timestamp(cue['start'])} --> {subtitle_timestamp(cue['end'])}",
                    f"{speaker_name}: {cue['text']}", ""])
        vtt.extend([str(index), f"{subtitle_timestamp(cue['start'], '.')} --> {subtitle_timestamp(cue['end'], '.')}",
                    f"<v {speaker_name}>{cue['text']}", ""])
    (project / "captions.srt").write_text("\n".join(srt) + "\n")
    (project / "captions.vtt").write_text("\n".join(vtt) + "\n")
    write_json(audio_dir / "manifest.json", {
        "generator": "generate_audio.py", "storySha256": sha256(story_path),
        "synthesis": "Local CPU inference; synthetic stock voices; no voice cloning or speech API.",
        "packages": {name: importlib.metadata.version(name) for name in
                     ["kokoro-onnx", "onnxruntime", "numpy", "soundfile", "phonemizer", "espeakng-loader"]},
        "models": [{"file": name, "sha256": digest, "source": f"{MODEL_RELEASE}/{name}"}
                   for name, digest in MODEL_FILES.items()],
        "modelLicense": "Apache-2.0", "kokoroOnnxLicense": "MIT", "voices": story["characters"],
        "speed": SPEED, "sampleRate": sample_rate, "channels": 1, "format": "PCM_16 WAV",
        "dialogue": {"path": "audio/dialogue.wav", "sha256": sha256(dialogue_path),
                     "frames": len(dialogue), "duration": duration, "peak": float(np.max(np.abs(dialogue))),
                     "clippedSamples": int(np.count_nonzero(np.abs(dialogue) >= 0.999))},
        "captionTimingMethod": CAPTION_METHOD, "lines": manifest_lines,
    })
    print(f"Complete: {duration:.3f}s; {len(lines)} utterances; {len(captions)} caption phrases; {len(mouth)} mouth samples.")


if __name__ == "__main__":
    main()
