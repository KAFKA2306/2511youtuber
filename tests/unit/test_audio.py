import json

import pytest
from pydub import AudioSegment

from src.steps.audio import AudioSynthesizer


class TestAudioSynthesizerUnit:
    def test_generates_silent_audio_when_script_has_no_segments(
        self, temp_run_dir, test_run_id
    ) -> None:
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_path = run_path / "script.json"
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump({"segments": []}, f)

        step = AudioSynthesizer(run_id=test_run_id, run_dir=temp_run_dir)
        output_path = step.run({"generate_script": script_path})

        assert output_path.exists()

        audio = AudioSegment.from_wav(output_path)
        assert audio.duration_seconds == pytest.approx(1.0, abs=0.05)

