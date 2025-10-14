from pathlib import Path
import shutil
import subprocess

import pytest
from pydub import AudioSegment

from src.steps.video import VideoRenderer
from src.providers.video_effects import TSUMUGI_OVERLAY_PATH

pytestmark = pytest.mark.unit


def test_video_renderer_generates_tsumugi_overlay_video(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    run_id = "tsumugi_overlay"
    run_dir = tmp_path
    run_path = run_dir / run_id
    run_path.mkdir(parents=True, exist_ok=True)

    audio_src = repo_root / "runs" / "20251013_083832" / "audio.wav"
    subtitles_src = repo_root / "runs" / "20251013_083832" / "subtitles.srt"
    overlay_src = repo_root / TSUMUGI_OVERLAY_PATH

    assert audio_src.is_file()
    assert subtitles_src.is_file()
    assert overlay_src.is_file()

    audio_dst = run_path / "audio.wav"
    subtitles_dst = run_path / "subtitles.srt"
    shutil.copyfile(subtitles_src, subtitles_dst)
    audio_segment = AudioSegment.from_wav(audio_src)[:5000]
    audio_segment.export(audio_dst, format="wav")

    video_config = {
        "resolution": "1280x720",
        "fps": 24,
        "codec": "libx264",
        "preset": "medium",
        "crf": 23,
        "effects": [
            {
                "type": "tsumugi_overlay",
                "image_path": str(overlay_src),
            }
        ],
    }

    renderer = VideoRenderer(run_id=run_id, run_dir=run_dir, video_config=video_config)
    output_path = renderer.execute(
        {
            "synthesize_audio": audio_dst,
            "prepare_subtitles": subtitles_dst,
        }
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    preview_path = output_path.with_name("overlay_preview.png")
    preview_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(output_path),
        "-frames:v",
        "1",
        str(preview_path),
    ]
    preview_cmd[0] = renderer._resolve_ffmpeg_binary()
    result = subprocess.run(preview_cmd, capture_output=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, preview_cmd, result.stdout, result.stderr)

    assert preview_path.exists()
