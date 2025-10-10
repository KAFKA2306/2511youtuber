from pathlib import Path

import litellm
import yaml

from src.providers.base import Provider
from src.utils.logger import get_logger
from src.utils.secrets import load_secret_values


logger = get_logger(__name__)


class GeminiProvider(Provider):
    name = "gemini"
    priority = 1

    def __init__(self, model: str = "gemini/gemini-2.5-flash-preview-09-2025", temperature: float = 0.7, max_tokens: int = 4000):
        self.configured_model = model
        self.model = self._normalise_model_name(model)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_keys = self._get_api_keys()
        self.current_key_index = 0

    def _get_api_keys(self) -> list[str]:
        return load_secret_values("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return len(self.api_keys) > 0

    @staticmethod
    def _normalise_model_name(model: str) -> str:
        if "/" in model:
            return model
        return f"gemini/{model}" if not model.startswith("gemini/") else model

    def execute(self, prompt: str, **kwargs) -> str:
        if not self.api_keys:
            raise ValueError("No Gemini API keys available")

        for attempt in range(len(self.api_keys)):
            api_key = self.api_keys[self.current_key_index]

            try:
                logger.info(
                    "Calling Gemini API",
                    model=self.model,
                    configured_model=self.configured_model,
                    key_index=self.current_key_index,
                )

                response = litellm.completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    api_key=api_key
                )

                content = response.choices[0].message.content
                logger.info(
                    "Gemini API succeeded",
                    response_length=len(content),
                    model=self.model,
                    configured_model=self.configured_model,
                )
                return content

            except Exception as e:
                logger.warning(f"Gemini API failed with key {self.current_key_index}", error=str(e))
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

                if attempt == len(self.api_keys) - 1:
                    raise

        raise Exception("All Gemini API keys exhausted")


class DummyLLMProvider(Provider):
    name = "dummy_llm"
    priority = 999

    def is_available(self) -> bool:
        return True

    def execute(self, prompt: str, **kwargs) -> str:
        logger.warning("Using dummy LLM provider - returning mock script")
        return """segments:
  - speaker: 田中
    text: こんにちは、今日は金融ニュースをお届けします。
  - speaker: 鈴木
    text: よろしくお願いします。
  - speaker: ナレーター
    text: それでは始めましょう。
  - speaker: 田中
    text: 本日の主要なニュースは経済成長に関するものです。
  - speaker: 鈴木
    text: 具体的にはどのような内容でしょうか。
  - speaker: 田中
    text: 成長率が前年比で三パーセント上昇しました。
  - speaker: 鈴木
    text: それは良いニュースですね。
  - speaker: ナレーター
    text: 詳しく見ていきましょう。
  - speaker: 田中
    text: この成長は多くの要因によるものです。
  - speaker: 鈴木
    text: なるほど、ありがとうございました。
"""


def load_prompt_template(template_name: str) -> str:
    prompts_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
    with open(prompts_path) as f:
        prompts = yaml.safe_load(f)
    return prompts[template_name]["user_template"]
