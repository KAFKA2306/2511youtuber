from pathlib import Path

import pytest

from src.providers.base import AllProvidersFailedError, ProviderChain
from src.steps.base import StepExecutionError
from src.steps.script import ScriptGenerator
from src.utils.config import Config

pytestmark = pytest.mark.unit


class TestScriptParsingErrors:
    def test_malformed_yaml(self, temp_run_dir, test_run_id):
        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        malformed_yaml = "segments:\n  - speaker春日部つむぎ\n    text: broken"

        with pytest.raises((ValueError, Exception)):
            step._parse_and_validate(malformed_yaml)

    def test_json_fallback_on_yaml_error(self, temp_run_dir, test_run_id):
        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        json_string = '{"segments": [{"speaker": "春日部つむぎ", "text": "こんにちは"}]}'

        script = step._parse_and_validate(json_string)
        assert len(script.segments) == 1

    def test_parse_allows_prefixed_code_block(self, temp_run_dir, test_run_id):
        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        wrapped = "了解です！\n```yaml\nsegments:\n  - speaker: 春日部つむぎ\n    text: こんにちは\n```"

        script = step._parse_and_validate(wrapped)
        assert script.segments[0].speaker == "春日部つむぎ"

    def test_parse_allows_inline_segments_without_fence(self, temp_run_dir, test_run_id):
        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        prefixed = "こちらが台本です:\nsegments:\n  - speaker: 春日部つむぎ\n    text: こんにちは"

        script = step._parse_and_validate(prefixed)
        assert script.segments[0].text.startswith("こんにちは")

    def test_max_recursion_depth(self, temp_run_dir, test_run_id):
        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        deeply_nested = '"' * 10 + "invalid" + '"' * 10

        with pytest.raises(ValueError, match="recursion"):
            step._parse_and_validate(deeply_nested, max_depth=3)


class TestProviderChainErrors:
    def test_all_providers_fail(self):
        from src.providers.base import Provider

        class FailingProvider(Provider):
            name = "failing"
            priority = 1

            def is_available(self):
                return True

            def execute(self, **kwargs):
                raise Exception("Provider failed")

        chain = ProviderChain([FailingProvider()])

        with pytest.raises(AllProvidersFailedError):
            chain.execute()

    def test_unavailable_providers_skipped(self):
        from src.providers.base import Provider

        class UnavailableProvider(Provider):
            name = "unavailable"
            priority = 1

            def is_available(self):
                return False

            def execute(self, **kwargs):
                raise Exception("Should not be called")

        class WorkingProvider(Provider):
            name = "working"
            priority = 2

            def is_available(self):
                return True

            def execute(self, **kwargs):
                return "success"

        chain = ProviderChain([UnavailableProvider(), WorkingProvider()])
        result = chain.execute()

        assert result == "success"


class TestStepExecutionErrors:
    def test_missing_input_file(self, temp_run_dir, test_run_id):
        from src.steps.script import ScriptGenerator

        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        with pytest.raises(ValueError, match="not found"):
            step.run({"collect_news": Path("/nonexistent/news.json")})

    def test_step_without_output_file(self, temp_run_dir, test_run_id):
        from src.steps.base import Step

        class BrokenStep(Step):
            name = "broken"
            output_filename = "broken.txt"

            def execute(self, inputs):
                return Path("/nonexistent/output.txt")

        step = BrokenStep(run_id=test_run_id, run_dir=temp_run_dir)

        with pytest.raises(StepExecutionError):
            step.run({})


class TestWorkflowStateErrors:
    def test_load_corrupted_state(self, temp_run_dir, test_run_id):
        from src.models import WorkflowState

        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True)

        state_path = run_path / "state.json"
        with open(state_path, "w") as f:
            f.write("invalid json{")

        with pytest.raises(Exception):
            WorkflowState.load_or_create(test_run_id, temp_run_dir)
