from pathlib import Path
from src.steps.thumbnail import ThumbnailGenerator
from src.utils.config import Config
import json

config = Config.load()
run_dir = Path("runs")

for i in range(10):
    run_id = f"final_test_{i}"
    test_path = run_dir / run_id
    test_path.mkdir(parents=True, exist_ok=True)

    script_data = {"segments": [{"speaker": "春日部つむぎ", "text": "金融市場最新速報", "timestamp": 0.0}]}
    with open(test_path / "script.json", "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False)

    metadata_data = {"title": "日銀金融政策決定会合の影響分析", "description": "最新の金融政策"}
    with open(test_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata_data, f, ensure_ascii=False)

    step = ThumbnailGenerator(run_id=run_id, run_dir=run_dir, thumbnail_config=config.steps.thumbnail.model_dump())

    output_path = step.run({"generate_script": test_path / "script.json", "analyze_metadata": test_path / "metadata.json"})

    from PIL import Image
    img = Image.open(output_path)
    px = img.load()
    bg_pixel = px[10, 10]

    preset_name = "A(黄)" if bg_pixel[0] > 200 and bg_pixel[1] > 200 and bg_pixel[2] < 100 else "B(黒)"

    print(f"{i+1}: {preset_name} | 背景={step.background_color} 文字={step.title_color} 内縁={step.outline_inner_color}({step.outline_inner_width}px) 外縁={step.outline_outer_width}px | {output_path.name}")
