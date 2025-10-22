# YouTube AI Video Generator v2

YouTube AI Video Generator v2 assembles narrated Japanese finance videos from daily news by chaining modular workflow steps. The command-line entry point wires together news collection, Gemini-based script generation, Voicevox audio synthesis, subtitle formatting, and FFmpeg rendering, with optional metadata and publishing steps enabled through configuration.【F:src/main.py†L1-L25】【F:apps/youtube/cli.py†L24-L111】【F:src/steps/video.py†L1-L63】

## Getting started
1. Install dependencies and developer tools:
   ```bash
   uv sync
   ```
2. Copy the example environment file and provide provider credentials:
   ```bash
   cp config/.env.example config/.env
   ```
   Gemini keys are required; add Perplexity, Twitter, Buzzsprout, and YouTube credentials when turning on those integrations.【F:config/.env.example†L1-L21】
3. Run the workflow (news query optional):
   ```bash
   uv run python -m src.main --news-query "FOMC 金利"
   ```
   Outputs land in `runs/<run_id>/` with a persisted `state.json` so reruns can resume mid-pipeline.【F:apps/youtube/cli.py†L24-L76】【F:src/core/state.py†L1-L32】

See [docs/operations.md](docs/operations.md) for detailed operations guidance.【F:docs/operations.md†L1-L41】

## Setup commands
- `uv sync`
- `cp config/.env.example config/.env`
- `nohup bash scripts/start_aim.sh >/dev/null 2>&1 &`
- `nohup bash scripts/voicevox_manager.sh start >/dev/null 2>&1 &`
- `nohup uv run python scripts/discord_news_bot.py >/dev/null 2>&1 &`

## Workflow summary
| Step | Module | Output | Notes |
| --- | --- | --- | --- |
| News collection | `src/steps/news.py` | `news.json` | Executes Perplexity and Gemini providers with fallback chaining.【F:src/steps/news.py†L1-L48】【F:src/providers/base.py†L1-L38】 |
| Script generation | `src/steps/script.py` | `script.json` | Prompts Gemini with speaker profiles and previous run context to produce structured dialogue segments.【F:src/steps/script.py†L1-L126】 |
| Audio synthesis | `src/steps/audio.py` | `audio.wav` | Calls the Voicevox HTTP API per segment and concatenates the resulting audio clips.【F:src/steps/audio.py†L1-L36】【F:src/providers/tts.py†L1-L64】 |
| Subtitle formatting | `src/steps/subtitle.py` | `subtitles.srt` | Allocates time slices proportionally to character counts and wraps Japanese lines to a configurable width.【F:src/steps/subtitle.py†L1-L72】 |
| Video rendering | `src/steps/video.py` | `video.mp4` | Generates a colour plate, applies Ken Burns and overlay effects, burns subtitles, and muxes audio via FFmpeg.【F:src/steps/video.py†L1-L63】 |

Optional steps add metadata analysis, thumbnail generation, platform uploads, and social distribution when enabled in `config/default.yaml`.【F:apps/youtube/cli.py†L64-L111】【F:config/default.yaml†L61-L159】

## Configuration and assets
- `config/default.yaml` — centralises workflow toggles, provider credentials, subtitle typography, and rendering parameters.【F:config/default.yaml†L1-L168】
- `config/prompts.yaml` — stores runtime prompt templates for news, script, and metadata providers.【F:src/providers/news.py†L1-L49】
- `assets/` — includes fonts and character art consumed by thumbnail and video steps; update paths if you customise visuals.【F:config/default.yaml†L61-L117】【F:src/steps/thumbnail.py†L1-L119】

## Repository structure
```
├── apps/              # Application entry points (YouTube CLI)
├── config/            # YAML configuration, prompt templates, env example
├── docs/              # System overview and operations guides
├── src/               # Core workflow, providers, and step implementations
├── tests/             # Unit, integration, and e2e suites (pytest markers enforced)
└── runs/              # Generated artefacts per run (created on demand)
```
Workflow classes live under `src/core/`, typed configuration models in `src/utils/config.py`, and step implementations in `src/steps/`, mirroring the runtime pipeline.【F:src/core/orchestrator.py†L1-L30】【F:src/utils/config.py†L1-L204】【F:src/steps/audio.py†L1-L36】

## Additional documentation
- [docs/system_overview.md](docs/system_overview.md) — architecture summary, dependencies, and run lifecycle.【F:docs/system_overview.md†L1-L46】
- [docs/operations.md](docs/operations.md) — setup, execution, testing, and maintenance tips.【F:docs/operations.md†L1-L41】
