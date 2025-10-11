# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **minimalist, resilient YouTube video generator** that creates Japanese financial news videos from news sources. Built as a zero-based rewrite of a failed predecessor (50+ hours of debugging), this v2 emphasizes **Simple, Resilient, Modular** design principles.

Key differences from v1:
- 5 steps (down from 13)
- 1 required external API (Gemini only)
- Checkpoint-based execution with file persistence
- No fallback system
- 58+ tests (v1 had 0 integration tests)

## Essential Commands

### Development & Execution
```bash
# Install dependencies (uv package manager)
uv sync

# Run full pipeline
uv run python -m src.main

# Run with specific config
uv run python src/main.py --config config/default.yaml
```

### Testing
```bash
# Fast unit tests (recommended during development)
uv run pytest tests/unit -m unit -v

# Unit tests with coverage
uv run pytest tests/unit --cov=src --cov-report=term-missing

# Integration tests (mocked APIs)
uv run pytest tests/integration -v

# E2E tests (requires GEMINI_API_KEY in .env)
uv run pytest -m e2e -v

# Full test suite
uv run pytest -v
```

### Linting & Formatting
```bash
# Check code style
uv run ruff check src tests

# Format code (auto-fix)
uv run ruff format src tests
```

## Architecture Overview

### Core Workflow (5 Steps)

The pipeline executes sequentially with checkpoint-based resumption:

```
1. NewsCollector      → runs/{run_id}/news.json
   (Perplexity, No DummyNews fallback)

2. ScriptGenerator    → runs/{run_id}/script.json
   (Gemini LLM via LiteLLM, No Japanese purity validation)

3. AudioSynthesizer   → runs/{run_id}/audio.wav
   (VOICEVOX → pyttsx3 fallback chain)

4. SubtitleFormatter  → runs/{run_id}/subtitles.srt
   (Character-ratio timing, no Whisper STT)

5. VideoRenderer      → runs/{run_id}/video.mp4
   (FFmpeg lavfi color + subtitles overlay)

Optional steps (disabled by default):
6. MetadataAnalyzer   → metadata.json
7. ThumbnailGenerator → thumbnail.png
8. YouTubeUploader    → upload_result.json
```

Each step:
- Reads from previous step's output files
- Saves outputs to `runs/{run_id}/` directory
- Supports checkpoint resumption (re-running skips completed steps)
- Is stateless and idempotent

### Key Design Patterns

**Provider Chain Pattern** (`src/providers/base.py`):
```python
class ProviderChain:
    def execute(self):
        for provider in sorted_by_priority:
            if provider.is_available():
                return provider.execute()
        raise AllProvidersFailedError()
```

All external dependencies use this pattern:
- **TTS**: VOICEVOX (free, local) → pyttsx3 (offline fallback)
- **News**: Perplexity API, No DummyNews
- **LLM**: Gemini only (required, no fallback in v2)

**Checkpoint-Based Orchestration** (`src/workflow.py`):
- WorkflowState stored in `runs/{run_id}/workflow_state.json`
- Steps check `step.name in state.completed_steps` before running
- Failures save partial progress for inspection

### Directory Structure

```
youtube-ai-v2/
├── src/                        # Application code
│   ├── main.py                 # CLI entrypoint
│   ├── workflow.py             # Orchestrator (checkpoint logic)
│   ├── models.py               # Pydantic data models
│   ├── steps/                  # 5 core + 3 optional steps
│   │   ├── base.py             # Step abstract class
│   │   ├── news.py             # NewsCollector
│   │   ├── script.py           # ScriptGenerator (Gemini)
│   │   ├── audio.py            # AudioSynthesizer (TTS chain)
│   │   ├── subtitle.py         # SubtitleFormatter (SRT)
│   │   ├── video.py            # VideoRenderer (FFmpeg)
│   │   ├── metadata.py         # (optional)
│   │   ├── thumbnail.py        # (optional)
│   │   └── youtube.py          # (optional)
│   ├── providers/              # Plugin-style API wrappers
│   │   ├── base.py             # Provider chain system
│   │   ├── llm.py              # Gemini via LiteLLM
│   │   ├── tts.py              # VOICEVOX + pyttsx3
│   │   ├── news.py             # Perplexity, No DummyNews
│   │   └── video_effects.py    # Ken Burns effects
│   └── utils/                  # Shared utilities
│       ├── config.py           # Pydantic config loader
│       ├── logger.py           # Structured JSON logging
│       └── secrets.py          # .env secret management
│
├── config/                     # Configuration files
│   ├── default.yaml            # All settings (steps, providers, logging)
│   └── prompts.yaml            # LLM prompts (script generation)
│
├── tests/                      # Test suites
│   ├── fixtures/               # Sample data (news, scripts)
│   ├── unit/                   # 40+ fast tests
│   ├── integration/            # 15+ orchestration tests
│   └── e2e/                    # 3 real API tests
│
├── runs/                       # Output directory (gitignored)
│   └── {run_id}/               # Per-execution artifacts
│       ├── news.json
│       ├── script.json
│       ├── audio.wav
│       ├── subtitles.srt
│       ├── video.mp4
│       └── workflow_state.json
│
└── docs/                       # Design documentation
    ├── DESIGN.md               # Architecture specs
    ├── ANTI_PATTERNS.md        # v1 failure lessons
    └── TESTING.md              # Test strategy
```

