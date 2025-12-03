#!/usr/bin/env python3
"""
Mass Generation & Gallery Script for Z-Image Turbo (Refactored).

This script:
1. Loads context (script, news, metadata) from a specific RUN ID.
2. Generates images for ALL combinations of:
   - Scene Types (Literal, Abstract, Atmospheric)
   - Moods (Crisis, Opportunity, Neutral)
   - Core Elements (from config)
3. Creates a comprehensive HTML gallery for review.

Usage:
    uv run python scripts/mass_generate_gallery.py [RUN_ID]
    
    If RUN_ID is not provided, it uses the latest run.
"""
import sys
import yaml
import json
import argparse
from pathlib import Path
from datetime import datetime
import torch
from diffusers import ZImagePipeline

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.core.io_utils import load_json
from src.steps.scene_generator import (
    SceneContext,
    ContextExtractor,
    PromptBuilder,
    SceneType
)

logger = get_logger(__name__)

def get_latest_run_id(runs_dir: Path) -> str:
    """Find the latest run ID in the runs directory that has a script."""
    # Filter for directories that look like timestamps (start with 202)
    runs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("202")]
    if not runs:
        return None
    
    # Sort by name (timestamp) descending
    for run in sorted(runs, key=lambda x: x.name, reverse=True):
        # Check if it has a script
        if (run / "generate_script" / "script.json").exists() or (run / "script.json").exists():
            return run.name
            
    return None

def load_run_context(run_dir: Path) -> SceneContext:
    """Load script, news, and metadata to build SceneContext."""
    
    # 1. Load Script
    script_path = run_dir / "generate_script" / "script.json"
    if not script_path.exists():
        script_path = run_dir / "script.json" # Fallback
    
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found in {run_dir}")
        
    script_data = load_json(script_path)
    segments = script_data.get("segments", [])
    
    # 2. Load News (Optional)
    news_path = run_dir / "collect_news" / "news.json"
    if not news_path.exists():
        news_path = run_dir / "news.json"
    
    news_data = load_json(news_path) if news_path.exists() else None
    
    # 3. Load Metadata (Optional)
    meta_path = run_dir / "analyze_metadata" / "metadata.json"
    if not meta_path.exists():
        meta_path = run_dir / "metadata.json"
        
    metadata = load_json(meta_path) if meta_path.exists() else None
    
    # 4. Build Context
    # We need to extract entities from the first few segments to simulate real usage
    first_segments_text = " ".join([s.get("text", "") for s in segments[:5]])
    
    # Simple entity extraction (can reuse logic if needed, but for now simple list)
    # In a real scenario, we might want to import the exact logic from SceneGenerator
    # For now, we'll use a placeholder or simple extraction if not available
    # Actually, let's use the one from SceneGenerator if possible, but it's an instance method _extract_entities
    # We can just pass an empty list or simple mock for now as it's less critical for *mass* generation of *styles*
    # unless the prompt builder heavily relies on it.
    # Looking at PromptBuilder, it doesn't seem to use top_entities heavily in the current implementation 
    # (it mostly uses core elements from config).
    
    context = SceneContext(
        title=metadata.get("title", "") if metadata else "No Title",
        description=metadata.get("description", "") if metadata else "",
        segments=segments,
        news_keywords=ContextExtractor.extract_news_keywords(news_data) if news_data else [],
        market_sentiment=ContextExtractor.extract_market_sentiment(None), # Stats not loaded for now
        top_entities=[] # Placeholder
    )
    
    return context

