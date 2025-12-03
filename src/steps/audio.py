import json
from pathlib import Path
from typing import Dict, List

from pydub import AudioSegment

from src.core.step import Step
from src.models import Script
from src.providers.base import Provider


class AudioSynthesizer(Step):
    name = "synthesize_audio"
    output_filename = "audio.wav"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        tts_provider: Provider,
        voicevox_config: Dict,
        speaker_aliases: Dict[str, List[str]] | None = None,
        bgm_config: Dict | None = None,
        voice_parameters: Dict | None = None,
    ):
        super().__init__(run_id, run_dir)
        self.voicevox_config = dict(voicevox_config)
        self.speaker_aliases = speaker_aliases or {}
        self.bgm_config = bgm_config or {}
        self.voice_parameters = voice_parameters or {}
        self.provider = tts_provider

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = Path(inputs["generate_script"])
        script = self._load_script(script_path)
        segments = []
        for segment in script.segments:
            # Determine segment type for voice parameter selection
            segment_type = self._classify_segment_type(segment.text)
            seg_audio = self.provider.execute(
                text=segment.text,
                speaker=segment.speaker,
                segment_type=segment_type,
                voice_params=self.voice_parameters,
            )
            segments.append(seg_audio)
        audio = segments[0]
        for segment_audio in segments[1:]:
            audio += segment_audio

        if self.bgm_config.get("enabled"):
            audio = self._mix_bgm(audio)

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(output_path, format="wav")
        return output_path

    def _classify_segment_type(self, text: str) -> str:
        if "？" in text or "?" in text:
            return "question"
        if "！" in text or "!" in text:
            return "emphasis"
        if any(word in text for word in ["驚き", "すごい", "なんと", "実は"]):
            return "emphasis"
        return "explanation"

    def _mix_bgm(self, voice_audio: AudioSegment) -> AudioSegment:
        bgm_file = self.bgm_config.get("file")
        if not bgm_file:
            return voice_audio

        bgm_path = Path(bgm_file)
        if not bgm_path.exists():
            return voice_audio

        bgm = AudioSegment.from_file(str(bgm_path))
        volume_ratio = float(self.bgm_config.get("volume", 0.15))
        bgm_volume_db = bgm.dBFS + (20 * (volume_ratio - 1))

        voice_duration_ms = len(voice_audio)
        if len(bgm) < voice_duration_ms:
            repeat_count = (voice_duration_ms // len(bgm)) + 1
            bgm = bgm * repeat_count

        bgm = bgm[:voice_duration_ms]
        bgm = bgm + (bgm_volume_db - bgm.dBFS)
        return voice_audio.overlay(bgm)

    def _load_script(self, script_path: Path) -> Script:
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)
