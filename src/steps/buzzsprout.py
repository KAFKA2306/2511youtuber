from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Mapping

import requests

from src.core.step import Step
from src.utils.config import BuzzsproutStepConfig
from src.utils.secrets import load_secret_values


class BuzzsproutUploader(Step):
    name = "upload_buzzsprout"
    output_filename = "buzzsprout.json"
    is_required = False
    api_base = "https://www.buzzsprout.com/api"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        buzzsprout_config: BuzzsproutStepConfig | Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        data = buzzsprout_config if isinstance(buzzsprout_config, BuzzsproutStepConfig) else buzzsprout_config or {}
        self.config = BuzzsproutStepConfig.model_validate(data)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        audio_path = Path(inputs["synthesize_audio"])

        cfg = self.config
        token = self._resolve_secret(cfg.token_key)
        podcast_id = cfg.podcast_id or self._resolve_secret(cfg.podcast_id_key)
        title = cfg.title_template.format(run_id=self.run_id)
        payload = {
            "title": title,
            "description": title,
            "private": str(not cfg.publish_immediately).lower(),
        }
        headers = {
            "Authorization": f"Token token={token}",
            "User-Agent": "youtube-ai-v2/1.0",
        }
        content_type = "audio/wav" if audio_path.suffix.lower() == ".wav" else "audio/mpeg"
        url = f"{self.api_base}/{podcast_id}/episodes.json"

        with audio_path.open("rb") as handle:
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                files={"audio_file": (audio_path.name, handle, content_type)},
                timeout=30,
            )

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(response.json(), ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    @staticmethod
    def _resolve_secret(key: str) -> str:
        return load_secret_values(key)[0]
