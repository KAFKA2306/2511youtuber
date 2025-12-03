import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.steps.script import ScriptGenerator
from src.models import Script

class MockLLMProvider:
    name = "mock_llm"
    model = "mock_model"
    
    def __init__(self, response: str):
        self.response = response
        self.execute_called = False
        
    def is_available(self) -> bool:
        return True
        
    def execute(self, prompt: str, **kwargs: Any) -> str:
        self.execute_called = True
        return self.response

def test_script_generator_dependency_injection():
    print("Running Fatal Test for ScriptGenerator DI...")
    run_id = "test_run"
    run_dir = Path("/tmp/test_run")
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Dummy speakers config
    speakers_config = {
        "analyst": {"name": "Analyst", "aliases": []},
        "reporter": {"name": "Reporter", "aliases": []},
        "narrator": {"name": "Narrator", "aliases": []}
    }
    
    mock_response = """
    {
        "segments": [
            {"speaker": "Analyst", "text": "Hello world。"}
        ]
    }
    """
    mock_provider = MockLLMProvider(response=mock_response)
    
    # Act
    try:
        # This should fail if DI is not implemented
        step = ScriptGenerator(
            run_id=run_id, 
            run_dir=run_dir, 
            speakers_config=speakers_config,
            llm_provider=mock_provider # <--- Injected dependency
        )
    except TypeError as e:
        print(f"❌ FAILED: ScriptGenerator does not accept 'llm_provider'. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ FAILED: Unexpected error during instantiation: {e}")
        sys.exit(1)
        
    # Verify internal state
    if not hasattr(step, "provider") or step.provider != mock_provider:
         print("❌ FAILED: ScriptGenerator did not store the injected provider correctly.")
         sys.exit(1)

    print("✅ SUCCESS: ScriptGenerator accepted the injected provider!")
    sys.exit(0)

if __name__ == "__main__":
    test_script_generator_dependency_injection()
