from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.utils.secrets import load_secret_values


class WorkflowConfig(BaseModel):
    default_run_dir: str
    checkpoint_enabled: bool


class NewsStepConfig(BaseModel):
    count: int
    query: str


class ScriptStepConfig(BaseModel):
    min_duration: int
    max_duration: int
    target_wow_score: float


class AudioStepConfig(BaseModel):
    sample_rate: int
    format: str


class VideoEffectConfig(BaseModel):
    type: str
    enabled: bool = True
    model_config = ConfigDict(extra="allow")


class VideoStepConfig(BaseModel):
    resolution: str
    fps: int
    codec: str
    preset: str
    crf: int
    effects: list[VideoEffectConfig] = Field(default_factory=list)


class SubtitleStepConfig(BaseModel):
    width_per_char_pixels: int
    min_visual_width: int
    max_visual_width: int


class ThumbnailStepConfig(BaseModel):
    enabled: bool = True
    width: int
    height: int
    background_color: str
    title_color: str
    subtitle_color: str
    accent_color: str
    padding: int = 80
    max_lines: int = 3
    max_chars_per_line: int = 12
    title_font_size: int = 96
    subtitle_font_size: int = 56
    font_path: str | None = None


class MetadataStepConfig(BaseModel):
    target_keywords: list[str]
    min_keyword_density: float
    max_title_length: int
    max_description_length: int
    default_tags: list[str] = Field(default_factory=list)


class YouTubeStepConfig(BaseModel):
    enabled: bool = True
    dry_run: bool = True
    default_visibility: str
    category_id: int
    default_tags: list[str] = Field(default_factory=list)


class StepsConfig(BaseModel):
    news: NewsStepConfig
    script: ScriptStepConfig
    audio: AudioStepConfig
    subtitle: SubtitleStepConfig
    video: VideoStepConfig
    thumbnail: ThumbnailStepConfig
    metadata: MetadataStepConfig
    youtube: YouTubeStepConfig


class GeminiProviderConfig(BaseModel):
    model: str
    temperature: float
    max_tokens: int


class LLMProvidersConfig(BaseModel):
    gemini: GeminiProviderConfig


class VOICEVOXProviderConfig(BaseModel):
    enabled: bool
    url: str
    speakers: Dict[str, int]


class Pyttsx3SpeakerConfig(BaseModel):
    rate: int


class Pyttsx3ProviderConfig(BaseModel):
    enabled: bool
    speakers: Dict[str, Pyttsx3SpeakerConfig]


class TTSProvidersConfig(BaseModel):
    voicevox: VOICEVOXProviderConfig
    pyttsx3: Pyttsx3ProviderConfig


class PerplexityNewsProviderConfig(BaseModel):
    enabled: bool = False
    model: str = "sonar"
    temperature: float = 0.2
    max_tokens: int = 2048


class DummyNewsProviderConfig(BaseModel):
    enabled: bool = False


class NewsProvidersConfig(BaseModel):
    perplexity: PerplexityNewsProviderConfig | None = None
    dummy: DummyNewsProviderConfig | None = None


class ProvidersConfig(BaseModel):
    llm: LLMProvidersConfig
    tts: TTSProvidersConfig
    news: NewsProvidersConfig


class LoggingConfig(BaseModel):
    level: str
    format: str


class Config(BaseModel):
    workflow: WorkflowConfig
    steps: StepsConfig
    providers: ProvidersConfig
    logging: LoggingConfig

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Config":
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        else:
            config_path = Path(config_path)

        with open(config_path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def get_gemini_api_keys(self) -> list[str]:
        return load_secret_values("GEMINI_API_KEY")
