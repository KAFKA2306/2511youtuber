import sys
from pathlib import Path

import ffmpeg
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.steps.intro_outro import IntroOutroConcatenator


def _duration(path: Path) -> float:
    return float(ffmpeg.probe(str(path))["format"]["duration"])


def test_intro_outro_concat(tmp_path: Path) -> None:
    run_id = "intro_outro"
    intro = Path("assets/video/やっほー春日部紬だよー今日も見てくれてありがとう.mp4").resolve()
    outro = Path("assets/video/ありがとう.mp4").resolve()
    main_source = Path("assets/video/春日部紬だよ.mp4").resolve()
    run_dir = tmp_path
    work_main = run_dir / run_id / "video.mp4"
    work_main.parent.mkdir(parents=True, exist_ok=True)
    work_main.write_bytes(main_source.read_bytes())
    step = IntroOutroConcatenator(
        run_id=run_id,
        run_dir=run_dir,
        intro_path=str(intro),
        outro_path=str(outro),
        codec="libx264",
        preset="medium",
        crf=23,
    )
    output = step.execute({"render_video": work_main})
    assert output.exists()
    intro_duration = _duration(intro)
    main_duration = _duration(work_main)
    outro_duration = _duration(outro)
    total_duration = _duration(output)
    assert total_duration == pytest.approx(intro_duration + main_duration + outro_duration, rel=0.05)
