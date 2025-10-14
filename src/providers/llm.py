from collections import deque
from pathlib import Path

import litellm
import yaml

from src.utils.secrets import load_secret_values


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        defaults = None
        if model is None or temperature is None or max_tokens is None:
            try:
                from src.utils.config import Config

                defaults = Config.load().providers.llm.gemini
            except Exception:
                defaults = None

        if model is None:
            if defaults is None or defaults.model is None:
                raise ValueError(
                    "GeminiProvider model must be provided or configured under providers.llm.gemini.model"
                )
            model = defaults.model

        if temperature is None:
            temperature = defaults.temperature if defaults is not None else 0.7

        if max_tokens is None:
            max_tokens = defaults.max_tokens if defaults is not None else 4000

        self.model = self._normalise_model_name(model)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
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

    @staticmethod
    def _normalise_model_name(model: str) -> str:
        value = model.strip()
        if value.startswith("gemini/") or "/" in value:
            return value
        return f"gemini/{value}"


def load_prompt_template(template_name: str) -> str:
    prompts_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
    with open(prompts_path) as f:
        prompts = yaml.safe_load(f)
    return prompts[template_name]["user_template"]
