# Gemini Code Assistant Context

## Project Overview

This project, `youtube-ai-v2`, is a Python application designed to automatically generate high-quality Japanese-language YouTube videos from financial news articles. It is a complete rewrite of a previous project, focusing on simplicity, resilience, and modularity.

The core workflow consists of 5 distinct, checkpointed steps:
1.  **NewsCollector**: Fetches financial news articles.
2.  **ScriptGenerator**: Uses the Gemini LLM to generate a video script from the news.
3.  **AudioSynthesizer**: Converts the script to audio using a TTS engine (VOICEVOX).
4.  **SubtitleFormatter**: Creates SRT subtitle files from the script.
5.  **VideoRenderer**: Renders the final video using FFmpeg, combining a background, subtitles, and Ken Burns effects.

The system is highly configurable through YAML files and is designed with clear separation of concerns, using a provider pattern for external services like LLMs and TTS.

## Building and Running

The project uses `uv` for dependency and environment management.

### Setup

1.  **Install dependencies:**
    ```bash
    uv sync
    ```
2.  **Configure environment:**
    *   Copy the example `.env` file:
        ```bash
        cp config/.env.example config/.env
        ```
    *   Edit `config/.env` and add your `GEMINI_API_KEY`.

### Running the Main Workflow

To run the entire video generation workflow:
```bash
uv run python -m src.main
```
or
```bash
python src/main.py
```
Output files for each run are stored in a timestamped directory within `runs/`.

### Running Tests

The project has a comprehensive test suite divided into unit, integration, and end-to-end tests.

*   **Run all tests:**
    ```bash
    pytest -v
    ```
*   **Run only unit tests (fastest):**
    ```bash
    pytest tests/unit -v
    ```
*   **Run unit and integration tests:**
    ```bash
    pytest tests/unit tests/integration -v
    ```
*   **Run end-to-end tests (requires a valid `GEMINI_API_KEY`):**
    ```bash
    pytest tests/e2e -v
    ```

## Development Conventions

*   **Dependency Management**: `uv` is used for managing dependencies, as defined in `pyproject.toml`.
*   **Linting & Formatting**: `ruff` is used for linting. Check for issues with:
    ```bash
    ruff check .
    ```
*   **Testing**: `pytest` is the testing framework. New features should be accompanied by tests. Test files are located in the `tests/` directory and are categorized into `unit`, `integration`, and `e2e`.
*   **Configuration**: All configuration is managed through YAML files in the `config/` directory. Secrets are managed via a `.env` file. No hardcoding of settings.
*   **Modularity**: The project follows a modular design. External services are abstracted into "providers" (`src/providers/`) and the main workflow is broken down into "steps" (`src/steps/`). This allows for easier testing and modification.
*   **Automation**: A cron job is set up to run the video generation process automatically at 7:00, 12:00, and 17:00 daily.
    ```bash
    0 7,12,17 * * * cd /home/kafka/projects/2510youtuber/youtube-ai-v2 && /home/kafka/.local/bin/uv run python -m src.main >> /home/kafka/projects/2510youtuber/youtube-ai-v2/logs/cron.log 2>&1
    ```
