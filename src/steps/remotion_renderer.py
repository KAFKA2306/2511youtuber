"""Remotion.dev video renderer integration."""

import json
import subprocess
from pathlib import Path
from typing import Dict

from src.core.step import Step


class RemotionRenderer(Step):
    """
    Render video using Remotion.dev React framework.
    
    This step bridges the Python workflow with Remotion's programmatic video generation.
    It converts subtitle and audio data into Remotion props and calls the CLI renderer.
    """
    
    name = "render_remotion_video"
    output_filename = "remotion_video.mp4"
    
    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        remotion_project_dir: Path | None = None,
        composition_id: str = "NewsVideo",
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ):
        super().__init__(run_id, run_dir)
        self.remotion_project_dir = remotion_project_dir or Path(__file__).parent.parent.parent / "remotion"
        self.composition_id = composition_id
        self.width = width
        self.height = height
        self.fps = fps
    
    def execute(self, inputs: Dict[str, Path]) -> Path:
        """
        Execute Remotion rendering.
        
        Args:
            inputs: Dictionary with keys:
                - format_subtitles: Path to .srt subtitle file
                - synthesize_audio: Path to .wav audio file
        
        Returns:
            Path to rendered video file
        """
        # Load required inputs
        subtitles_path = Path(inputs.get("format_subtitles", ""))
        audio_path = Path(inputs.get("synthesize_audio", ""))
        
        if not subtitles_path.exists():
            raise ValueError(f"Subtitle file not found: {subtitles_path}")
        if not audio_path.exists():
            raise ValueError(f"Audio file not found: {audio_path}")
        
        # Prepare Remotion props
        props = self._prepare_props(subtitles_path, audio_path)
        run_dir = self.run_dir / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        props_file = run_dir / "remotion_props.json"
        props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Render video with Remotion
        output_path = self.get_output_path()
        self._run_remotion_render(props_file, output_path)
        
        return output_path
    
    def _prepare_props(self, subtitles_path: Path, audio_path: Path) -> dict:
        """Convert subtitle and audio data to Remotion props format."""
        subtitles = self._parse_srt(subtitles_path)
        
        return {
            "subtitles": subtitles,
            "audioUrl": f"file://{audio_path.absolute()}",
        }
    
    def _parse_srt(self, srt_path: Path) -> list[dict]:
        """
        Parse SRT subtitle file into Remotion format.
        
        Args:
            srt_path: Path to .srt file
        
        Returns:
            List of subtitle dicts with start, end, and text fields
        """
        content = srt_path.read_text(encoding="utf-8")
        subtitles = []
        
        for block in content.strip().split("\n\n"):
            lines = block.split("\n")
            if len(lines) >= 3:
                time_str = lines[1]
                text = " ".join(lines[2:])
                start, end = self._parse_srt_time(time_str)
                subtitles.append({"start": start, "end": end, "text": text})
        
        return subtitles
    
    def _parse_srt_time(self, time_str: str) -> tuple[float, float]:
        """Parse SRT timestamp range (HH:MM:SS,mmm --> HH:MM:SS,mmm) to seconds."""
        start_str, end_str = time_str.split(" --> ")
        return self._srt_to_seconds(start_str), self._srt_to_seconds(end_str)
    
    @staticmethod
    def _srt_to_seconds(srt_time: str) -> float:
        """Convert SRT time format (HH:MM:SS,mmm) to seconds."""
        time_part, ms_part = srt_time.replace(",", ".").split(".")
        h, m, s = map(int, time_part.split(":"))
        return h * 3600 + m * 60 + s + float(f"0.{ms_part}")
    
    def _run_remotion_render(self, props_file: Path, output_path: Path):
        """
        Execute Remotion CLI to render video.
        
        Args:
            props_file: Path to JSON file containing Remotion props
            output_path: Where to save the rendered video
        
        Raises:
            RuntimeError: If Remotion render fails
        """
        cmd = [
            "npx",
            "remotion",
            "render",
            str(self.remotion_project_dir / "src/index.ts"),
            self.composition_id,
            str(output_path),
            "--props",
            f"@{props_file}",  # @ prefix loads from file
            "--overwrite",
            "--height",
            str(self.height),
            "--width",
            str(self.width),
            "--fps",
            str(self.fps),
        ]
        
        print(f"🎬 Rendering with Remotion: {self.composition_id}")
        print(f"   Props: {props_file}")
        print(f"   Output: {output_path}")
        
        result = subprocess.run(
            cmd,
            cwd=self.remotion_project_dir,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            error_msg = f"Remotion render failed:\n{result.stderr}\n{result.stdout}"
            raise RuntimeError(error_msg)
        
        print(f"✅ Remotion render complete: {output_path}")
