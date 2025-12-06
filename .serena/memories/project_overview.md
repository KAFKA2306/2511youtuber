## Project purpose
YouTube AI Video Generator v2 builds narrated Japanese finance videos from daily news using modular workflow steps (news collection, Gemini-based script generation, scene/image generation, Voicevox audio, subtitles, FFmpeg rendering) with optional metadata/social publishing.

## Tech stack
- Python 3.11
- Taskfile + uv for env/run commands
- Providers: Gemini, Perplexity, Voicevox, FFmpeg, social APIs (YouTube, Twitter, LinkedIn, Hatena)

## Structure highlights
- Entry: src/main.py, workflow orchestration in src/workflow.py; steps under src/steps/** and providers under src/providers/**
- Models/contracts in src/models.py; utils in src/utils/**; prompts/config in config/**; docs in docs/**
- Apps (e.g., YouTube CLI) under apps/youtube/; assets/prompts under assets/ and config/scene_prompts.yaml
- Tests under tests/unit, tests/integration, tests/e2e with fixtures in tests/fixtures
- Finance/qualification packs separated under config/packs/*, assets/series/*, runs/* per docs/markets/qualification.md