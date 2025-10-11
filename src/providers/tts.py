import subprocess
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
    ):
        self.url = url.rstrip("/")
        self.speakers = dict(speakers)
        self.manager_script = manager_script
        self.auto_start = auto_start
        self.alias_ids = self._build_alias_ids(aliases or {})
        if self.auto_start and self.manager_script:
            self._ensure_server()

    def _build_alias_ids(self, aliases: Dict[str, List[str]]) -> Dict[str, int]:
        mapping = {name: speaker_id for name, speaker_id in self.speakers.items()}
        for canonical, alias_list in aliases.items():
            speaker_id = self.speakers.get(canonical)
            if speaker_id is None:
                continue
            for alias in alias_list:
                mapping[alias] = speaker_id
        return {key.strip(): value for key, value in mapping.items()}

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
        key = speaker.strip()
        if key in self.alias_ids:
            return self.alias_ids[key]
        for alias, speaker_id in self.alias_ids.items():
            if key.startswith(alias):
                return speaker_id
        return self.alias_ids[key]

    def is_available(self) -> bool:
        response = requests.get(f"{self.url}/version")
        return response.status_code == 200

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_id = self._speaker_id(speaker)
        query = requests.post(
            f"{self.url}/audio_query",
            params={"text": text, "speaker": speaker_id},
        )
        synthesis = requests.post(
            f"{self.url}/synthesis",
            params={"speaker": speaker_id},
            json=query.json(),
        )
        return AudioSegment.from_file(BytesIO(synthesis.content), format="wav")
