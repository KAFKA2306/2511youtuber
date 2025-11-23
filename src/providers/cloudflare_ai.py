from __future__ import annotations

import os

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CloudflareAIClient:
    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        model: str = "@cf/bytedance/stable-diffusion-xl-lightning",
    ) -> None:
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "dc1aa018702e10045b00865b63f144d0")
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.model = model
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run"

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1920,
        height: int = 1080,
        num_steps: int = 6,
        seed: int | None = None,
        guidance: float = 7.5,
        model: str | None = None,
    ) -> bytes:
        target_model = model or self.model
        url = f"{self.base_url}/{target_model}"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_steps": num_steps,
            "guidance": guidance,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed is not None:
            payload["seed"] = seed

        logger.info(
            "Generating image with model=%s width=%d height=%d steps=%d", target_model, width, height, num_steps
        )
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content
