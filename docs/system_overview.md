# System Overview

## Purpose
YouTube AI Video Generator v2 turns up-to-date financial news into narrated Japanese videos with subtitles and optional distribution assets. The YouTube app entry point (`src/main.py`) loads environment variables, parses an optional news query, and delegates execution to `apps.youtube.run` so that the workflow can be driven from the command line or scheduled automation.【F:src/main.py†L1-L25】【F:apps/youtube/cli.py†L24-L47】

## Workflow orchestration
The `apps.youtube` runner constructs a timestamped `run_id`, resolves the configured output directory, and instantiates all enabled steps before handing them to `WorkflowOrchestrator`. The orchestrator resumes from checkpoints when artifacts already exist, persists a JSON `state.json` file after each step, and reports run metadata when complete.【F:apps/youtube/cli.py†L29-L111】【F:src/core/orchestrator.py†L1-L30】【F:src/core/state.py†L1-L41】

Each step subclasses `src.core.step.Step`, which standardises output locations under `<run_dir>/<run_id>/` and protects downstream consumers by ensuring the declared artifact exists. Failed optional steps (such as thumbnail generation or social posting) can be omitted because the `is_required` flag defaults to `False` only where the pipeline tolerates absence.【F:src/core/step.py†L1-L33】【F:src/steps/thumbnail.py†L40-L59】【F:apps/youtube/cli.py†L64-L111】

### Default pipeline
| Order | Step | Responsibility | Output |
| --- | --- | --- | --- |
| 1 | `NewsCollector` | Query Perplexity and Gemini news providers with fallback logic to gather recent finance stories. | `news.json` |
| 2 | `ScriptGenerator` | Prompt Gemini with collected headlines, speaker profiles, and carry-over notes to produce a structured dialogue script. | `script.json` |
| 3 | `AudioSynthesizer` | Use VOICEVOX to synthesise each script segment and concatenate them into a single WAV file. | `audio.wav` |
| 4 | `SubtitleFormatter` | Estimate per-line timing by text length and wrap Japanese text to fit the configured on-screen width, emitting SRT captions. | `subtitles.srt` |
| 5 | `VideoRenderer` | Render an FFmpeg colour source with Ken Burns overlays, apply optional image overlays, and burn in subtitles while muxing audio. | `video.mp4` |
| 6 | `IntroOutroConcatenator` (config gated) | Prepend and append branded clips around the rendered video when `steps.video.intro_outro.enabled` is true. | `video_intro_outro.mp4` |

【F:src/steps/news.py†L1-L48】【F:src/providers/base.py†L1-L38】【F:src/steps/script.py†L1-L130】【F:src/steps/audio.py†L1-L36】【F:src/steps/subtitle.py†L1-L72】【F:src/steps/video.py†L1-L63】【F:src/steps/intro_outro.py†L1-L76】

### Optional extensions
Additional artefacts are generated when the corresponding configuration flags are enabled:

- `MetadataAnalyzer` summarises the script (and optionally LLM output) into SEO metadata before truncating to YouTube limits.【F:src/steps/metadata.py†L1-L83】
- `ThumbnailGenerator` samples preset colour palettes, renders the script headline, and composites configured overlay images.【F:src/steps/thumbnail.py†L1-L119】
- `YouTubeUploader`, `TwitterPoster`, `PodcastExporter`, and `BuzzsproutUploader` publish deliverables using provider clients when their configs are enabled.【F:apps/youtube/cli.py†L64-L111】

## Configuration
`Config.load` reads `config/default.yaml`, validates strongly typed step/provider settings, and exposes helper methods for secret resolution and prompt loading. Each step consumes only the portion of the config it needs (e.g., speaker aliases, subtitle width, intro/outro clip toggles, video effects), keeping runtime behaviour transparent.【F:src/utils/config.py†L1-L204】【F:config/default.yaml†L1-L159】

The config file also declares provider endpoints (VOICEVOX server URL, Gemini models, Perplexity options) and workflow defaults such as checkpoint output directories and logging format.【F:config/default.yaml†L1-L168】【F:src/utils/config.py†L204-L257】

## External dependencies
- **Gemini & Perplexity** — `NewsCollector`, `ScriptGenerator`, and `MetadataAnalyzer` call Gemini or Perplexity through provider wrappers that handle prompt templates and JSON coercion.【F:src/steps/news.py†L1-L48】【F:src/steps/script.py†L1-L115】【F:src/steps/metadata.py†L1-L83】
- **VOICEVOX** — `AudioSynthesizer` relies on the `VOICEVOXProvider`, which can auto-start a managed server and maps alias spellings to speaker IDs before invoking the HTTP API.【F:src/steps/audio.py†L1-L36】【F:src/providers/tts.py†L1-L64】
- **FFmpeg** — `VideoRenderer` resolves the FFmpeg binary, applies configured filters, and muxes audio/video streams for deterministic rendering.【F:src/steps/video.py†L1-L63】

## Outputs and run directory
Every workflow execution writes artefacts beneath `runs/<run_id>/`. The orchestrator tracks completion in `state.json`, while each step names its output according to `output_filename`, making runs self-contained for auditing or re-uploading.【F:src/core/step.py†L17-L33】【F:src/core/state.py†L1-L32】【F:apps/youtube/cli.py†L29-L63】
