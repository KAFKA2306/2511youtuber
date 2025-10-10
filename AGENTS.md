# Repository Guidelines

## Project Structure & Module Organization
- `src/` houses the v2 pipeline: `main.py` drives the CLI, `workflow.py` orchestrates the five steps, and `steps/` and `providers/` keep responsibilities isolated; assets and prompts live in `config/` while shared docs are in `docs/`.
- `tests/` mirrors runtime boundaries with `unit/`, `integration/`, and `e2e/` suites plus reusable fixtures; keep new tests in the matching tier.
- `core/` is the zero-base rebuild: start work there when exploring the minimalist architecture—`src/` and `docs/` inside it must remain self-contained so old and new stacks can coexist.

## Build, Test, and Development Commands
- Install once with `python -m pip install -e .[dev]` to get runtime plus Ruff, pytest, and coverage extras.
- Run fast feedback with `pytest tests/unit -m unit -v`; add `--cov=src --cov-report=term-missing` before submitting substantial changes.
- Exercise integrations via `pytest tests/integration -v` and full regression with `pytest -v`; mark slow Gemini runs with `-m e2e` only when the key in `.env` is configured.
- Launch the MVP locally using `python -m src.main --config config/default.yaml`; when iterating on the new minimalist stack, point to `core/src/main.py` explicitly.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, type hints everywhere; modules and functions use `snake_case`, classes use `PascalCase`.
- Keep logic in small, composable functions; favor data classes or Pydantic models for shared contracts in `src/models.py`.
- Format and lint with `ruff check src tests` (add `core/src` when that code matures). Do not add inline comments or defensive error handling inside the `core` rebuild—success-path logic only.

## Testing Guidelines
- Mirror runtime seams: unit tests for pure logic, integration tests for step orchestration, e2e for Gemini-backed runs.
- Store deterministic Gemini fixtures under `tests/fixtures/` and update them whenever prompts change.
- New modules in `core/` must ship with unit tests that assert artifact paths and Gemini post-processing stay stable.

## Commit & Pull Request Guidelines
- Follow the existing history: short, imperative commit titles (`Add lightweight Pillow stub for tests`).
- Each PR needs a concise summary, linked issues, and evidence of test results; include sample artifacts or screenshots when touching rendering code.
- Tag the DRI for the affected module (`Workflow`, `Gemini Script`, `Audio`, `Video`, `Quality`) to keep ownership clear.
