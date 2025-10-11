from collections import deque
from pathlib import Path

import litellm
import yaml

from src.utils.secrets import load_secret_values


class GeminiProvider:
    name = "gemini"

    def __init__(
        self, model: str = "gemini/gemini-2.5-flash-preview-09-2025", temperature: float = 0.7, max_tokens: int = 4000
    ):
        self.model = model if "/" in model else f"gemini/{model}" if not model.startswith("gemini/") else model
        self.temperature = temperature
        self.max_tokens = max_tokens
        key_values = load_secret_values("GEMINI_API_KEY")
        self.api_keys = list(key_values)
        self._keys = deque(self.api_keys)

    def is_available(self) -> bool:
        return bool(self.api_keys)

    def execute(self, prompt: str, **kwargs) -> str:
        if not self._keys:
            raise RuntimeError("No Gemini API keys configured")
        api_key = self._keys[0]
        self._keys.rotate(-1)
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=api_key,
        )
        return response.choices[0].message.content


def load_prompt_template(template_name: str) -> str:
    prompts_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
    with open(prompts_path) as f:
        prompts = yaml.safe_load(f)
    return prompts[template_name]["user_template"]
