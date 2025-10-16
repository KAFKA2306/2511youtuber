from pathlib import Path
from src.steps.thumbnail import ThumbnailGenerator
from src.utils.config import Config
import json

config = Config.load()
run_dir = Path("runs")
run_id = "thumbnail_test"

test_path = run_dir / run_id
test_path.mkdir(parents=True, exist_ok=True)

script_data = {
    "segments": [
        {"speaker": "春日部つむぎ", "text": "金融市場最新速報", "timestamp": 0.0}
    ]
}
with open(test_path / "script.json", "w", encoding="utf-8") as f:
    json.dump(script_data, f, ensure_ascii=False)

metadata_data = {
    "title": "日銀金融政策決定会合の影響分析",
    "description": "最新の金融政策が市場に与える影響を徹底解説"
}
with open(test_path / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata_data, f, ensure_ascii=False)

step = ThumbnailGenerator(
    run_id=run_id,
    run_dir=run_dir,
    thumbnail_config=config.steps.thumbnail.model_dump()
)

output_path = step.run({
    "generate_script": test_path / "script.json",
    "analyze_metadata": test_path / "metadata.json"
})

print(f"サムネイル生成完了: {output_path}")
print(f"絶対パス: {output_path.absolute()}")
