#!/usr/bin/env python3
"""
Standalone test script to verify scene generation on an existing run.
Usage: python test_scene_gen.py <run_id>
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.steps.scene_generator import SceneGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_scene_gen.py <run_id>")
        print("Example: python test_scene_gen.py 20251130_120005")
        sys.exit(1)
    
    run_id = sys.argv[1]
    run_dir = Path("runs")
    
    if not (run_dir / run_id).exists():
        print(f"❌ Run directory not found: {run_dir / run_id}")
        sys.exit(1)
    
    # Check required inputs (handle both old flat structure and new nested structure)
    script_path = run_dir / run_id / "generate_script" / "script.json"
    if not script_path.exists():
        script_path = run_dir / run_id / "script.json"  # Old structure
    
    news_path = run_dir / run_id / "collect_news" / "news.json"
    if not news_path.exists():
        news_path = run_dir / run_id / "news.json"  # Old structure
    
    metadata_path = run_dir / run_id / "analyze_metadata" / "metadata.json"
    if not metadata_path.exists():
        metadata_path = run_dir / run_id / "metadata.json"  # Old structure
    
    if not script_path.exists():
        print(f"❌ Script not found in either location")
        print(f"   Tried: {run_dir / run_id / 'generate_script' / 'script.json'}")
        print(f"   Tried: {run_dir / run_id / 'script.json'}")
        sys.exit(1)
    
    print(f"✅ Found run: {run_id}")
    print(f"✅ Script: {script_path}")
    print(f"✅ News: {news_path if news_path.exists() else 'N/A'}")
    print(f"✅ Metadata: {metadata_path if metadata_path.exists() else 'N/A'}")
    print()
    
    # Configure scene generator (test with small settings)
    config = {
        "enabled": True,
        "images_per_video": 2,  # Only 2 scenes for quick test
        "variants_per_type": 1,  # Only 1 variant per type for quick test
        "width": 1280,
        "height": 720,
        "num_steps": 6,  # Faster generation for testing
        "scene_duration_seconds": 30,
        "model_path": "external/hf-cache-hub/models/Z-Image-Turbo",
        "device": "cuda",
        # Performance optimization (NEW in v2.1)
        "batch_size": 2,  # Process 2 images at once for 1.5-1.8x speedup
        "compile_model": False,  # Set True for 10-20% speedup (adds startup overhead)
    }
    
    print("🎨 Initializing SceneGenerator...")
    print(f"   - Scenes: {config['images_per_video']}")
    print(f"   - Variants per type: {config['variants_per_type']}")
    print(f"   - Total images: {config['images_per_video'] * 3 * config['variants_per_type']}")
    print(f"   - Resolution: {config['width']}x{config['height']}")
    print(f"   - Batch size: {config['batch_size']} (clean architecture v2.1)")
    print(f"   - Model compilation: {'Enabled' if config['compile_model'] else 'Disabled'}")
    print()
    
    generator = SceneGenerator(
        run_id=run_id,
        run_dir=run_dir,
        scene_config=config,
    )
    
    # Prepare inputs
    inputs = {
        "generate_script": str(script_path),
    }
    
    if news_path.exists():
        inputs["collect_news"] = str(news_path)
    
    if metadata_path.exists():
        inputs["analyze_metadata"] = str(metadata_path)
    
    print("🚀 Starting scene generation...")
    print()
    
    try:
        output_path = generator.execute(inputs)
        print()
        print(f"✅ Scene generation completed!")
        print(f"   Output: {output_path}")
        print()
        
        # Show generated files
        scene_dir = output_path.parent
        print("📁 Generated files:")
        for scene_subdir in sorted(scene_dir.glob("scene_*")):
            if scene_subdir.is_dir():
                print(f"   {scene_subdir.name}/")
                for img in sorted(scene_subdir.glob("*.png")):
                    size_mb = img.stat().st_size / 1024 / 1024
                    print(f"      - {img.name} ({size_mb:.2f} MB)")
        
        print()
        print(f"🎉 Test successful! Check output at: {scene_dir}")
        
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
