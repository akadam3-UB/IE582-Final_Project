from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.runtime_inputs import (
    FFmpegMicrophoneRecorder,
    RuntimeCommandInputs,
    WhisperAudioTranscriber,
)


class RuntimeCommandInputsTests(unittest.TestCase):
    def test_command_file_updates_current_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            command_path = pathlib.Path(tmpdir) / "command.txt"
            command_path.write_text("track the person", encoding="utf-8")

            runtime = RuntimeCommandInputs(
                initial_command="track something",
                command_file=str(command_path),
            )

            command_text, vlm_text, changed = runtime.poll()
            self.assertTrue(changed)
            self.assertEqual(command_text, "track the person")
            self.assertIsNone(vlm_text)

    def test_vlm_json_file_updates_current_vlm_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vlm_path = pathlib.Path(tmpdir) / "vlm.json"
            vlm_path.write_text('{"action":"track","target_label":"person"}', encoding="utf-8")

            runtime = RuntimeCommandInputs(
                initial_command="track the person",
                vlm_json_file=str(vlm_path),
            )

            command_text, vlm_text, changed = runtime.poll()
            self.assertTrue(changed)
            self.assertEqual(command_text, "track the person")
            self.assertEqual(vlm_text, '{"action":"track","target_label":"person"}')

    def test_transcriber_prefers_mlx_backend_when_available(self) -> None:
        fake_module = SimpleNamespace(
            transcribe=lambda audio_path, path_or_hf_repo=None: {
                "text": f"track the person via {path_or_hf_repo}"
            }
        )
        with mock.patch(
            "ie582_final_project.runtime_inputs._module_available",
            side_effect=lambda name: name == "mlx_whisper",
        ):
            with mock.patch.dict(sys.modules, {"mlx_whisper": fake_module}, clear=False):
                transcriber = WhisperAudioTranscriber(model_name="base", backend="auto")
                text = transcriber.transcribe(pathlib.Path("dummy.wav"))

        self.assertIn("mlx-community/whisper-base", text)
        self.assertEqual(transcriber.backend_name, "mlx-whisper")

    def test_ffmpeg_recorder_builds_expected_command(self) -> None:
        recorder = FFmpegMicrophoneRecorder(input_spec=":2", sample_rate=22050, channels=1, ffmpeg_bin="ffmpeg")
        output_path = pathlib.Path("/tmp/test_command.wav")

        with mock.patch("ie582_final_project.runtime_inputs.subprocess.run") as run_mock:
            recorder.record_to_file(output_path, duration_sec=1.7)

        cmd = run_mock.call_args.args[0]
        self.assertEqual(cmd[:6], ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f"])
        self.assertIn(":2", cmd)
        self.assertIn(str(output_path), cmd)
        self.assertIn("22050", cmd)


if __name__ == "__main__":
    unittest.main()
