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

    def is_available(self) -> bool:
        try:
            engine = pyttsx3.init()
            engine.stop()
            return True
        except:
            return False

    def execute(self, text: str, speaker: str, **kwargs) -> AudioSegment:
        speaker_config = self.speakers.get(speaker, {"rate": 150})

        engine = pyttsx3.init()
        engine.setProperty('rate', speaker_config['rate'])

        temp_path = Path(f"/tmp/pyttsx3_{speaker}_{hash(text)}.wav")
        engine.save_to_file(text, str(temp_path))
        engine.runAndWait()

        audio = AudioSegment.from_wav(temp_path)
        temp_path.unlink()

        logger.info(f"pyttsx3 synthesis completed", speaker=speaker, duration_ms=len(audio))
        return audio