## Configuration System

**Unified Pydantic-based config** (`src/utils/config.py`):

- **Primary**: `config/default.yaml` - all runtime settings
- **Secrets**: `.env` file - API keys only (never commit)
- **Prompts**: `config/prompts.yaml` - LLM system prompts

Key config sections:
```yaml
workflow:
  default_run_dir: "runs"
  checkpoint_enabled: true

steps:
  script:
    speakers:
      analyst: {name: "春日部つむぎ", aliases: ["つむぎ"]}
      reporter: {name: "ずんだもん"}
      narrator: {name: "玄野武宏"}

providers:
  llm:
    gemini:
      model: "gemini/gemini-2.5-flash-preview-09-2025"
      temperature: 0.7

  tts:
    voicevox:
      enabled: true
      url: "http://localhost:50121"
      speakers:
        春日部つむぎ: 3
        ずんだもん: 1
        玄野武宏: 11
```

**Speaker Mapping**: Script generator outputs speaker names (春日部つむぎ), which map to provider-specific IDs (VOICEVOX ID: 3).

## Data Models

Pydantic v2 models in `src/models.py`:

```python
class ScriptSegment(BaseModel):
    speaker: str           # Must match speakers config
    text: str              # Japanese-only validated
    voice_config: dict     # Provider-specific params

class Script(BaseModel):
    segments: List[ScriptSegment]

class WorkflowState(BaseModel):
    run_id: str
    status: str            # "running", "success", "partial", "failed"
    completed_steps: List[str]
    outputs: Dict[str, str]  # {step_name: output_file_path}
    errors: List[str]
```

All models use strict validation. Scripts reject English text via regex validation.

## Critical Implementation Details

### Japanese Purity Validation

Script generation enforces Japanese-only output:

```python
# src/models.py
def is_pure_japanese(text: str) -> bool:
    return bool(re.match(r"^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s\d、。！？「」『』・\n]+$", text))
```

This prevents v1's bug where English metadata leaked into script text.

### LLM Output Parsing Strategy

Gemini can output YAML-in-YAML (recursive wrapping). Parsing logic in `src/steps/script.py`:

1. Try YAML parse
2. If result is string, try JSON parse
3. If still string, recursively YAML parse (max 3 levels)
4. Validate with Pydantic

This solves v1's `RecursionDepthExceeded` errors.

### FFmpeg Stability

**Lessons from v1**:
- Never use PNG loop input (causes hang with `-loop 1`)
- Use `lavfi color` source directly
- Avoid parameter duplication (quality settings in one place only)

Correct implementation (`src/steps/video.py`):
```python
video_stream = ffmpeg.input(
    f'color=c=0x193d5a:size=1920x1080:duration={duration}:rate={fps}',
    f='lavfi'
)
```

### TTS Provider Chain

Speaker-aware fallback:

```python
# config/default.yaml
providers.tts.voicevox.speakers:
  春日部つむぎ: 3    # VOICEVOX speaker ID
  ずんだもん: 1

providers.tts.pyttsx3.speakers:
  春日部つむぎ: {rate: 140}  # Fallback uses speech rate
```

Chain tries VOICEVOX first, falls back to pyttsx3 if unavailable.

## Common Development Patterns

### Adding a New Provider

1. Create class inheriting from `Provider` in `src/providers/`
2. Implement `is_available()` and `execute(**kwargs)`
3. Add to chain in respective step (e.g., `AudioSynthesizer`)
4. Update `config/default.yaml` with provider settings

