# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the v2 pipeline: `main.py` powers the CLI entrypoint, `workflow.py` sequences the five steps, and `steps/` plus `providers/` isolate per-step behavior; shared contracts live in `src/models.py`.
- `config/` stores prompts and assets, `docs/` captures reference material, and `tests/` mirrors runtime seams with `unit/`, `integration/`, `e2e/`, and reusable fixtures under `tests/fixtures/`.

## Build, Test, and Development Commands
- Install tooling once with `uv sync`; it provisions runtime deps plus Ruff, pytest, and coverage extras.
- Run fast feedback via `uv run pytest tests/unit -m unit -v`; pair with `--cov=src --cov-report=term-missing` before shipping substantial work.
- Validate orchestration with `uv run pytest tests/integration -v`; run the full regression suite using `uv run pytest -v` and target Gemini-backed flows with `-m e2e` when the `.env` key is configured.
- Launch the CLI using `uv run python -m src.main --config config/default.yaml`; use `uv run python src/main.py` when iterating on the minimalist stack.
- manage docs/*.md as clean and latest

## Coding Style & Naming Conventions
- Python 3.11, four-space indentation, and type hints everywhere; modules and functions use `snake_case`, classes use `PascalCase`, constants stay uppercase.
- Favor small, composable functions and data classes or Pydantic models in `src/models.py`; keep success-path logic only.
- Keep implementations minimal per the docs: keep files short, isolate concerns across modules, avoid adding comments, no error handling. No mockups—let the real pipeline seams carry the behavior.
- Format and lint with `uv run ruff check src tests` (add `src` as that code stabilizes).
- must not hard coding and write comments. separate config. must not write retry and timeout logic. delete retry and timeout logic. think truely root cause. must not try catch logic.
- always think to reduce codes and delete files to keep simple but stable.

## Testing Guidelines
- Co-locate pure logic tests in `tests/unit`, orchestration cases in `tests/integration`, and cross-service flows in `tests/e2e`.
- Name tests with intent (`test_handles_empty_script`) and refresh fixtures in `tests/fixtures/` whenever prompts or Gemini payloads change.
- Test files must use REAL gemini API keys to verify REAL LLM Output syntax errors.

## Commit & Pull Request Guidelines
- Follow existing history: short, imperative commit titles such as `Add lightweight pillow stub for tests`.
- Each PR should include a crisp summary, linked issues, evidence of test runs, and sample artifacts or screenshots when modifying rendering.
- Tag the relevant DRI (`Workflow`, `Gemini Script`, `Audio`, `Video`, `Quality`) to keep ownership visible.

## Security & Configuration Tips
- Keep secrets in `.env` and never commit API keys; rotate Gemini credentials if the file changes hands.
- Review `config/default.yaml` before public demos to ensure no experimental providers are enabled.
