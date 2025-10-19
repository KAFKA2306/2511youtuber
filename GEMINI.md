# Gemini Code Assistant Context: youtube-ai-v2

This document provides context for the `youtube-ai-v2` project, a Python-based application that automates the creation of Japanese financial news videos for YouTube.

## Project Overview

The project implements a modular pipeline that transforms news articles into fully rendered videos. The workflow consists of several distinct steps, orchestrated to fetch news, generate scripts, synthesize audio, create subtitles, and render a final video file. It leverages external services like Gemini for content generation, Voicevox for text-to-speech, and FFmpeg for video processing.

The architecture is designed for resilience and extensibility, allowing steps to be added or modified easily. Configuration is centralized and strongly typed, and the system supports checkpointing to resume failed runs.

### Core Technologies
- **Language:** Python 3.11+
- **Package Management:** `uv`
- **Configuration:** Pydantic, YAML
- **Core Libraries:** `litellm` (LLM abstraction), `ffmpeg-python`, `pydub`, `Pillow`
- **External Services:** Google Gemini, Perplexity, Voicevox, YouTube API, Twitter API

## Building and Running

### 1. Installation
Install all required dependencies, including development tools, using `uv`.
```bash
uv sync
```

### 2. Configuration
Create a local environment file from the example and populate it with the necessary API keys and secrets. At a minimum, a Gemini API key is required.
```bash
cp config/.env.example config/.env
```
Further configuration for steps, providers, and output formats can be adjusted in `config/default.yaml`.

### 3. Running the Workflow
Execute the main workflow from the command line. You can optionally provide a news query to override the default.
```bash
uv run python -m src.main --news-query "FOMC 金利"
```
Outputs for each run, including logs, intermediate artifacts, and the final video, are stored in a timestamped subdirectory within the `runs/` directory.

## Development Conventions

### Code Structure
- `src/`: Main application source code.
  - `core/`: Core abstractions like `Orchestrator`, `Step`, and `State`.
  - `providers/`: Wrappers for external services (LLMs, TTS, etc.).
  - `steps/`: Individual pipeline steps (e.g., `NewsCollector`, `VideoRenderer`).
  - `models.py`: Pydantic models for data structures like `NewsItem` and `Script`.
- `apps/`: Application entry points (e.g., the main CLI).
- `config/`: YAML configuration files (`default.yaml`, `prompts.yaml`).
- `tests/`: Pytest tests, categorized by markers.
- `scripts/`: Helper scripts for tasks like managing services.

### Coding Style
- **Typing:** The codebase uses Python's type hints extensively, with Pydantic models for data validation and configuration.
- **Formatting & Linting:** `ruff` is used for linting and formatting. Check the `pyproject.toml` for the exact configuration.
  ```bash
  # Run linter
  uv run ruff check .

  # Run formatter
  uv run ruff format .
  ```
- **Modularity:** The system is built around small, focused components. Steps are self-contained, and providers abstract away the details of external APIs.

### Testing
- **Framework:** `pytest`
- **Test Types:** Tests are categorized using markers defined in `pytest.ini`:
  - `unit`: Fast tests with no external dependencies.
  - `integration`: Tests that may use mocked external services.
  - `e2e`: Slow, end-to-end tests that call real APIs and require credentials.
- **Running Tests:**
  ```bash
  # Run all tests
  uv run pytest

  # Run only unit tests
  uv run pytest -m unit
  ```