import shutil
from pathlib import Path

from pydub import AudioSegment


def get_audio_duration(path: Path) -> float:
    audio = AudioSegment.from_wav(path)
    return len(audio) / 1000.0


def find_ffmpeg_binary() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise FileNotFoundError("FFmpeg executable not found in PATH")
    return binary


def sanitize_path_for_ffmpeg(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:")
