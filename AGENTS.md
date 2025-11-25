# Repository Guidelines

要因を調査して根本対策。エラーハンドリング禁止。抜本的な課題を解決。コメント禁止。最小のコードにしつつ、目標を達成する。常に最小のコードベース、効率的なディレクトリ構成に改善する。
DRYの原則に準拠。config/default.yamlを変更するだけで、意図通りに全体の動作が変更できなければならない。ハードコーディング禁止。
ROOTにファイルを生成しない。適切なディレクトリに追加していく。使い捨てのコードw生成しない。無用なテストを削除する。

> [!CAUTION]
> **News Query Configuration**: `config/default.yaml`の`steps.news.query`は**絶対に短縮・簡素化しないこと**。
> 過去に運用で使われていた長いクエリ（105文字）は、多様なニュースソースをカバーするために必要です。
> 変更する場合は必ず`git log -p --all -- config/default.yaml | grep -A 2 -B 2 "query:"`で履歴を確認すること。

## Project Structure & Module Organization

- Source code for the v2 workflow lives in `src/`, with `main.py` as the CLI entrypoint, `workflow.py` orchestrating steps, and individual step/provider logic under `src/steps/` and `src/providers/`.
- Shared contracts and data models are defined in `src/models.py`; utilities (configuration, logging, secrets) sit in `src/utils/`.
- Runtime prompts and assets are stored in `config/`, while documentation belongs in `docs/`; tests mirror pipeline seams under `tests/unit/`, `tests/integration/`, `tests/e2e/`, and `tests/fixtures/` for reusable data.
- Finance (`finance_news`) と Qualification (`takken`, `boki2`, `ap`) のディレクトリは `config/packs/finance/` と `config/packs/qualification/`、`assets/series/finance_news/` と `assets/series/qualification/<season>/`、`runs/finance_news/` と `runs/qualification/<season>/` のように完全分離し、詳細要件は `docs/markets/qualification.md` に従う。

## Build, Test, and Development Commands

### Using Task Runner (Recommended)
- `task bootstrap` — complete first-time setup: dependencies + services + automation + cron
- `task run` — run main workflow; pass args with `task run -- --news-query "your query"`
- `task test:unit` — run unit tests with coverage
- `task test:integration` — validate orchestration
- `task test:e2e` — drive Gemini-backed flows (requires `.env` keys)
- `task lint` and `task lint:fix` — check and auto-fix code quality
- `task services:status` — check all service statuses
- `task services:start` — start all background services
- `task aim:import` and `task aim:dashboard` — refresh and view Aim dashboards at http://<server-ip>:43800

### Manual Commands (Alternative)
- `uv sync` installs runtime dependencies plus Ruff, pytest, and coverage tooling.
- `uv run python -m src.main` launches the CLI; use `uv run python src/main.py` for a lightweight iteration loop.
- `uv run pytest tests/unit -m unit -v --cov=src --cov-report=term-missing` provides fast feedback with coverage; `uv run pytest tests/integration -v` validates orchestration, and `uv run pytest -v -m e2e` drives Gemini-backed flows once `.env` keys are set.
- `uv run python scripts/import_to_aim.py && aim up --host 0.0.0.0 --port 43800` refreshes Aim dashboards and exposes them to anyone with the URL.
- Run linting and formatting via `uv run ruff check src tests` and `uv run ruff format src tests`.

## Setup Commands

### First-Time Setup (Task Runner)
```bash
# Install Task runner
snap install task --classic

# Complete bootstrap
task bootstrap
```

This executes dependencies installation, starts all background services (Aim, Voicevox, Discord bot), and installs cron automation.

### Manual Setup (Alternative)
Memorize this exact sequence; Aim dashboard, Discord bot, and Voicevox engine must remain active via `nohup`.

- `uv sync`
- `.env` はユーザーが用意する。自動生成・上書きは禁止。
- `source .venv/bin/activate`
- `nohup bash scripts/start_aim.sh >/dev/null 2>&1 &`
- `nohup bash scripts/voicevox_manager.sh start >/dev/null 2>&1 &`
- `nohup uv run python scripts/discord_news_bot.py >/dev/null 2>&1 &`
- `python scripts/automation.py --skip-cron`
- `python scripts/automation.py --install-cron`

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

## Value Request Workflow

- Populate `config/.env` with at least one valid `PERPLEXITY_API_KEY_*` or `GEMINI_API_KEY_*` so news providers can execute custom factual queries.
- Run `.venv/bin/python -m src.main --news-query "<verbatim request>"` to force the workflow to investigate the exact claim.
- Collect evidence from `runs/<run_id>/collect_news/news.json` plus downstream outputs before drafting the response; if the run fails, fix credentials and rerun instead of speculating.
