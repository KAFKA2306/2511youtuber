## Before finishing tasks
- Ensure config-driven changes respect config/default.yaml toggles; avoid root-level file creation.
- Run lint/tests when possible: `task lint`, `task test:unit` or targeted `uv run pytest ...`; note Ruff may require installation via uv sync.
- Verify workflow entry via `uv run python -m src.main --news-query "..."` for end-to-end smoke when feasible.
- Keep secrets in config/.env (copy from example); do not generate or overwrite user .env.
- Preserve news query configuration length (config/default.yaml steps.news.query) per repo caution.