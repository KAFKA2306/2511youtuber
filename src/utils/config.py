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


class SpeakerProfileConfig(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)


class ScriptSpeakersConfig(BaseModel):
    analyst: SpeakerProfileConfig
    reporter: SpeakerProfileConfig
    narrator: SpeakerProfileConfig


class ScriptStepConfig(BaseModel):
    min_duration: int
    max_duration: int
    target_wow_score: float
    speakers: ScriptSpeakersConfig


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


class ThumbnailOverlayOffsetConfig(BaseModel):
    top: int | None = None
    right: int | None = None
    bottom: int | None = None
    left: int | None = None


class ThumbnailOverlayConfig(BaseModel):
    name: str | None = None
    enabled: bool = True
    image_path: str
    anchor: str = "bottom_right"
    height_ratio: float | None = None
    width_ratio: float | None = None
    height: int | None = None
    width: int | None = None
    offset: ThumbnailOverlayOffsetConfig | None = None


class ThumbnailStepConfig(BaseModel):
    enabled: bool = False
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
    overlays: list[ThumbnailOverlayConfig] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class MetadataStepConfig(BaseModel):
    enabled: bool = False
    target_keywords: list[str]
    max_title_length: int
    max_description_length: int
    default_tags: list[str] = Field(default_factory=list)


class YouTubeStepConfig(BaseModel):
    enabled: bool = False
    dry_run: bool = True
    default_visibility: str
    category_id: int
    default_tags: list[str] = Field(default_factory=list)


class PodcastStepConfig(BaseModel):
    enabled: bool = False
    feed_title: str = "金融ニュース解説ポッドキャスト"
    feed_description: str = "AI生成の日本経済・金融ニュース解説"
    feed_author: str = "2510 YouTuber AI"
    feed_url: str = "https://example.com/podcast"


class BuzzsproutStepConfig(BaseModel):
    enabled: bool = False
    podcast_id: str | None = None
    token_key: str = "buzzsprout_api_token"
    podcast_id_key: str = "buzzsprout_podcast_id"
    title_template: str = "金融ニュース解説 Episode {run_id}"
    publish_immediately: bool = True


class StepsConfig(BaseModel):
    news: NewsStepConfig
    script: ScriptStepConfig
    audio: AudioStepConfig
    subtitle: SubtitleStepConfig
    video: VideoStepConfig
    thumbnail: ThumbnailStepConfig
    metadata: MetadataStepConfig
    youtube: YouTubeStepConfig
    podcast: PodcastStepConfig
    buzzsprout: BuzzsproutStepConfig


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
    manager_script: str | None = None
    auto_start: bool = False


class TTSProvidersConfig(BaseModel):
    voicevox: VOICEVOXProviderConfig


class PerplexityNewsProviderConfig(BaseModel):
    enabled: bool = False
    model: str = "sonar"
    temperature: float = 0.2
    max_tokens: int = 2048


class NewsProvidersConfig(BaseModel):
    perplexity: PerplexityNewsProviderConfig | None = None


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


def load_prompts(prompts_path: str | Path | None = None) -> Dict:
    if prompts_path is None:
        prompts_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
    else:
        prompts_path = Path(prompts_path)

    with open(prompts_path) as f:
        return yaml.safe_load(f)
