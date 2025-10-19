import json
import sys
from pathlib import Path

import ffmpeg
from PIL import Image
from pydub import AudioSegment

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.core.media_utils import find_ffmpeg_binary
from src.providers.video_effects import OverlayEffect, _overlay_position
from src.steps.subtitle import SubtitleFormatter
from src.steps.video import VideoRenderer
from src.utils.config import Config


def test_static_frame_layout(tmp_path) -> None:
    config = Config.load()
    video_cfg = config.steps.video
    subtitle_cfg = config.steps.subtitle
    style_cfg = video_cfg.subtitles
    width, height = map(int, video_cfg.resolution.split("x"))
    margin_l = int(style_cfg.margin_l or 0)
    margin_r = int(style_cfg.margin_r or 0)
    margin_v = int(style_cfg.margin_v or 0)
    formatter = SubtitleFormatter(
        "layout",
        Path(tmp_path),
    )
    safe_width = formatter.wrap_width_pixels
    sample_text = "市場の反応が読めないときほど冷静さが問われます。長期的な視点で投資判断を行いましょう。"
    lines = [line for line in formatter._wrap_text(sample_text) if line]
    assert lines
    widths = [formatter._text_width(line) for line in lines]
    assert max(widths) <= safe_width
    font = formatter._load_font()
    ascent, descent = font.getmetrics() if font else (formatter.width_per_char_pixels, 0)
    line_height = ascent + descent
    subtitle_boxes = []
    subtitle_layout = []
    total_lines = len(lines)
    for index, line in enumerate(lines):
        offset = total_lines - 1 - index
        bottom = height - margin_v - offset * line_height
        top = bottom - line_height
        line_width = formatter._text_width(line)
        left = margin_l + (safe_width - line_width) / 2
        right = left + line_width
        subtitle_boxes.append((left, top, right, bottom))
        subtitle_layout.append((line, left, top))
        assert left >= margin_l
        assert right <= width - margin_r
        assert top >= 0
    overlays = []
    for effect_cfg in video_cfg.effects:
        if effect_cfg.type not in {"overlay", "tsumugi_overlay"}:
            continue
        params = {
            "image_path": effect_cfg.image_path,
            "anchor": effect_cfg.anchor,
            "height_ratio": effect_cfg.height_ratio,
            "width_ratio": effect_cfg.width_ratio,
            "height": effect_cfg.height,
            "width": effect_cfg.width,
            "offset": effect_cfg.offset.model_dump() if effect_cfg.offset else None,
        }
        effect = OverlayEffect(**params)
        with Image.open(effect.image_path) as source:
            orig_w, orig_h = source.size
        overlay_w, overlay_h = effect._dimensions(orig_w, orig_h, width, height)
        pos_x, pos_y = _overlay_position((width, height), (overlay_w, overlay_h), effect.anchor, params["offset"])
        overlay_box = (float(pos_x), float(pos_y), float(pos_x + overlay_w), float(pos_y + overlay_h))
        assert 0 <= overlay_box[0] < overlay_box[2] <= width
        assert 0 <= overlay_box[1] < overlay_box[3] <= height
        overlays.append((effect.image_path, overlay_box))
    output_dir = Path("runs") / "video_0sec_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    layout = {
        "subtitles": [
            {
                "index": index,
                "text": subtitle_layout[index][0],
                "box": [
                    int(round(subtitle_boxes[index][0])),
                    int(round(subtitle_boxes[index][1])),
                    int(round(subtitle_boxes[index][2])),
                    int(round(subtitle_boxes[index][3])),
                ],
            }
            for index in range(len(subtitle_boxes))
        ],
        "overlays": [
            {
                "image": image_path,
                "box": [int(round(value)) for value in box],
            }
            for image_path, box in overlays
        ],
    }
    with open(output_dir / "layout.json", "w", encoding="utf-8") as target:
        json.dump(layout, target, ensure_ascii=True, indent=2)
    duration_ms = 4000
    audio_path = output_dir / "silence.wav"
    AudioSegment.silent(duration=duration_ms).export(audio_path, format="wav")
    subtitle_path = output_dir / "subtitles.srt"
    timestamps = [{"start": 0.0, "end": duration_ms / 1000.0, "text": sample_text}]
    subtitle_content = formatter._generate_srt(timestamps)
    with open(subtitle_path, "w", encoding="utf-8") as target:
        target.write(subtitle_content)
    renderer = VideoRenderer("video_0sec_test", output_dir, video_cfg.model_dump())
    video_path = renderer.execute({
        "synthesize_audio": audio_path,
        "prepare_subtitles": subtitle_path,
    })
    snapshot_path = output_dir / "static_frame.png"
    (
        ffmpeg.input(str(video_path), ss=0)
        .output(str(snapshot_path), vframes=1)
        .overwrite_output()
        .run(cmd=find_ffmpeg_binary(), capture_stdout=True, capture_stderr=True)
    )
    assert snapshot_path.exists()
