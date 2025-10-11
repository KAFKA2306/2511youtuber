#!/usr/bin/env python3
import json
from pathlib import Path

from PIL import Image, ImageDraw

from src.steps.thumbnail import ThumbnailGenerator
from src.utils.config import Config


def ensure_character_asset(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (2048, 4096), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((512, 256, 1536, 1280), fill=(239, 71, 111, 255))
    draw.rectangle((768, 1280, 1280, 3584), fill=(25, 61, 90, 255))
    image.save(path)


def prepare_script(path: Path) -> Path:
    data = {
        "segments": [
            {"speaker": "春日部つむぎ", "text": "本日のマーケットトピックをお届けします。"},
            {"speaker": "ずんだもん", "text": "注目の指標と為替の動きをチェックします。"},
            {"speaker": "玄野武宏", "text": "投資家が押さえるべきポイントを整理します。"},
        ],
        "total_duration_estimate": 180.0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def run_thumbnail_test() -> Path:
    config = Config.load("config/default.yaml")
    thumbnail_config = config.steps.thumbnail.model_dump()
    overlays = thumbnail_config.get("overlays") or []
    for overlay in overlays:
        if not overlay.get("enabled", True):
            continue
        overlay_path = overlay.get("image_path") or overlay.get("path")
        if overlay_path:
            ensure_character_asset(Path(overlay_path))
    run_dir = Path("output")
    run_id = "thumbnail_test"
    script_path = prepare_script(run_dir / run_id / "script.json")
    step = ThumbnailGenerator(run_id=run_id, run_dir=run_dir, thumbnail_config=thumbnail_config)
    output_path = step.run({"generate_script": script_path})
    return output_path


if __name__ == "__main__":
    result = run_thumbnail_test()
    print("generated", result)
