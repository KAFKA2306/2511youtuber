# Phase 0 Investigation Memo — Core vs YouTube App

_Date: 2025-10-12_

## Snapshot Metrics
- Total LOC (total/code): 2,277 / 1,834 (`uv run python scripts/inspect_tree.py`)
- Top-heavy modules: `src/steps/thumbnail.py` (320 code LOC), `src/providers/youtube.py` (170), `src/utils/config.py` (145), `src/steps/script.py` (144), `src/steps/metadata.py` (131)
- Directory distribution:
  - `src/steps/`: 1,120 total LOC (919 code)
  - `src/providers/`: 590 total (471 code)
  - `src/utils/`: 307 total (232 code)
  - `src/main.py`: 149 total (128 code)

_Target guardrail_: Refactors must land with flat or negative total LOC; any new abstraction must replace >= existing lines.

## Responsibility Classification

| Layer | Candidate Modules | Notes |
| --- | --- | --- |
| Core orchestration | `src/workflow.py`, `src/models.py` (`Workflow*`), `src/steps/base.py` | Already small; promote to `src/core/` with immutable contracts. retain minimal dependencies (Path, datetime). |
| Core utilities | `src/utils/logger.py`, `src/utils/config.py` (partial), `src/utils/secrets.py` | Split config into core schema vs YouTube overrides. Logger + secrets reusable as-is. |
| Generic providers | `src/providers/base.py`, `src/providers/llm.py`, `src/providers/tts.py`, `src/providers/news.py`, `src/providers/video_effects.py` | Extract interface layer; mark news/script assumptions for generalisation. |
| YouTube app layer | `src/main.py`, `src/providers/youtube.py`, `src/utils/discord.py`, `src/steps/news.py`, `src/steps/script.py`, `src/steps/audio.py`, `src/steps/subtitle.py`, `src/steps/video.py`, `src/steps/metadata.py`, `src/steps/thumbnail.py`, `src/steps/youtube.py` | Strong domain coupling (news-centric prompts, YouTube metadata, FFmpeg presets). Move under `apps/youtube/` during split. |
| Mixed/needs split | `src/utils/config.py`, `config/default.yaml`, `config/prompts.yaml` | Contains both core schema and concrete defaults. Create `config/base.yaml` for shared defaults + per-app overlays. |

## Immediate Reduction/Consolidation Targets
- `src/steps/thumbnail.py`: Inline overlay helpers into utility module or template engine; aim for 10–15% trim by consolidating geometry helpers and JSON readers.
- `src/steps/script.py`: Template parsing and previous-context logic are intertwined; extract reusable parsing helpers (code fence stripping, YAML/JSON coercion) into `core` and drop redundant recursion.
- `src/providers/youtube.py`: Dry-run ID generator + OAuth flow occupy 170 LOC; move OAuth + credential loading into separate helper and reuse across future apps, shrinking client class by ~40 LOC.
- `src/utils/config.py`: Schema objects include many YouTube-only fields; derive `StepsConfig` subclasses per app so shared Core schema falls below 100 LOC.

## Candidate Deletions / Simplifications
- `src/utils/discord.py`: If Discord summary is optional, move call behind plugin hook; allow builds to omit module entirely.
- Thumbnail overlays: Remove unused `anchor` variants and redundant conversion steps once app layer provides curated overlays.
- Metadata step: Verify whether `recommendations` are consumed elsewhere; delete unused JSON fields.

## Open Questions
1. Should `WorkflowState` persist to disk for all library consumers, or should persistence be optional? Allow injecting state backend? (affects interface design)
2. Can `execute_with_fallback` become a generic strategy primitive under `core/providers`? Currently news-specific.
3. Do future workflows always follow sequential steps, or do we need branching/composition? Impacts `WorkflowOrchestrator` redesign.

## Next Actions
1. Confirm guardrail: no net LOC increase across Phase 1 branches. Adopt `scripts/inspect_tree.py` as pre-commit check.
2. Plan extraction of `core` package: start with moving `WorkflowOrchestrator`, `WorkflowState`, `WorkflowResult`, and `Step` base class without adding code.
3. Draft `apps/youtube` skeleton (CLI wrapper + workflow registration) on prototype branch while deleting redundant helpers in existing modules to stay within LOC budget.

## Prototype Branch Strategy (Phase 1 Draft)
- **Branch name**: `feat/core-split-prototype` (kept short for future rebases).
- **Milestone 1 – Baseline shrink**: delete unused helpers (e.g., duplicate thumbnail geometry, redundant metadata fields) and move Discord summary behind feature flag to achieve ≥80 LOC reduction before structural moves.
- **Milestone 2 – Core package extraction**: relocate `WorkflowOrchestrator`, `WorkflowState`, `WorkflowResult`, and `Step` base class under `src/core/` with identical implementations; adjust imports only where necessary. Validate zero net LOC change by offsetting with further simplifications (e.g., consolidate JSON load helpers).
- **Milestone 3 – App adapter**: create `apps/youtube/__init__.py` and `apps/youtube/workflow.py` providing step list factory + CLI entry. `src/main.py` becomes thin shim (≤60 LOC target) that delegates to app layer.
- **Milestone 4 – Sanity tests**: run `uv run pytest tests/unit -m unit` and CLI smoke (`uv run python -m src.main --config config/default.yaml`) to confirm parity; capture LOC snapshot via `scripts/inspect_tree.py` in PR description.
- **Exit criteria**: total project LOC ≤ current baseline (2,277) and `src/core/` contains only domain-neutral code. Document migration steps in `docs/architecture/phase0_core_boundary_memo.md`.
