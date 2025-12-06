#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import yaml
from aim import Repo

sys.path.append(str(Path(__file__).parent.parent))


def restore_prompt(run_id: str, template_name: str, dry_run: bool = False):
    print(f"🔍 Searching for run {run_id}...")
    
    repo = Repo(str(Path(__file__).parent.parent))
    run = repo.get_run(run_id)
    
    if not run:
        for candidate in repo.iter_runs():
            if candidate.get("run_id") == run_id:
                run = candidate
                break
    
    if not run:
        print(f"❌ Run {run_id} not found.")
        print(f"❌ Run {run_id} not found.")
        return

    key = f"{template_name}_raw_template"
    raw_content = run.get(key)

    if not raw_content:
        print(f"❌ Template '{template_name}' not found in run {run_id}.")
        print("Available keys:", [k for k in run.keys() if "_raw_template" in k])
        return

    print(f"✅ Found template version from run {run_id}")
    
    if dry_run:
        print("\n--- PREVIEW ---")
        print(raw_content)
        print("--- END PREVIEW ---")
        return

    prompts_path = Path(__file__).parent.parent / "config" / "prompts.yaml"
    with open(prompts_path, "r", encoding="utf-8") as f:
        current_config = yaml.safe_load(f)

    restored_section = yaml.safe_load(raw_content)
    current_config[template_name] = restored_section

    with open(prompts_path, "w", encoding="utf-8") as f:
        yaml.dump(current_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✅ Successfully restored '{template_name}' to config/prompts.yaml")


def main():
    parser = argparse.ArgumentParser(description="Restore prompt template from Aim history")
    parser.add_argument("run_id", help="The Run ID to restore from")
    parser.add_argument("--template", default="script_generation", help="Template name (default: script_generation)")
    parser.add_argument("--dry-run", action="store_true", help="Show preview without writing file")
    
    args = parser.parse_args()
    restore_prompt(args.run_id, args.template, args.dry_run)


if __name__ == "__main__":
    main()
