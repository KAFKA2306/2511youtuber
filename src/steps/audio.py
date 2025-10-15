import json
from pathlib import Path
from typing import Dict, List

from src.core.step import Step
from src.models import Script
from src.providers.tts import VOICEVOXProvider


class AudioSynthesizer(Step):
    name = "synthesize_audio"
    output_filename = "audio.wav"

    def __init__(
        self, run_id: str, run_dir: Path, voicevox_config: Dict, speaker_aliases: Dict[str, List[str]] | None = None
    ):
        super().__init__(run_id, run_dir)
        self.voicevox_config = dict(voicevox_config)
        self.speaker_aliases = speaker_aliases or {}
        self.provider = VOICEVOXProvider(**self.voicevox_config, aliases=self.speaker_aliases)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = Path(inputs["generate_script"])
        script = self._load_script(script_path)
        segments = [self.provider.execute(text=segment.text, speaker=segment.speaker) for segment in script.segments]
        audio = segments[0]
        for segment_audio in segments[1:]:
            audio += segment_audio
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(output_path, format="wav")
        return output_path

    def _load_script(self, script_path: Path) -> Script:
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)
