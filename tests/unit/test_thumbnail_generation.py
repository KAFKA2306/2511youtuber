import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.steps.thumbnail import PRESETS, ThumbnailGenerator


def test_generate_thumbnails_for_presets(tmp_path):
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    script_path = inputs_dir / "script.json"
    metadata_path = inputs_dir / "metadata.json"
    script_path.write_text(json.dumps({"segments": [{"speaker": "A", "text": "速報タイトル"}, {"speaker": "B", "text": "サブタイトル"}]}))
    metadata_path.write_text(json.dumps({"title": "金融速報", "description": "解説\n詳細"}))
    run_dir = Path("runs/thumbnail_test")
    run_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, preset in enumerate(PRESETS):
        run_id = f"preset_{index}"
        config = {
            "enabled": True,
            "randomize_palette": False,
            "width": 1280,
            "height": 720,
            "show_subtitle": True,
            "padding": 80,
            "max_lines": 4,
            "max_chars_per_line": 12,
            "title_font_size": 96,
            "subtitle_font_size": 56,
            "font_path": "assets/fonts/ZenMaruGothic-Bold.ttf",
            "overlays": [],
        }
        config.update(preset)
        generator = ThumbnailGenerator(run_id=run_id, run_dir=run_dir, thumbnail_config=config)
        output = generator.execute({
            "generate_script": str(script_path),
            "analyze_metadata": str(metadata_path),
        })
        outputs.append({"index": index, "path": str(output), "palette": preset})
    log_path = run_dir / "results.json"
    log_path.write_text(json.dumps(outputs, ensure_ascii=False, indent=2))
    for item in outputs:
        expected = run_dir / f"preset_{item['index']}" / "thumbnail.png"
        assert Path(item["path"]) == expected
        assert expected.exists()
    assert log_path.exists()
