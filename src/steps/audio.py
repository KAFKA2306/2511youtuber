import json
from pathlib import Path
from typing import Dict
from pydub import AudioSegment
from src.steps.base import Step
from src.providers.base import ProviderChain
from src.providers.tts import VOICEVOXProvider, Pyttsx3Provider
from src.models import Script


class AudioSynthesizer(Step):
    name = "synthesize_audio"
    output_filename = "audio.wav"

    def __init__(self, run_id: str, run_dir: Path, voicevox_config: Dict = None, pyttsx3_config: Dict = None):
        super().__init__(run_id, run_dir)
        self.voicevox_config = voicevox_config or {}
        self.pyttsx3_config = pyttsx3_config or {}

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = inputs.get("generate_script")
        if not script_path or not Path(script_path).exists():
            raise ValueError("Script file not found")

        script = self._load_script(Path(script_path))
        self.logger.info(f"Loaded script", segments=len(script.segments))

        tts_chain = ProviderChain([
            VOICEVOXProvider(**self.voicevox_config),
            Pyttsx3Provider(**self.pyttsx3_config)
        ])

        audio_segments = []
        for i, segment in enumerate(script.segments):
            self.logger.info(f"Synthesizing segment {i+1}/{len(script.segments)}", speaker=segment.speaker)

            audio = tts_chain.execute(text=segment.text, speaker=segment.speaker)
            audio_segments.append(audio)

        combined_audio = sum(audio_segments[1:], audio_segments[0])

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        combined_audio.export(output_path, format="wav")

        duration_seconds = len(combined_audio) / 1000.0
        self.logger.info(
            f"Audio synthesized",
            segments=len(audio_segments),
            duration_seconds=duration_seconds,
            output_path=str(output_path)
        )

        return output_path

    def _load_script(self, script_path: Path) -> Script:
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)
