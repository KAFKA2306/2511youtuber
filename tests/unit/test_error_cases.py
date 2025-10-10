import pytest
from pathlib import Path
from src.steps.script import ScriptGenerator
from src.models import ScriptSegment, Script
from src.providers.base import AllProvidersFailedError, ProviderChain
from src.steps.base import StepExecutionError


class TestScriptParsingErrors:
    def test_malformed_yaml(self, temp_run_dir, test_run_id):
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)

        malformed_yaml = "segments:\n  - speaker田中\n    text: broken"

        with pytest.raises((ValueError, Exception)):
            step._parse_and_validate(malformed_yaml)

    def test_json_fallback_on_yaml_error(self, temp_run_dir, test_run_id):
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)

        json_string = '{"segments": [{"speaker": "田中", "text": "こんにちは"}]}'

        script = step._parse_and_validate(json_string)
        assert len(script.segments) == 1

    def test_max_recursion_depth(self, temp_run_dir, test_run_id):
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)

        deeply_nested = '"' * 10 + "invalid" + '"' * 10

        with pytest.raises(ValueError, match="recursion"):
            step._parse_and_validate(deeply_nested, max_depth=3)


class TestJapanesePurityValidation:
    def test_reject_english_in_script(self):
        with pytest.raises(ValueError, match="Non-Japanese"):
            ScriptSegment(speaker="田中", text="Hello world")

    def test_reject_mixed_language(self):
        with pytest.raises(ValueError, match="Non-Japanese"):
            ScriptSegment(speaker="鈴木", text="今日はgood day")

    def test_accept_pure_japanese_with_numbers(self):
        segment = ScriptSegment(speaker="田中", text="今日は2025年10月10日です。")
        assert segment.text == "今日は2025年10月10日です。"

    def test_accept_japanese_punctuation(self):
        segment = ScriptSegment(speaker="ナレーター", text="こんにちは！今日は良い天気ですね。")
        assert segment.text


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

        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)

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
