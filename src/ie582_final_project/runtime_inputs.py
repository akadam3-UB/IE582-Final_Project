"""Runtime helpers for speech/text command updates and VLM grounding input."""

from __future__ import annotations

import importlib.util
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _normalize_mlx_model_name(model_name: str) -> str:
    model = model_name.strip()
    if not model:
        return "mlx-community/whisper-tiny"
    if "/" in model or model.startswith("."):
        return model

    simple_map = {
        "tiny": "mlx-community/whisper-tiny",
        "base": "mlx-community/whisper-base",
        "small": "mlx-community/whisper-small",
        "medium": "mlx-community/whisper-medium",
        "large": "mlx-community/whisper-large-v3",
        "turbo": "mlx-community/whisper-large-v3-turbo",
        "large-v3": "mlx-community/whisper-large-v3",
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    }
    return simple_map.get(model, f"mlx-community/whisper-{model}")


@dataclass
class _TrackedFile:
    """File reader that only reports content when the file changes."""

    path: Optional[Path] = None
    _last_signature: Optional[Tuple[int, int]] = None

    def poll(self) -> Tuple[Optional[str], bool]:
        if self.path is None or not self.path.exists():
            return None, False

        stat = self.path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
        if signature == self._last_signature:
            return None, False

        self._last_signature = signature
        return _read_text(self.path), True


class WhisperAudioTranscriber:
    """Wrapper around local speech-to-text backends.

    Backend selection order:
    1. `mlx_whisper` on Apple Silicon when available
    2. `whisper` as a fallback
    """

    def __init__(self, model_name: str = "base", backend: str = "auto") -> None:
        self.model_name = model_name
        self.backend = backend
        self._model = None
        self._backend_name: Optional[str] = None
        self._backend_module = None

    @property
    def backend_name(self) -> Optional[str]:
        return self._backend_name

    def _load_backend(self) -> Tuple[str, object]:
        if self._backend_module is not None and self._backend_name is not None:
            return self._backend_name, self._backend_module

        requested = self.backend.strip().lower()
        errors = []
        candidates = []
        if requested == "auto":
            candidates = ["mlx-whisper", "whisper"]
        elif requested in {"mlx", "mlx-whisper", "mlx_whisper"}:
            candidates = ["mlx-whisper"]
        elif requested == "whisper":
            candidates = ["whisper"]
        else:
            raise RuntimeError(
                f"Unsupported whisper backend '{self.backend}'. Use auto, mlx-whisper, or whisper."
            )

        for candidate in candidates:
            if candidate == "mlx-whisper" and _module_available("mlx_whisper"):
                try:
                    import mlx_whisper  # type: ignore
                except Exception as exc:
                    errors.append(f"mlx-whisper import failed: {exc}")
                    continue

                self._backend_name = "mlx-whisper"
                self._backend_module = mlx_whisper
                return self._backend_name, self._backend_module

            if candidate == "whisper" and _module_available("whisper"):
                try:
                    import whisper  # type: ignore
                except Exception as exc:
                    errors.append(f"whisper import failed: {exc}")
                    continue

                self._backend_name = "whisper"
                self._backend_module = whisper
                return self._backend_name, self._backend_module

        detail = f" Details: {'; '.join(errors)}" if errors else ""
        raise RuntimeError(
            "No speech transcription backend is installed. "
            "On Apple Silicon, install `mlx-whisper`; otherwise install `openai-whisper`."
            + detail
        )

    def _get_model(self):
        if self._model is not None:
            return self._model

        backend_name, backend_module = self._load_backend()
        if backend_name == "whisper":
            self._model = backend_module.load_model(self.model_name)
        else:
            self._model = backend_module
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        model = self._get_model()
        if self.backend_name == "mlx-whisper":
            result = model.transcribe(
                str(audio_path),
                path_or_hf_repo=_normalize_mlx_model_name(self.model_name),
            )
        else:
            result = model.transcribe(str(audio_path))
        text = str(result.get("text", "")).strip()
        return text


class FFmpegMicrophoneRecorder:
    """Record short microphone clips on macOS using ffmpeg/avfoundation."""

    def __init__(
        self,
        input_spec: str = ":0",
        sample_rate: int = 16000,
        channels: int = 1,
        ffmpeg_bin: str = "ffmpeg",
    ) -> None:
        self.input_spec = input_spec
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.ffmpeg_bin = ffmpeg_bin

    def record_to_file(self, output_path: Path, duration_sec: float) -> Path:
        duration_sec = max(0.5, float(duration_sec))
        cmd = [
            self.ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "avfoundation",
            "-i",
            self.input_spec,
            "-t",
            f"{duration_sec:.2f}",
            "-ac",
            str(self.channels),
            "-ar",
            str(self.sample_rate),
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "ffmpeg was not found. Install ffmpeg to use microphone capture on macOS."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(
                "ffmpeg microphone capture failed. "
                f"Input spec '{self.input_spec}' may be wrong or microphone access may be blocked. "
                f"{stderr}"
            ) from exc

        return output_path


def list_macos_audio_devices(ffmpeg_bin: str = "ffmpeg") -> str:
    """Return ffmpeg avfoundation device listing text for macOS."""

    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-f",
        "avfoundation",
        "-list_devices",
        "true",
        "-i",
        "",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg was not found. Install ffmpeg first.") from exc

    output = "\n".join(part for part in (proc.stderr, proc.stdout) if part).strip()
    if not output:
        output = "No avfoundation device output returned by ffmpeg."
    return output


class RuntimeCommandInputs:
    """Track dynamic command updates from text files, audio files, and VLM JSON files."""

    def __init__(
        self,
        initial_command: str,
        command_file: Optional[str] = None,
        audio_file: Optional[str] = None,
        vlm_json_file: Optional[str] = None,
        whisper_model: str = "base",
        whisper_backend: str = "auto",
    ) -> None:
        self.current_command = initial_command.strip()
        self.current_vlm_text: Optional[str] = None

        self._command_file = _TrackedFile(Path(command_file).expanduser() if command_file else None)
        self._audio_file = _TrackedFile(Path(audio_file).expanduser() if audio_file else None)
        self._vlm_json_file = _TrackedFile(Path(vlm_json_file).expanduser() if vlm_json_file else None)
        self._audio_transcriber = WhisperAudioTranscriber(
            model_name=whisper_model,
            backend=whisper_backend,
        )

    def poll(self) -> Tuple[str, Optional[str], bool]:
        """Return the latest command text, latest VLM JSON text, and whether anything changed."""

        changed = False

        command_text, command_updated = self._command_file.poll()
        if command_updated and command_text:
            self.current_command = command_text
            changed = True

        _, audio_updated = self._audio_file.poll()
        if audio_updated and self._audio_file.path is not None:
            transcribed = self._audio_transcriber.transcribe(self._audio_file.path)
            if transcribed:
                self.current_command = transcribed
                changed = True

        vlm_text, vlm_updated = self._vlm_json_file.poll()
        if vlm_updated:
            self.current_vlm_text = vlm_text or None
            changed = True

        return self.current_command, self.current_vlm_text, changed