def generate_gallery(output_dir: Path, images_data: list, run_id: str, context: SceneContext):
    """Generate a rich HTML gallery."""
    
    # Format context for display
    keywords_html = ", ".join([f"<span class='tag'>{k}</span>" for k in context.news_keywords])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Z-Image Turbo Gallery - Run {run_id}</title>
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #111; color: #eee; padding: 0; margin: 0; }}
            header {{ background: #1a1a1a; padding: 20px; border-bottom: 1px solid #333; position: sticky; top: 0; z-index: 100; }}
            h1 {{ margin: 0; font-size: 24px; color: #fff; }}
            .meta {{ font-size: 14px; color: #888; margin-top: 10px; }}
            .tag {{ background: #333; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-right: 5px; }}
            
            .container {{ padding: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }}
            
            .card {{ background: #1e1e1e; border-radius: 12px; overflow: hidden; border: 1px solid #333; transition: transform 0.2s; }}
            .card:hover {{ transform: translateY(-2px); border-color: #555; }}
            
            .img-wrapper {{ position: relative; padding-top: 56.25%; /* 16:9 */ background: #000; }}
            .img-wrapper img {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
            
            .info {{ padding: 15px; }}
            .badges {{ display: flex; gap: 8px; margin-bottom: 10px; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
            
            .type-literal {{ background: #2E7D32; color: #fff; }}
            .type-abstract {{ background: #1565C0; color: #fff; }}
            .type-atmospheric {{ background: #6A1B9A; color: #fff; }}
            
            .mood-crisis {{ background: #C62828; color: #fff; }}
            .mood-opportunity {{ background: #F9A825; color: #000; }}
            .mood-neutral {{ background: #424242; color: #fff; }}
            
            .prompt-box {{ background: #111; padding: 10px; border-radius: 6px; font-size: 11px; color: #aaa; max-height: 80px; overflow-y: auto; font-family: monospace; }}
            .param-row {{ display: flex; justify-content: space-between; font-size: 11px; color: #666; margin-top: 8px; }}
        </style>
    </head>
    <body>
        <header>
            <h1>Z-Image Turbo Gallery</h1>
            <div class="meta">
                Run ID: <strong>{run_id}</strong> | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                <br>
                Keywords: {keywords_html}
            </div>
        </header>
        
        <div class="container">
            <div class="grid">
    """
    
    for img in images_data:
        type_cls = f"type-{img['type']}"
        mood_cls = f"mood-{img['mood']}"
        
        html += f"""
            <div class="card">
                <div class="img-wrapper">
                    <img src="{img['filename']}" loading="lazy" alt="{img['type']} {img['mood']}">
                </div>
                <div class="info">
                    <div class="badges">
                        <span class="badge {type_cls}">{img['type']}</span>
                        <span class="badge {mood_cls}">{img['mood']}</span>
                    </div>
                    <div class="prompt-box">{img['prompt']}</div>
                    <div class="param-row">
                        <span>Core: {img['core_element'][:30]}...</span>
                    </div>
                </div>
            </div>
        """
        
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Gallery created at: {output_dir / 'index.html'}")

def main():
    parser = argparse.ArgumentParser(description="Mass generate scenes from run context")
    parser.add_argument("run_id", nargs="?", help="Run ID to use (default: latest)")
    args = parser.parse_args()
    
    root_dir = Path(__file__).parent.parent
    runs_dir = root_dir / "runs"
    
    # 1. Determine Run ID
    run_id = args.run_id or get_latest_run_id(runs_dir)
    if not run_id:
        print("❌ No runs found in runs/ directory.")
        sys.exit(1)
        
    run_dir = runs_dir / run_id
    if not run_dir.exists():
        print(f"❌ Run directory not found: {run_dir}")
        sys.exit(1)
        
    print(f"📂 Using Run ID: {run_id}")
    
    # 2. Load Context
    try:
        context = load_run_context(run_dir)
        print(f"✅ Context loaded: {len(context.segments)} segments, {len(context.news_keywords)} keywords")
    except Exception as e:
        print(f"❌ Failed to load context: {e}")
        sys.exit(1)
        
    # 3. Load Config & Initialize Builder
    config_path = root_dir / "config" / "scene_prompts.yaml"
    with open(config_path, "r") as f:
        prompts_cfg = yaml.safe_load(f)
        
    prompt_builder = PromptBuilder(prompts_cfg)
    
    # 4. Initialize Model
    print("🚀 Loading Z-Image-Turbo...")
    model_path = root_dir / "external/hf-cache-hub/models/Z-Image-Turbo"
    pipe = ZImagePipeline.from_pretrained(
        str(model_path),
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=False
    ).to("cuda")
    
    # 5. Prepare Tasks (Combinatorial Explosion!)
    tasks = []
    output_dir = root_dir / "runs" / f"gallery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_run_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # We want to iterate over ALL core elements for ALL types for ALL moods
    # This might be a lot, so we might want to limit core elements if there are too many
    
    # Helper to access private/protected config in builder if needed, 
    # or just read from loaded cfg directly (easier)
    
    scene_types = ["literal", "abstract", "atmospheric"]
    moods = ["crisis", "opportunity", "neutral"]
    
    # Mock segment text for prompt building (we use a generic one or one from context)
    # The prompt builder uses segment text mainly for context, but for mass gen we might want to see 
    # how it behaves with a "typical" segment from the run.
    sample_segment_text = " ".join([s.get("text", "") for s in context.segments[:3]])
    
    task_id = 0
    
    for s_type in scene_types:
        type_cfg = prompts_cfg.get(s_type, {})
        core_elements = type_cfg.get("core_elements", [])
        
        # Limit core elements to avoid generating hundreds of images if list is huge
        # But user asked for "網羅的に" (exhaustively), so let's try to be comprehensive 
        # but maybe cap at 5 per type if list is long? 
        # Let's do ALL for now, assuming lists aren't massive (usually 5-10).
        
        for core in core_elements:
            for mood in moods:
                # We need to "force" the core element into the prompt builder
                # The current PromptBuilder selects randomly. 
                # We might need to bypass the random selection or subclass/modify it.
                # Since we want to test specific combinations, we should probably construct the prompt manually 
                # using the same logic as PromptBuilder but with fixed choices.
                
                # RE-IMPLEMENTING PromptBuilder logic here for deterministic control
                # (Or we could modify PromptBuilder to accept overrides, but that changes src code)
                
                common = prompts_cfg.get("common", {})
                mood_mods = type_cfg.get("mood_modifiers", {}).get(mood, {})
                
                # Base parts
                parts = []
                
                # 1. Core Element (Fixed)
                parts.append(core)
                
                # 2. Mood Modifiers
                if s_type == "literal":
                    parts.append(mood_mods.get("lighting", ""))
                    parts.append(mood_mods.get("atmosphere", ""))
                    parts.append(mood_mods.get("color", ""))
                elif s_type == "abstract":
                    parts.append(mood_mods.get("atmosphere", ""))
                    parts.append(mood_mods.get("color", ""))
                    parts.append(mood_mods.get("motion", ""))
                elif s_type == "atmospheric":
                    parts.append(mood_mods.get("color", ""))
                    parts.append(mood_mods.get("effect", ""))
                
                # 3. Boosters (Pick one fixed or none for purity? Let's pick first one for consistency)
                boosters = prompts_cfg.get("youtube_boosters", [])
                if boosters:
                    parts.append(boosters[0]) 
                
                # 4. Common Quality
                parts.append(common.get("youtube_appeal", ""))
                parts.append(common.get("quality", ""))
                
                # Construct
                final_prompt = ", ".join([p for p in parts if p])
                
                # Negative
                neg_base = common.get("negative_base", "")
                neg_extra = type_cfg.get("negative_extra", "")
                negative_prompt = f"{neg_base}, {neg_extra}"
                
                filename = f"{s_type}_{mood}_{task_id:03d}.png"
                
                tasks.append({
                    "type": s_type,
                    "mood": mood,
                    "core_element": core,
                    "prompt": final_prompt,
                    "negative_prompt": negative_prompt,
                    "filename": filename
                })
                task_id += 1

    print(f"📋 Found {len(tasks)} variations to generate.")
    
    generated_data = []
    
    # Generate
    for i, task in enumerate(tasks):
        print(f"[{i+1}/{len(tasks)}] {task['type']} / {task['mood']}...")
        
        image = pipe(
            prompt=task["prompt"],
            negative_prompt=task["negative_prompt"],
            num_inference_steps=9,
            guidance_scale=0.0,
            height=720,
            width=1280
        ).images[0]
        
        save_path = output_dir / task["filename"]
        image.save(save_path)
        
        # Update task with full path for gallery (relative)
        task["filename"] = task["filename"]
        generated_data.append(task)
        
    # Create Gallery
    generate_gallery(output_dir, generated_data, run_id, context)
    
    print("\n🎉 Mass generation complete!")
    print(f"📂 Output directory: {output_dir}")
    print(f"👀 Open {output_dir}/index.html to review images.")

if __name__ == "__main__":
    main()
