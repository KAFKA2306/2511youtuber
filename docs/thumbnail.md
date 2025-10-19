# Thumbnail

## Step
- `ThumbnailGenerator` (`src/steps/thumbnail.py:69`) extends `Step` and declares `name="generate_thumbnail"`, `output_filename="thumbnail.png"`, `is_required=False`; `execute` builds the image from script and metadata inputs and writes the PNG when `self.enabled` is true (`src/steps/thumbnail.py:100`).
- Palette selection pulls `random.choice` from `PRESETS` unless `thumbnail_config` supplies `palettes` or `presets` (`src/steps/thumbnail.py:14`, `src/steps/thumbnail.py:58`), populating fields such as `background_color`, `title_color`, and stroke widths (`src/steps/thumbnail.py:82`).
- Text and overlays rely on `_resolve_title`, `_resolve_subtitle`, `_render_text`, `_wrap_text`, `_prepare_overlays`, `_scale_overlay`, `_resolve_position`, and `_text_width` to lay out typography and images (`src/steps/thumbnail.py:128`, `src/steps/thumbnail.py:133`, `src/steps/thumbnail.py:198`, `src/steps/thumbnail.py:227`, `src/steps/thumbnail.py:149`, `src/steps/thumbnail.py:163`, `src/steps/thumbnail.py:179`, `src/steps/thumbnail.py:250`).
- External helpers `load_script` and `load_json` source `Script` segments and metadata (`src/core/io_utils.py:10`, `src/core/io_utils.py:17`; `src/models.py:14`).

## Configuration
- Default values live under `config/default.yaml:80`, defining canvas size, color palette, typography, `show_subtitle`, `right_guard_band_px`, stroke widths, and overlay entries that point at `assets/春日部つむぎ立ち絵公式_v2.0/春日部つむぎ立ち絵公式_v1.1.1.png` and `assets/icon2510youtuber-mini.png`.
- Runtime schema `ThumbnailStepConfig` and `ThumbnailOverlayConfig` (`src/utils/config.py:157`, `src/utils/config.py:169`) keep overlay dimensions (`height_ratio`, `width_ratio`, `height`, `width`) and offsets (`ThumbnailOverlayOffsetConfig`) while allowing extra palette keys via `model_config = ConfigDict(extra="allow")`.
- The CLI injects `config.steps.thumbnail.model_dump()` when `config.steps.thumbnail.enabled` is true, ensuring orchestrator order after metadata (`apps/youtube/cli.py:132`).
- Downstream consumers: `YouTubeUploader.execute` requests the generated path from `inputs` and nulls empty files (`src/steps/youtube.py:46`), while `YouTubeClient.upload` validates the file, handles dry-run metadata, and submits the thumbnail to the API (`src/providers/youtube.py:102`, `src/providers/youtube.py:137`). `TwitterStepConfig.thumbnail_path` enables alternate thumbnails for social clips (`src/utils/config.py:207`).

## Validation
- `tests/unit/test_thumbnail_generation.py:4` spins up `ThumbnailGenerator` with the default-like config to emit `thumbnail.png`, copying it to `test_thumbnail_output.png` for manual review.
