import subprocess
from io import BytesIO
from pathlib import Path
from typing import Dict

import pyttsx3
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
    ):
        self.url = url.rstrip("/")
        self.speakers = dict(speakers)
        self.manager_script = manager_script
        self.auto_start = auto_start
        if self.auto_start and self.manager_script:
            self._ensure_server()

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
        return self.speakers[speaker]

    def is_available(self) -> bool:
        response = requests.get(f"{self.url}/version")
        return response.status_code == 200

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_id = self._speaker_id(speaker)
        query = requests.post(
            f"{self.url}/audio_query",
            params={"text": text, "speaker": speaker_id},
        )
        query.raise_for_status()
        synthesis = requests.post(
            f"{self.url}/synthesis",
            params={"speaker": speaker_id},
            json=query.json(),
        )
        synthesis.raise_for_status()
        return AudioSegment.from_file(BytesIO(synthesis.content), format="wav")


class Pyttsx3Provider:
    name = "pyttsx3"

    def __init__(self, speakers: Dict[str, Dict] | None = None):
        self.speakers = speakers or {
            "春日部つむぎ": {"rate": 140},
            "ずんだもん": {"rate": 160},
            "玄野武宏": {"rate": 150},
        }
        self._engine = None

    def is_available(self) -> bool:
        return True

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_config = self.speakers[speaker]
        self._ensure_engine()
        temp_path = Path(f"/tmp/pyttsx3_{speaker}_{hash(text)}.wav")
        self._engine.setProperty("rate", speaker_config["rate"])
        self._engine.save_to_file(text, str(temp_path))
        self._engine.runAndWait()
        audio = AudioSegment.from_wav(temp_path)
        temp_path.unlink(missing_ok=True)
        return audio

    def _ensure_engine(self) -> None:
        if self._engine:
            return
        self._engine = pyttsx3.init()
        self._engine.stop()
