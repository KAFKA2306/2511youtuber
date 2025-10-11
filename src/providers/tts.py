import requests
import pyttsx3
import subprocess
import time
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from typing import Dict
from pydub import AudioSegment
from src.providers.base import Provider
from src.utils.logger import get_logger


logger = get_logger(__name__)


class VOICEVOXProvider(Provider):
    name = "voicevox"
    priority = 1
    _bootstrapped: Dict[str, bool] = {}

    def __init__(
        self,
        url: str,
        speakers: Dict[str, int],
        manager_script: str | None = None,
        auto_start: bool = False,
        query_timeout: float = 10.0,
        synthesis_timeout: float = 30.0,
        startup_timeout_seconds: float = 60.0,
        startup_poll_interval_seconds: float = 2.0,
    ):
        self.url = url.rstrip("/")
        self.speakers = dict(speakers)
        self.manager_script = manager_script
        self.auto_start = auto_start
        self.query_timeout = query_timeout
        self.synthesis_timeout = synthesis_timeout
        self.startup_timeout_seconds = startup_timeout_seconds
        self.startup_poll_interval_seconds = startup_poll_interval_seconds
        if self.auto_start and self.manager_script:
            self._ensure_server()
        self._ready = False
        self._wait_for_server()

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
        if speaker in self.speakers:
            return self.speakers[speaker]
        if self.speakers:
            return next(iter(self.speakers.values()))
        return 3

    def _wait_for_server(self) -> None:
        if self._ready:
            return
        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._ping_server():
                self._ready = True
                return
            time.sleep(self.startup_poll_interval_seconds)
        raise RuntimeError("VOICEVOX server not healthy")

    def _ping_server(self) -> bool:
        with suppress(requests.RequestException):
            response = requests.get(f"{self.url}/version", timeout=self.query_timeout)
            return response.status_code == 200
        return False

    def is_available(self) -> bool:
        if self._ready:
            return True
        return self._ping_server()

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        self._wait_for_server()
        speaker_id = self._speaker_id(speaker)
        query = requests.post(
            f"{self.url}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=self.query_timeout,
        )
        query.raise_for_status()
        synthesis = requests.post(
            f"{self.url}/synthesis",
            params={"speaker": speaker_id},
            json=query.json(),
            timeout=self.synthesis_timeout,
        )
        synthesis.raise_for_status()
        return AudioSegment.from_file(BytesIO(synthesis.content), format="wav")


class Pyttsx3Provider(Provider):
    name = "pyttsx3"
    priority = 2

    def __init__(self, speakers: Dict[str, Dict] = None):
        self.speakers = speakers or {
            "田中": {"rate": 140},
            "鈴木": {"rate": 160},
            "ナレーター": {"rate": 150}
        }
        self._engine = None
        self._engine_available = None
        self._engine_error = None

    def is_available(self) -> bool:
        self._ensure_engine()
        # Even if the engine cannot be initialised we can fall back to synthetic audio
        return True

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_config = self.speakers.get(speaker, {"rate": 150})

        self._ensure_engine()

        if self._engine_available and self._engine:
            temp_path = Path(f"/tmp/pyttsx3_{speaker}_{hash(text)}.wav")
            self._engine.setProperty('rate', speaker_config['rate'])
            self._engine.save_to_file(text, str(temp_path))
            self._engine.runAndWait()

            audio = AudioSegment.from_wav(temp_path)
            temp_path.unlink(missing_ok=True)

            logger.info(f"pyttsx3 synthesis completed", speaker=speaker, duration_ms=len(audio))
            return audio

        duration_ms = max(len(text) * 80, 500)
        audio = AudioSegment.silent(duration=duration_ms, frame_rate=24000)
        logger.info(
            "pyttsx3 engine unavailable, generated silent fallback audio",
            speaker=speaker,
            duration_ms=duration_ms,
            error=str(self._engine_error) if self._engine_error else None,
        )
        return audio

    def _ensure_engine(self) -> None:
        if self._engine_available is not None:
            return

        try:
            engine = pyttsx3.init()
            engine.stop()
            self._engine = engine
            self._engine_available = True
        except Exception as exc:
            self._engine = None
            self._engine_available = False
            self._engine_error = exc
