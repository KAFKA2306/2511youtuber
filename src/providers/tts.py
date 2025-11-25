import subprocess
import unicodedata
from difflib import get_close_matches
from io import BytesIO
from pathlib import Path
from typing import Dict, List

import requests
from pydub import AudioSegment


class VOICEVOXProvider:
    name = "voicevox"
    _bootstrapped: Dict[str, bool] = {}

    def __init__(
        self,
        url: str,
        speakers: Dict[str, int],
        manager_script: str | None = None,
        auto_start: bool = False,
        aliases: Dict[str, List[str]] | None = None,
        voice_parameters: Dict | None = None,
    ):
        self.url = url.rstrip("/")
        self.speakers = dict(speakers)
        self.manager_script = manager_script
        self.auto_start = auto_start
        self.alias_ids = self._build_alias_ids(aliases or {})
        self.voice_parameters = voice_parameters or {}
        if self.auto_start and self.manager_script:
            self._ensure_server()

    def _build_alias_ids(self, aliases: Dict[str, List[str]]) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        for name, speaker_id in self.speakers.items():
            normalised = self._normalise_key(name)
            mapping[normalised] = speaker_id
        for canonical, alias_list in aliases.items():
            speaker_id = self.speakers.get(canonical)
            if speaker_id is None:
                continue
            for alias in alias_list:
                mapping[self._normalise_key(alias)] = speaker_id
        return mapping

    def _ensure_server(self) -> None:
        script_path = Path(self.manager_script).expanduser()
        if not script_path.is_absolute():
            script_path = (Path.cwd() / script_path).resolve()
        key = str(script_path)
        if self._bootstrapped.get(key):
            return
        subprocess.run([str(script_path), "start"], check=True)
        self._bootstrapped[key] = True

    def _speaker_id(self, speaker: str) -> int:
        key = self._normalise_key(speaker)
        if key in self.alias_ids:
            return self.alias_ids[key]
        for alias, speaker_id in self.alias_ids.items():
            if key.startswith(alias):
                return speaker_id
        matches = get_close_matches(key, list(self.alias_ids.keys()), n=1, cutoff=0.75)
        if matches:
            return self.alias_ids[matches[0]]
        return self.alias_ids[key]

    def _normalise_key(self, value: str) -> str:
        key = unicodedata.normalize("NFKC", str(value or "")).strip()
        return key

    def is_available(self) -> bool:
        response = requests.get(f"{self.url}/version")
        return response.status_code == 200

    def _get_voice_params(self, speaker: str, segment_type: str | None = None) -> Dict:
        params = self.voice_parameters.get("default", {}).copy()

        if segment_type:
            type_params = self.voice_parameters.get("by_type", {}).get(segment_type, {})
            params.update(type_params)

        char_params = self.voice_parameters.get("by_character", {}).get(speaker, {})
        params.update(char_params)

        return params

    def _classify_segment_type(self, text: str) -> str:
        if "？" in text or "?" in text:
            return "question"
        elif "！" in text or "!" in text:
            return "emphasis"
        elif any(word in text for word in ["驚き", "すごい", "なんと", "実は"]):
            return "emphasis"
        else:
            return "explanation"

    def _synth(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_id = self._speaker_id(speaker)

        segment_type = kwargs.get("segment_type") or self._classify_segment_type(text)
        voice_params = self._get_voice_params(speaker, segment_type)

        query = requests.post(
            f"{self.url}/audio_query",
            params={"text": text, "speaker": speaker_id},
        )
        query_data = query.json()

        if "speedScale" in voice_params:
            query_data["speedScale"] = float(voice_params["speedScale"])
        if "intonationScale" in voice_params:
            query_data["intonationScale"] = float(voice_params["intonationScale"])
        if "pitchScale" in voice_params:
            query_data["pitchScale"] = float(voice_params["pitchScale"])
        if "volumeScale" in voice_params:
            query_data["volumeScale"] = float(voice_params["volumeScale"])

        synthesis = requests.post(
            f"{self.url}/synthesis",
            params={"speaker": speaker_id},
            json=query_data,
        )
        return AudioSegment.from_file(BytesIO(synthesis.content), format="wav")

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        if text.strip() == "(間)":
            return AudioSegment.silent(duration=500)
        if "(間)" in text:
            parts = text.split("(間)")
            audio = AudioSegment.empty()
            for index, part in enumerate(parts):
                segment = part.strip()
                if segment:
                    audio += self._synth(segment, speaker, **kwargs)
                if index < len(parts) - 1:
                    audio += AudioSegment.silent(duration=500)
            return audio
        return self._synth(text, speaker, **kwargs)
