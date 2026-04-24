#!/usr/bin/env python3
"""Capture microphone snippets on macOS and write transcribed commands to a file."""

from __future__ import annotations

import argparse
import pathlib
import signal
import sys
import tempfile
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.runtime_inputs import (
    FFmpegMicrophoneRecorder,
    WhisperAudioTranscriber,
    list_macos_audio_devices,
)


def _write_if_changed(path: pathlib.Path, text: str, last_text: str) -> str:
    normalized = text.strip()
    if not normalized or normalized == last_text:
        return last_text
    path.write_text(normalized, encoding="utf-8")
    print(f"[speech] {normalized}")
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Live microphone -> command file bridge for macOS")
    parser.add_argument("--output-command-file", default="runtime_command.txt", help="Where to write the latest transcribed command")
    parser.add_argument("--duration-sec", type=float, default=2.5, help="Length of each recorded microphone clip")
    parser.add_argument("--pause-sec", type=float, default=0.4, help="Pause between recordings")
    parser.add_argument("--input-spec", default=":0", help="ffmpeg avfoundation input spec, e.g. ':0' for the first audio device")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--whisper-model", default="base", help="Whisper model name or MLX repo alias")
    parser.add_argument("--whisper-backend", default="auto", choices=("auto", "mlx-whisper", "whisper"))
    parser.add_argument("--list-devices", action="store_true", help="Print ffmpeg avfoundation devices and exit")
    parser.add_argument("--once", action="store_true", help="Record a single clip and exit")
    args = parser.parse_args()

    if args.list_devices:
        print(list_macos_audio_devices())
        return

    output_path = pathlib.Path(args.output_command_file).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    recorder = FFmpegMicrophoneRecorder(
        input_spec=args.input_spec,
        sample_rate=args.sample_rate,
        channels=args.channels,
    )
    transcriber = WhisperAudioTranscriber(
        model_name=args.whisper_model,
        backend=args.whisper_backend,
    )

    shutdown = False

    def handle_signal(signum, frame) -> None:
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    last_text = ""
    with tempfile.TemporaryDirectory(prefix="ie582_mic_") as tmpdir:
        clip_path = pathlib.Path(tmpdir) / "mic_command.wav"

        while not shutdown:
            try:
                recorder.record_to_file(clip_path, args.duration_sec)
                text = transcriber.transcribe(clip_path)
                last_text = _write_if_changed(output_path, text, last_text)
            except RuntimeError as exc:
                raise SystemExit(str(exc)) from exc

            if args.once:
                break
            time.sleep(max(0.0, args.pause_sec))


if __name__ == "__main__":
    main()
