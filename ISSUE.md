# Issue: Failing tests after recent refactor

**Repository:** `2511youtuber`

**Description:**
After overhauling the testing strategy and fixing several initialization bugs, most tests now pass. However, two fast tests continue to fail:

1. `test_custom_news_query`
2. `test_different_duration_configs`

Both failures occur during the `collect_news` step, suggesting a problem with the news provider configuration or error handling in `NewsCollector`.

**Steps to Reproduce**
```bash
# Ensure API keys are set in the environment
uv run pytest tests -v -m "fast or not slow"
```
You will see failures similar to:
```
FAILED tests/test_real_workflow.py::test_custom_news_query - AssertionError: assert 'failed' == 'success'
FAILED tests/test_real_workflow.py::test_different_duration_configs - AssertionError: assert 'failed' == 'success'
```

**Expected Result:** All fast tests should pass.

**Actual Result:** The two tests fail with a workflow status of `failed`.

**Possible Causes:**
- Missing or incorrect API credentials for Perplexity/Gemini.
- `NewsCollector` may not be correctly building providers from `config.providers.news`.
- Exceptions from providers are not being logged, making debugging difficult.

**Suggested Investigation:**
- Add logging inside `NewsCollector.execute` to capture provider exceptions.
- Verify that `load_secret_values` correctly loads the required keys.
- Ensure `NewsProvidersConfig` matches the expected schema.

**Next Steps:**
1. Enhance error handling in `NewsCollector`.
2. Re‑run the failing tests after confirming credentials.
3. Update the issue with any new error messages.

---
*You can copy the contents of this file into a new GitHub issue in the repository.*
