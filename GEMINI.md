# Gemini Code Assistant Context

## Project snapshot
`youtube-ai-v2` generates narrated Japanese finance videos by composing modular workflow steps. The CLI entry point in `src/main.py` defers to `apps.youtube.run`, which assembles step instances, hands them to the `WorkflowOrchestrator`, and writes artefacts beneath `runs/<run_id>/`. Each step inherits from `src.core.step.Step`, declaring the artifact filename that downstream steps consume.【F:src/main.py†L1-L25】【F:apps/youtube/cli.py†L24-L111】【F:src/core/step.py†L1-L33】

The default pipeline covers news collection, Gemini-powered script generation, Voicevox audio synthesis, subtitle formatting, and FFmpeg rendering. Optional steps add metadata, thumbnails, YouTube uploads, Twitter clips, podcast exports, and Buzzsprout publishing when enabled in configuration.【F:apps/youtube/cli.py†L64-L111】【F:src/steps/video.py†L1-L63】【F:config/default.yaml†L61-L159】

## Key files
- `config/default.yaml` — workflow toggles, provider endpoints, subtitle/video settings.【F:config/default.yaml†L1-L168】
- `config/prompts.yaml` — prompt templates used by news, script, and metadata providers.【F:src/providers/news.py†L1-L49】
- `src/utils/config.py` — typed configuration models and loader utilities.【F:src/utils/config.py†L1-L204】
- `docs/system_overview.md` — architecture and dependency reference.【F:docs/system_overview.md†L1-L46】
- `docs/operations.md` — setup, execution, testing, and maintenance commands.【F:docs/operations.md†L1-L41】

## Running and testing
```bash
uv sync                               # install dependencies
cp config/.env.example config/.env    # provide Gemini/Perplexity/etc. keys
uv run python -m src.main             # execute the YouTube workflow
uv run pytest -m unit                 # run fast tests
uv run pytest -m "unit or integration"
```
End-to-end tests (`pytest -m e2e`) require valid Gemini credentials and any optional provider keys configured in the environment.【F:config/.env.example†L1-L21】【F:pytest.ini†L1-L11】
