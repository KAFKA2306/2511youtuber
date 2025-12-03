import sys
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.steps.scene_generator import SceneGenerator
from src.services.image_generation import ImageGenerationService, ImageGenerationRequest, ImageGenerationResult

class MockImageService:
    def is_available(self) -> bool:
        return True
        
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        return ImageGenerationResult(image=None, seed=0, prompt=request.prompt)

    def generate_batch(self, requests: List[ImageGenerationRequest]) -> List[ImageGenerationResult]:
        return [self.generate(req) for req in requests]

def test_scene_generator_dependency_injection():
    print("Running Fatal Test for SceneGenerator DI...")
    run_id = "test_run"
    run_dir = Path("/tmp/test_run")
    run_dir.mkdir(parents=True, exist_ok=True)
    
    mock_service = MockImageService()
    
    # Act
    try:
        # This should fail if DI is not strictly enforced (i.e. if it tries to instantiate ZImageTurboService internally when None is passed, or if we want to enforce passing it)
        # For this refactoring, we want to ENFORCE passing the service.
        step = SceneGenerator(
            run_id=run_id, 
            run_dir=run_dir, 
            image_service=mock_service # <--- Injected dependency
        )
    except TypeError as e:
        print(f"❌ FAILED: SceneGenerator does not accept 'image_service'. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ FAILED: Unexpected error during instantiation: {e}")
        sys.exit(1)
        
    # Verify internal state
    if not hasattr(step, "image_service") or step.image_service != mock_service:
         print("❌ FAILED: SceneGenerator did not store the injected service correctly.")
         sys.exit(1)

    print("✅ SUCCESS: SceneGenerator accepted the injected service!")
    sys.exit(0)

if __name__ == "__main__":
    test_scene_generator_dependency_injection()