### Adding a New Step

1. Create class inheriting from `Step` in `src/steps/`
2. Implement `execute(inputs: Dict[str, Path]) -> Path`
3. Set `name`, `output_filename`, `is_required` attributes
4. Add to step list in `src/main.py`
5. Write unit test in `tests/unit/`

### Modifying Script Generation

**DO NOT** hardcode prompts in code. Edit `config/prompts.yaml` instead:

```yaml
script_generation:
  system: |
    あなたは金融ニュースの対話スクリプト生成AIです。
    話者: 春日部つむぎ、ずんだもん、玄野武宏
    ...
```

Script generator loads prompts from config.

## Testing Strategy

### Test Pyramid

- **Unit tests** (40+ tests, <1s): Pure logic, no mocked dependencies
- **Integration tests** (15+ tests, ~5s): Step-to-step flow without dummy providers
- **E2E tests** (3 tests, ~60s): Real Gemini API calls

### Running Subsets

```bash
# During feature development (fast feedback)
pytest tests/unit/test_providers.py -v

# Before commit (comprehensive)
pytest tests/unit tests/integration -v

# Before release (includes API costs)
pytest -v
```

### Test Markers

```python
@pytest.mark.unit          # Fast, no external deps
@pytest.mark.integration   # Mocked APIs
@pytest.mark.e2e           # Real API calls
```

Run specific marker: `pytest -m unit`

## Coding Principles (From AGENTS.md)

**Strict rules from v1 failure analysis**:

1. **No hardcoding**: All config in YAML, not Python files
2. **No retry logic**: Root cause fixes only (no masking failures)
3. **No timeout logic**: Infinite wait reveals actual problems
4. **No try-catch**: Let errors surface (except Critical/Warning classification)
5. **No comments**: Code should be self-documenting
6. **Reduce, don't add**: Delete code to maintain simplicity

These may seem extreme but come from painful v1 debugging experience (see `docs/ANTI_PATTERNS.md`).

## Error Handling Philosophy

Errors are classified:

- **CriticalError**: Workflow must stop (e.g., Gemini API down)
- **Exception (required step)**: Workflow partial success
- **Exception (optional step)**: Continue to next step

Example from `src/workflow.py`:
```python
try:
    output = step.run(inputs)
except CriticalError:
    return WorkflowResult(status="failed")
except Exception:
    if step.is_required:
        return WorkflowResult(status="partial")
    # else continue
```

## Troubleshooting Quick Reference

### "ModuleNotFoundError: No module named 'src'"

Run from project root: `cd youtube-ai-v2 && pytest tests/unit`

### "VOICEVOX connection refused"

VOICEVOX is optional. If unavailable, system falls back to pyttsx3 automatically.

To enable: Install VOICEVOX Nemo and start server on port 50121.

### "pyttsx3 espeak not found" (Linux)

```bash
sudo apt-get install espeak espeak-data libespeak-dev
```

### "FFmpeg not found"

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Script generation returns English text

Check `config/prompts.yaml` - ensure system prompt explicitly states "日本語のみ使用してください"

## File Naming & Conventions

- **Modules/functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private methods**: `_leading_underscore`

Python 3.11+, 4-space indentation, type hints preferred.

## Environment Variables

Create `.env` in project root:

```bash
# Required
GEMINI_API_KEY=your-key-here

# Optional (improves quality)
PERPLEXITY_API_KEY=your-key-here

# For YouTube upload (optional)
YOUTUBE_CLIENT_SECRETS_FILE=path/to/credentials.json
```

Never commit `.env` file.

## Key Differences from v1 Project

This is a **complete rewrite**, not an iteration. Major changes:

| Aspect | v1 | v2 |
|--------|----|----|
| Steps | 13 | 5 |
| Required APIs | 6 | 1 (Gemini) |
| Framework | CrewAI (7 agents) | Direct LiteLLM |
| State | In-memory | File-persisted checkpoints |
| Integration tests | 0 | 15+ |
| Success rate | 20% | 95% target |

See `docs/ANTI_PATTERNS.md` for detailed v1 failure analysis.

## References

- **Design specs**: `docs/DESIGN.md` - Full architecture
- **Failure lessons**: `docs/ANTI_PATTERNS.md` - What NOT to do
- **Test guide**: `docs/TESTING.md` - Detailed test documentation
- **Coding rules**: `AGENTS.md` - Strict development constraints
- **Project overview**: `README.md` - Quick start guide
