import json
import sys
import types
from pathlib import Path

tweepy_stub = types.ModuleType("tweepy")
tweepy_stub.OAuth1UserHandler = lambda *args, **kwargs: None
tweepy_stub.API = lambda auth: types.SimpleNamespace(
    media_upload=lambda *args, **kwargs: types.SimpleNamespace(media_id_string="1"),
    update_status=lambda *args, **kwargs: types.SimpleNamespace(id_str="1", text=""),
)
sys.modules.setdefault("tweepy", tweepy_stub)

from src.steps import twitter


def test_post_latest_run(tmp_path, monkeypatch):
    run_root = tmp_path / "runs"
    (run_root / "20240101_000000").mkdir(parents=True)
    latest = run_root / "20251015_183513"
    latest.mkdir()
    video = latest / "video.mp4"
    video.write_bytes(b"v")
    metadata = latest / "metadata.json"
    metadata.write_text(json.dumps({"title": "タイトル", "tags": ["a", "b", "c", "d", "e", "f"]}), encoding="utf-8")
    thumb = latest / "thumbnail.png"
    thumb.write_bytes(b"i")
    calls = {}

    class Dummy:
        def post(self, text, video_path, image_path):
            calls["text"] = text
            calls["video"] = video_path
            calls["image"] = image_path
            return {"status": text}

    dummy = Dummy()
    monkeypatch.setattr(twitter.TwitterClient, "from_config", classmethod(lambda cls, config, dry_run: dummy))
    monkeypatch.setattr(twitter.subprocess, "run", lambda cmd, check: Path(cmd[-1]).write_bytes(b"c"))
    run_id = max(p.name for p in run_root.iterdir())
    poster = twitter.TwitterPoster(run_id=run_id, run_dir=run_root, twitter_config={"dry_run": True, "thumbnail_path": str(thumb)})
    output = poster.execute({"render_video": video, "analyze_metadata": metadata})
    assert calls["text"] == "タイトル\na b c d e"
    assert calls["video"] == latest / "twitter_clip.mp4"
    assert calls["image"] == thumb
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "タイトル\na b c d e"}
