import json
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from src.steps import twitter
from src.utils.config import Config

load_dotenv()


def test_post_latest_run(tmp_path, monkeypatch):


    run_root = tmp_path / "runs"
    (run_root / "20240101_000000").mkdir(parents=True)
    latest = run_root / "20251015_183513"
    latest.mkdir()
    video = latest / "video.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=100x100:rate=1:duration=1",
            str(video),
        ],
        check=True,
    )
    metadata = latest / "metadata.json"
    metadata.write_text(
        json.dumps({"title": "タイトル", "tags": ["a", "b", "c", "d", "e", "f"]}),
        encoding="utf-8",
    )
    thumb = latest / "thumbnail.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=100x100:rate=1:duration=1",
            str(thumb),
        ],
        check=True,
    )

    config = Config.load("config/default.yaml")
    twitter_config = config.steps.twitter.model_dump()
    twitter_config["dry_run"] = False
    twitter_config["thumbnail_path"] = str(thumb)



    run_id = max(p.name for p in run_root.iterdir())
    poster = twitter.TwitterPoster(
        run_id=run_id, run_dir=run_root, twitter_config=twitter_config
    )
    output = poster.execute({"render_video": video, "analyze_metadata": metadata})
    result = json.loads(output.read_text(encoding="utf-8"))
    assert "id" in result
    assert result["text"] == "タイトル\na b c d e"
    assert "media_ids" in result