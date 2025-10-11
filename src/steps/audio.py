import json
from pathlib import Path
from typing import Dict, List

from src.models import Script
from src.providers.base import execute_with_fallback
from src.providers.tts import Pyttsx3Provider, VOICEVOXProvider
from src.steps.base import Step


class AudioSynthesizer(Step):
    name = "synthesize_audio"
    output_filename = "audio.wav"

    def __init__(
        self, run_id: str, run_dir: Path, voicevox_config: Dict | None = None, pyttsx3_config: Dict | None = None
    ):
        super().__init__(run_id, run_dir)
        self.voicevox_config = voicevox_config or {}
        self.pyttsx3_config = pyttsx3_config or {}

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = Path(inputs["generate_script"])
        script = self._load_script(script_path)
        if not script.segments:
            raise ValueError("Script contains no segments")

        providers = self._build_providers()
        audio_segments = [
            execute_with_fallback(providers, text=segment.text, speaker=segment.speaker) for segment in script.segments
        ]

        combined_audio = audio_segments[0]
        for segment_audio in audio_segments[1:]:
            combined_audio += segment_audio

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_audio.export(output_path, format="wav")
        return output_path

    def _load_script(self, script_path: Path) -> Script:
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)

    def _build_providers(self) -> List:
        providers = []
        if self.voicevox_config:
            providers.append(VOICEVOXProvider(**self.voicevox_config))
        providers.append(Pyttsx3Provider(**self.pyttsx3_config))
        return providers
