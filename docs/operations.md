# Operations Guide

## Environment setup
1. Install dependencies with [`uv`](https://github.com/astral-sh/uv):
   ```bash
   uv sync
   ```
2. Copy the example environment file and add provider credentials:
   ```bash
   cp config/.env.example config/.env
   ```
   At minimum a `GEMINI_API_KEY` is required for script and metadata generation. Add Perplexity and social API keys when enabling those providers.【F:config/.env.example†L1-L21】

Dependencies, Python version, and optional developer extras are declared in `pyproject.toml`. Use `uv run` (or another Python 3.11+ environment) to execute the CLI and tests with the resolved lockfile.【F:pyproject.toml†L1-L36】

## Running the workflow
Run the YouTube pipeline with an optional custom news query:
```bash
uv run python -m src.main --news-query "トヨタ 四半期 決算"
```
The CLI loads configuration from `config/default.yaml`, builds enabled steps, and writes outputs to `runs/<run_id>/` using the timestamped identifier logged at startup.【F:apps/youtube/cli.py†L24-L76】【F:config/default.yaml†L1-L168】

Toggle optional steps (metadata, thumbnail, YouTube upload, Twitter clip, podcast export, Buzzsprout upload) through the `steps` section of the config file. Disabled steps produce empty placeholder files only when the pipeline expects their outputs downstream.【F:apps/youtube/cli.py†L64-L111】【F:config/default.yaml†L61-L159】

## Testing
Pytest markers group the suite into unit, integration, and end-to-end tiers. Use strict markers to avoid accidentally running slow tests:
```bash
uv run pytest -m unit
uv run pytest -m "unit or integration"
uv run pytest -m e2e  # requires live Gemini/Perplexity credentials
```
The pytest configuration enables verbose output and enforces marker registration for safety.【F:pytest.ini†L1-L11】

## Maintenance tips
- Generated artefacts and the orchestrator `state.json` accumulate under `runs/`. Remove dated run directories after archiving outputs to keep disk usage manageable.【F:src/core/state.py†L1-L41】
- Thumbnail and overlay assets referenced in `config/default.yaml` must exist locally; update paths if moving the repository or trimming the `assets/` folder.【F:config/default.yaml†L61-L117】
- FFmpeg and VOICEVOX must be reachable at runtime. Configure alternate binaries or hosts through the video and TTS provider settings before invoking the workflow.【F:src/steps/video.py†L1-L63】【F:src/providers/tts.py†L1-L64】
