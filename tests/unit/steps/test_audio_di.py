import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from pydub import AudioSegment

from src.steps.audio import AudioSynthesizer


class MockTTSProvider:
    name = "mock_tts"

    def __init__(self):
        self.execute_called = False

    def is_available(self) -> bool:
        return True

    def execute(self, text: str, speaker: str, **kwargs: Any) -> AudioSegment:
        self.execute_called = True
        return AudioSegment.silent(duration=100)


def test_audio_synthesizer_dependency_injection():
    print("Running Fatal Test for AudioSynthesizer DI...")
    run_id = "test_run"
    run_dir = Path("/tmp/test_run")
    run_dir.mkdir(parents=True, exist_ok=True)

    # Dummy config
    voicevox_config = {"enabled": True, "url": "http://localhost:50021", "speakers": {}}

    mock_provider = MockTTSProvider()

    # Act
    try:
        # This should fail if DI is not implemented
        step = AudioSynthesizer(
            run_id=run_id,
            run_dir=run_dir,
            voicevox_config=voicevox_config,
            tts_provider=mock_provider,  # <--- Injected dependency
        )
    except TypeError as e:
        print(f"❌ FAILED: AudioSynthesizer does not accept 'tts_provider'. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ FAILED: Unexpected error during instantiation: {e}")
        sys.exit(1)

    # Verify internal state
    if not hasattr(step, "provider") or step.provider != mock_provider:
        print("❌ FAILED: AudioSynthesizer did not store the injected provider correctly.")
        sys.exit(1)

    print("✅ SUCCESS: AudioSynthesizer accepted the injected provider!")
    sys.exit(0)


if __name__ == "__main__":
    test_audio_synthesizer_dependency_injection()
