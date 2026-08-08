from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.core.state import WorkflowState
from src.utils.prompt_version import prompt_bundle_version


class PromptVersionTests(unittest.TestCase):
    def test_prompt_version_is_content_addressed_and_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompts = Path(tmp) / "prompts.yaml"
            first = b"script_generation:\n  user_template: first\n"
            prompts.write_bytes(first)

            expected = f"sha256:{hashlib.sha256(first).hexdigest()}"
            self.assertEqual(prompt_bundle_version(prompts), expected)
            self.assertEqual(prompt_bundle_version(prompts), expected)

            prompts.write_text("script_generation:\n  user_template: second\n", encoding="utf-8")
            self.assertNotEqual(prompt_bundle_version(prompts), expected)

    def test_workflow_state_persists_prompt_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            version = "sha256:" + "a" * 64
            state = WorkflowState(run_id="run-1", prompt_version=version)
            state.save(run_dir)

            payload = json.loads((run_dir / "run-1" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["prompt_version"], version)

            restored = WorkflowState.load_or_create("run-1", run_dir)
            self.assertEqual(restored.prompt_version, version)


if __name__ == "__main__":
    unittest.main()
