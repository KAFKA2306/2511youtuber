# Thumbnail

## Step
- Implementation sits in `src/steps/thumbnail.py`, where `ThumbnailGenerator` (`src/steps/thumbnail.py:69`) extends `Step` (`src/core/step.py:12`) and writes `run_dir/run_id/thumbnail.png` via `Step.get_output_path` (`src/core/step.py:21`).
- Palette randomisation uses `cfg.get("randomize_palette", True)` (`src/steps/thumbnail.py:77`) and `PRESETS` (`src/steps/thumbnail.py:14`). When true it samples with `random.choice`, otherwise it honours explicit `palettes` or `presets` entries in the provided config (`src/steps/thumbnail.py:58`).
- `PRESETS` bundles five dictionaries consumed by `_palette_candidates`:
  - `{'background_color': '#fef155', 'title_color': '#EB001B', 'outline_inner_color': '#FFFFFF', 'outline_inner_width': 30, 'outline_outer_color': '#000000', 'outline_outer_width': 0}` (`src/steps/thumbnail.py:14`).
  - `{'background_color': '#000000', 'title_color': '#FFD700', 'outline_inner_color': '#EB001B', 'outline_inner_width': 30, 'outline_outer_color': '#000000', 'outline_outer_width': 0}` (`src/steps/thumbnail.py:23`).
  - `{'background_color': '#0B0F19', 'title_color': '#FFE16A', 'outline_inner_color': '#FFFFFF', 'outline_inner_width': 15, 'outline_outer_color': '#000000', 'outline_outer_width': 0}` (`src/steps/thumbnail.py:31`).
  - `{'background_color': '#111827', 'title_color': '#FDE047', 'outline_inner_color': '#FFFFFF', 'outline_inner_width': 15, 'outline_outer_color': '#0B0F19', 'outline_outer_width': 0}` (`src/steps/thumbnail.py:39`).
  - `{'background_color': '#0A0F1F', 'title_color': '#FFD700', 'outline_inner_color': '#FFFFFF', 'outline_inner_width': 15, 'outline_outer_color': '#000000', 'outline_outer_width': 0}` (`src/steps/thumbnail.py:47`).
- `execute` reads script and metadata inputs from `inputs["generate_script"]` and `inputs.get("analyze_metadata")` using `load_script` (`src/core/io_utils.py:17`) and `load_json` (`src/core/io_utils.py:10`), then renders text and overlays through `_render_text`, `_wrap_text`, `_prepare_overlays`, `_scale_overlay`, `_resolve_position`, and `_text_width` (`src/steps/thumbnail.py:198`, `src/steps/thumbnail.py:227`, `src/steps/thumbnail.py:149`, `src/steps/thumbnail.py:163`, `src/steps/thumbnail.py:179`, `src/steps/thumbnail.py:250`).
- Title and subtitle resolution prefer metadata fields before script segments (`src/steps/thumbnail.py:128`, `src/steps/thumbnail.py:133`), defaulting to Japanese fallbacks when inputs are missing.

## Configuration
- Default runtime settings live in `config/default.yaml:80`, providing `enabled`, `width`, `height`, `background_color`, `title_color`, `subtitle_color`, `show_subtitle`, `padding`, `max_lines`, `max_chars_per_line`, `title_font_size`, `subtitle_font_size`, `font_path`, `right_guard_band_px`, `outline_inner_color`, `outline_inner_width`, `outline_outer_color`, `outline_outer_width`, and overlay definitions referencing `assets/春日部つむぎ立ち絵公式_v2.0/春日部つむぎ立ち絵公式_v1.1.1.png` plus `assets/icon2510youtuber-mini.png`.
- Schema objects `ThumbnailOverlayOffsetConfig`, `ThumbnailOverlayConfig`, and `ThumbnailStepConfig` reside in `src/utils/config.py:150`, `src/utils/config.py:157`, and `src/utils/config.py:169`. These models accept optional `randomize_palette`, `palettes`, `presets`, per-overlay dimensions (`height_ratio`, `width_ratio`, `height`, `width`), and positional offsets.
- The CLI wires the step by passing `config.steps.thumbnail.model_dump()` when `config.steps.thumbnail.enabled` evaluates to true (`apps/youtube/cli.py:132`). This keeps thumbnail generation after metadata analysis within the orchestrator list.

## Downstream Usage
- YouTube uploads request the generated thumbnail path through `inputs.get("generate_thumbnail")` in `src/steps/youtube.py:46`, falling back to `None` when the file is absent or empty before invoking `YouTubeClient.upload` (`src/providers/youtube.py:102`).
- `YouTubeClient.upload` validates the path, logs dry-run metadata with the optional thumbnail entry during non-upload runs, and attaches the PNG via the API when available (`src/providers/youtube.py:137`).
- Alternate surfaces can reference thumbnails through `TwitterStepConfig.thumbnail_path` in `src/utils/config.py:207` for social clip workflows.

## Validation
- `tests/unit/test_thumbnail_generation.py:1` instantiates `ThumbnailGenerator` with an inline config mirroring `config/default.yaml` values, executes against fixture outputs under `/runs/`, and copies the resulting `thumbnail.png` to `test_thumbnail_output.png` for inspection.
