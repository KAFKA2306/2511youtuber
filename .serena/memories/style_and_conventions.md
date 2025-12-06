## Coding style
- Python 3.11, 4-space indents, exhaustive type hints, immutable defaults.
- Prefer small composable functions, success-path logic; push config to config/default.yaml (no hardcoded constants), DRY and minimal codebase.
- Avoid comments and avoid adding new error-handling wrappers; focus on root-cause fixes rather than defensive handling.
- Naming: snake_case for modules/functions, PascalCase for classes, uppercase constants.
- Follow existing Step interface patterns; shared prompts/config live under config/, assets under assets/; avoid creating files at repo root.