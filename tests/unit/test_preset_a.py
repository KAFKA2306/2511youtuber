from pathlib import Path
from src.steps.thumbnail import ThumbnailGenerator
import json

run_dir = Path("runs")
run_id = "preset_a_test"
test_path = run_dir / run_id
test_path.mkdir(parents=True, exist_ok=True)

script_data = {"segments": [{"speaker": "春日部つむぎ", "text": "金融市場最新速報", "timestamp": 0.0}]}
with open(test_path / "script.json", "w", encoding="utf-8") as f:
    json.dump(script_data, f, ensure_ascii=False)

metadata_data = {"title": "日銀金融政策決定会合", "description": "最新の金融政策"}
with open(test_path / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata_data, f, ensure_ascii=False)

manual_preset_a = {
    "enabled": True,
    "width": 1280,
    "height": 720,
    "background_color": "#fef155",
    "title_color": "#EB001B",
    "outline_inner_color": "#FFFFFF",
    "outline_inner_width": 3,
    "outline_outer_color": "#000000",
    "outline_outer_width": 6,
    "padding": 80,
    "max_lines": 3,
    "max_chars_per_line": 12,
    "title_font_size": 96,
    "subtitle_font_size": 56,
    "show_subtitle": False,
    "font_path": "assets/fonts/ZenMaruGothic-Bold.ttf",
    "right_guard_band_px": 400,
    "overlays": [
        {
            "name": "character",
            "enabled": True,
            "image_path": "assets/春日部つむぎ立ち絵公式_v2.0/春日部つむぎ立ち絵公式_v1.1.1.png",
            "anchor": "bottom_right",
            "height_ratio": 0.85,
            "offset": {"right": 20, "bottom": 0}
        }
    ]
}

step = ThumbnailGenerator(run_id=run_id, run_dir=run_dir, thumbnail_config=manual_preset_a)

print(f"背景色設定: {step.background_color}")
print(f"文字色設定: {step.title_color}")

output_path = step.run({
    "generate_script": test_path / "script.json",
    "analyze_metadata": test_path / "metadata.json"
})

print(f"生成完了: {output_path.absolute()}")

from PIL import Image
img = Image.open(output_path)
pixels = img.load()
bg_pixel = pixels[10, 10]
print(f"実際の背景RGB: {bg_pixel}")
