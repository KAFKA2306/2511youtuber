# Repository Guidelines

要因を調査して根本対策。エラーハンドリング禁止。抜本的な課題を解決。コメント禁止。最小のコードにしつつ、目標を達成する
常に最小のコードベース、効率的なディレクトリ構成に改善する。

## Project Structure & Module Organization
- Source code for the v2 workflow lives in `src/`, with `main.py` as the CLI entrypoint, `workflow.py` orchestrating steps, and individual step/provider logic under `src/steps/` and `src/providers/`.
- Shared contracts and data models are defined in `src/models.py`; utilities (configuration, logging, secrets) sit in `src/utils/`.
- Runtime prompts and assets are stored in `config/`, while documentation belongs in `docs/`; tests mirror pipeline seams under `tests/unit/`, `tests/integration/`, `tests/e2e/`, and `tests/fixtures/` for reusable data.

## Build, Test, and Development Commands
- `uv sync` installs runtime dependencies plus Ruff, pytest, and coverage tooling.
- `uv run python -m src.main` launches the CLI; use `uv run python src/main.py` for a lightweight iteration loop.
- `uv run pytest tests/unit -m unit -v --cov=src --cov-report=term-missing` provides fast feedback with coverage; `uv run pytest tests/integration -v` validates orchestration, and `uv run pytest -v -m e2e` drives Gemini-backed flows once `.env` keys are set.
- Run linting and formatting via `uv run ruff check src tests` and `uv run ruff format src tests`.

## Coding Style & Naming Conventions
- Target Python 3.11 with four-space indents, exhaustive type hints, and immutable defaults.
- Favor small, composable functions, success-path logic only, and avoid comments, retries, timeouts, or defensive wrappers; push configuration into `config/` rather than hard-coding constants.
- Modules and functions use `snake_case`, classes use `PascalCase`, and constants remain uppercase.

## Testing Guidelines
- Tests use pytest; name cases descriptively (e.g., `test_handles_empty_script`).
- Store fixture payloads under `tests/fixtures/`, especially when prompts or Gemini schemas change.
- End-to-end tests must run with real Gemini API keys to validate live LLM syntax; keep coverage above the `--cov` thresholds before shipping.

## Commit & Pull Request Guidelines
- Follow the history’s short, imperative commit titles (e.g., `Add lightweight pillow stub for tests`).
- Pull requests should summarize changes, link issues, document test evidence, and provide artifacts or screenshots for rendering adjustments.
- Tag the appropriate DRI (`Workflow`, `Gemini Script`, `Audio`, `Video`, `Quality`) to maintain ownership visibility.

## Security & Configuration Tips
- Keep secrets in `.env` and never commit API keys; rotate Gemini credentials if distribution changes.
- Review `config/default.yaml` before demos to ensure only stable providers are enabled and experimental toggles remain disabled.
