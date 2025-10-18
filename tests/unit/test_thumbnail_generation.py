import json
from pathlib import Path
import tempfile
from src.steps.thumbnail import ThumbnailGenerator

run_dir = Path("/home/kafka/projects/2510youtuber/youtube-ai-v2/runs/20251017_170002")
metadata_path = run_dir / "metadata.json"
script_path = run_dir / "script.json"

with open(metadata_path) as f:
    metadata = json.load(f)

print(f"Title from metadata: {metadata['title']}")

with tempfile.TemporaryDirectory() as tmpdir:
    output_dir = Path(tmpdir)

    config = {
        "enabled": True,
        "width": 1280,
        "height": 720,
        "background_color": "#000000",
        "title_color": "#FFD700",
        "padding": 80,
        "max_lines": 4,
        "max_chars_per_line": 12,
        "title_font_size": 96,
        "font_path": "assets/fonts/ZenMaruGothic-Bold.ttf",
        "right_guard_band_px": 400,
        "outline_inner_color": "#EB001B",
        "outline_inner_width": 2,
        "outline_outer_color": "#000000",
        "outline_outer_width": 5,
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

    generator = ThumbnailGenerator(run_id="test", run_dir=output_dir, thumbnail_config=config)

    inputs = {
        "generate_script": str(script_path),
        "analyze_metadata": str(metadata_path)
    }

    output_path = generator.execute(inputs)
    print(f"Thumbnail generated at: {output_path}")

    import shutil
    dest = Path("test_thumbnail_output.png")
    shutil.copy(output_path, dest)
    print(f"Copied to: {dest.absolute()}")
