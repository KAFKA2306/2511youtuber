import time
from collections import deque
from pathlib import Path

import litellm
import yaml

from src.providers.base import has_credentials
from src.utils.secrets import load_secret_values


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        if model is None or temperature is None or max_tokens is None:
            from src.utils.config import Config

            defaults = Config.load().providers.llm.gemini

        if model is None:
            if defaults is None or defaults.model is None:
                raise ValueError("GeminiProvider model must be provided or configured under providers.llm.gemini.model")
            model = defaults.model

        if temperature is None:
            temperature = defaults.temperature if defaults is not None else 0.7

        if max_tokens is None:
            max_tokens = defaults.max_tokens if defaults is not None else 4000

        self.model = self._normalise_model_name(model)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)

        # Load fallback model if configured
        self.fallback_model = None
        if defaults is not None and hasattr(defaults, "fallback_model") and defaults.fallback_model:
            self.fallback_model = self._normalise_model_name(defaults.fallback_model)

        key_values = load_secret_values("GEMINI_API_KEY")
        self.api_keys = list(key_values)
        self._keys = deque(self.api_keys)

    is_available = has_credentials

    def execute(self, prompt: str, **kwargs) -> str:
        if not self._keys:
            raise RuntimeError("No Gemini API keys configured")

        # Try primary model first
        result = self._try_execute_with_model(self.model, prompt)
        if result is not None:
            return result

        # If primary model failed with 503 and fallback is configured, try fallback
        if self.fallback_model:
            print(f"🔄 Switching to fallback model: {self.fallback_model}")
            result = self._try_execute_with_model(self.fallback_model, prompt, is_fallback=True)
            if result is not None:
                return result

        # All attempts failed
        raise RuntimeError(
            f"All Gemini API keys failed with 503 errors for both primary ({self.model}) "
            f"and fallback ({self.fallback_model if self.fallback_model else 'none'}) models. "
            "The service is heavily overloaded. Please try again later."
        )

    def _try_execute_with_model(self, model: str, prompt: str, is_fallback: bool = False) -> str | None:
        """Try to execute with a specific model using all available API keys.

        Returns:
            Response content if successful, None if all keys failed with 503 errors
        """
        max_retries = len(self.api_keys)

        for attempt in range(max_retries):
            api_key = self._keys[0]
            self._keys.rotate(-1)

            try:
                response = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    api_key=api_key,
                )
                if not is_fallback and attempt > 0:
                    print(f"✅ Success with API key {attempt + 1}/{max_retries}")
                return response.choices[0].message.content

            except litellm.exceptions.InternalServerError as e:
                error_str = str(e)

                # Handle 503 Service Unavailable (overloaded)
                if "503" in error_str or "overloaded" in error_str.lower():
                    model_label = "fallback" if is_fallback else "primary"
                    print(f"⚠️  {model_label} model API key {attempt + 1}/{max_retries} overloaded, trying next key...")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Brief delay before next key
                        continue
                    else:
                        # All keys exhausted for this model, return None to try fallback
                        print(f"❌ All API keys exhausted for {model_label} model: {model}")
                        return None

                # For other errors, raise immediately
                raise

            except Exception:
                # For non-503 errors, raise immediately
                raise

        # If we get here, all keys failed with 503
        return None

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
