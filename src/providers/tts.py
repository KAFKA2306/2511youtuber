import requests
import pyttsx3
from pathlib import Path
from typing import Dict
from pydub import AudioSegment
from src.providers.base import Provider
from src.utils.logger import get_logger


logger = get_logger(__name__)


class VOICEVOXProvider(Provider):
    name = "voicevox"
    priority = 1

    def __init__(self, url: str = "http://localhost:50021", speakers: Dict[str, int] = None):
        self.url = url
        self.speakers = speakers or {"田中": 11, "鈴木": 8, "ナレーター": 3}

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.url}/version", timeout=2)
            return response.status_code == 200
        except:
            return False

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_id = self.speakers.get(speaker, 3)

        query_response = requests.post(
            f"{self.url}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=10
        )
        query_response.raise_for_status()
        query_data = query_response.json()

        synthesis_response = requests.post(
            f"{self.url}/synthesis",
            params={"speaker": speaker_id},
            json=query_data,
            timeout=30
        )
        synthesis_response.raise_for_status()

        temp_path = Path(f"/tmp/voicevox_{speaker}_{hash(text)}.wav")
        with open(temp_path, "wb") as f:
            f.write(synthesis_response.content)

        audio = AudioSegment.from_wav(temp_path)
        temp_path.unlink()

        logger.info(f"VOICEVOX synthesis completed", speaker=speaker, duration_ms=len(audio))
        return audio


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
