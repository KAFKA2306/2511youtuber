## Common commands
- `task bootstrap` — install deps + start services + cron setup.
- `task run -- --news-query "<query>"` — run main workflow (YouTube AI video generator).
- `task services:status` / `task services:start` — check/start background services.
- `task lint` / `task lint:fix` — lint and auto-fix with Ruff.
- `task test:unit` / `task test:integration` / `task test:e2e` — run tests by scope; `uv run pytest tests/unit -m unit -v --cov=src --cov-report=term-missing` for fast feedback.
- Manual entry: `uv run python -m src.main` or `uv run python src/main.py`.
- Scene generation test: `uv run python scripts/test_scene_gen.py <run_id>`.
- Automation: `python scripts/automation.py --skip-cron` then `python scripts/automation.py --install-cron`.
- Git helpers: `task git:status`, `task git:sync -- "message"`.