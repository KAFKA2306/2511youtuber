from __future__ import annotations

from pathlib import Path
from typing import Annotated, Dict, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.utils.constants import DEFAULT_COOLDOWN_HOURS, DEFAULT_FETCH_COUNT, QUERY_BUCKETS
from src.utils.secrets import load_secret_values


class WorkflowConfig(BaseModel):
    default_run_dir: str
    checkpoint_enabled: bool


class NewsStepConfig(BaseModel):
    query_buckets: Dict[str, str] = Field(default_factory=lambda: QUERY_BUCKETS)
    bucket_schedule: str | None = None  # Optional: specific bucket to force
    fetch_count: int = DEFAULT_FETCH_COUNT
    final_count: int = 3
    cooldown_hours: int = DEFAULT_COOLDOWN_HOURS
    # Legacy/Deprecated
    count: int = 3
    query: str | None = None
    recent_topics_runs: int = 0
    recent_topics_max_chars: int = 0
    recent_topics_min_token_length: int = 2
    recent_topics_stopwords: list[str] = Field(default_factory=list)


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


class VideoOverlayOffsetConfig(BaseModel):
    top: int | None = None
    right: int | None = None
    bottom: int | None = None
    left: int | None = None


def default_tsumugi_offset() -> VideoOverlayOffsetConfig:
    return VideoOverlayOffsetConfig(right=20, bottom=0)


class VideoOverlayConfig(BaseModel):
    type: Literal["overlay"] = "overlay"
    enabled: bool = True
    image_path: str
    anchor: str = "bottom_right"
    height_ratio: float | None = None
    width_ratio: float | None = None
    height: int | None = None
    width: int | None = None
    offset: VideoOverlayOffsetConfig | None = None


class MultiOverlayItemConfig(BaseModel):
    enabled: bool = True
    image_path: str
    anchor: str = "bottom_right"
    height_ratio: float | None = None
    width_ratio: float | None = None
    height: int | None = None
    width: int | None = None
    offset: VideoOverlayOffsetConfig | None = None


class MultiOverlayEffectConfig(BaseModel):
    type: Literal["multi_overlay"] = "multi_overlay"
    enabled: bool = True
    overlays: list[VideoOverlayConfig | MultiOverlayItemConfig] = Field(default_factory=list)


class TsumugiOverlayConfig(BaseModel):
    type: Literal["tsumugi_overlay"] = "tsumugi_overlay"
    enabled: bool = True
    image_path: str = "assets/春日部つむぎ立ち絵公式_v2.0/春日部つむぎ立ち絵公式_v1.1.1.png"
    anchor: str = "bottom_right"
    height_ratio: float | None = 0.85
    width_ratio: float | None = None
    height: int | None = None
    width: int | None = None
    offset: VideoOverlayOffsetConfig = Field(default_factory=default_tsumugi_offset)


class KenBurnsEffectConfig(BaseModel):
    type: Literal["ken_burns"] = "ken_burns"
    enabled: bool = True
    zoom_speed: float = 0.0015
    max_zoom: float = 1.2
    hold_frame_factor: float = 1.0
    pan_mode: str = "center"


VideoEffectConfig = Annotated[
    Union[
        KenBurnsEffectConfig,
        VideoOverlayConfig,
        TsumugiOverlayConfig,
        MultiOverlayEffectConfig,
    ],
    Field(discriminator="type"),
]


class VideoSubtitleStyleConfig(BaseModel):
    font_path: str | None = None
    font_name: str | None = None
    font_size: int | None = None
    primary_colour: str | None = None
    outline_colour: str | None = None
    outline: int | None = None
    shadow: int | None = None
    bold: int | None = None
    italic: int | None = None
    alignment: int | None = None
    margin_l: int | None = None
    margin_r: int | None = None
    margin_v: int | None = None
    model_config = ConfigDict(extra="allow")


class VideoIntroThumbnailClipConfig(BaseModel):
    enabled: bool = False
    duration_seconds: float = 0.0
    source_key: str = "generate_thumbnail"


class VideoIntroOutroConfig(BaseModel):
    enabled: bool = False
    intro_path: str | None = None
    outro_path: str | None = None
    twitter_outro_path: str | None = None
    thumbnail_clip: VideoIntroThumbnailClipConfig | None = None


class VideoThumbnailFlashConfig(BaseModel):
    enabled: bool = False
    duration_seconds: float = 0.0
    source_key: str = "generate_thumbnail"


class VideoStepConfig(BaseModel):
    resolution: str
    fps: int
    codec: str | None = None
    preset: str | None = None
    crf: int | None = None
    encoder_options: Dict[str, str | int | float] = Field(default_factory=dict)
    encoder_global_args: list[str] = Field(default_factory=list)
    effects: list[VideoEffectConfig] = Field(default_factory=list)
    subtitles: VideoSubtitleStyleConfig | None = None
    intro_outro: VideoIntroOutroConfig | None = None
    thumbnail_overlay: VideoThumbnailFlashConfig | None = None


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
    padding: int = 80
    max_lines: int = 3
    max_chars_per_line: int = 12
    title_font_size: int = 96
    subtitle_font_size: int = 56
    font_path: str | None = None
    overlays: list[ThumbnailOverlayConfig] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class SceneGeneratorStepConfig(BaseModel):
    enabled: bool = False
    images_per_video: int = 4
    variants_per_type: int = 2
    width: int = 1280
    height: int = 720
    num_steps: int = 9
    scene_duration_seconds: int = 30
    model_path: str = "external/hf-cache-hub/models/Z-Image-Turbo"
    device: str = "cuda"


class AIThumbnailStepConfig(BaseModel):
    enabled: bool = False
    width: int = 1920
    height: int = 1080
    num_steps: int = 6
    text_overlay_enabled: bool = True


class MetadataStepConfig(BaseModel):
    enabled: bool = False
    use_llm: bool = True
    llm_model: str | None = None
    fallback_llm_model: str | None = None
    llm_temperature: float | None = None
    llm_max_tokens: int | None = None
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


class TwitterStepConfig(BaseModel):
    enabled: bool = False
    dry_run: bool = True
    clip_duration_seconds: int = 60
    start_offset_seconds: int = 0


class LinkedInStepConfig(BaseModel):
    enabled: bool = False
    dry_run: bool = True


class HatenaStepConfig(BaseModel):
    enabled: bool = False
    dry_run: bool = True


class PodcastStepConfig(BaseModel):
    enabled: bool = False
    feed_title: str
    feed_description: str
    feed_author: str
    feed_url: str


class BuzzsproutStepConfig(BaseModel):
    enabled: bool = False
    podcast_id: str | None = None
    token_key: str = "buzzsprout_api_token"
    podcast_id_key: str = "buzzsprout_podcast_id"
    title_template: str = "金融ニュース解説 Episode {run_id}"
    publish_immediately: bool = False


class StepsConfig(BaseModel):
    news: NewsStepConfig
    script: ScriptStepConfig
    audio: AudioStepConfig
    subtitle: SubtitleStepConfig
    video: VideoStepConfig
    thumbnail: ThumbnailStepConfig
    thumbnail_ai: AIThumbnailStepConfig
    scene_generator: SceneGeneratorStepConfig
    metadata: MetadataStepConfig
    youtube: YouTubeStepConfig
    twitter: TwitterStepConfig
    linkedin: LinkedInStepConfig
    hatena: HatenaStepConfig
    podcast: PodcastStepConfig
    buzzsprout: BuzzsproutStepConfig


class GeminiLLMConfig(BaseModel):
    model: str
    fallback_model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 32768


class LLMProvidersConfig(BaseModel):
    gemini: GeminiLLMConfig


class VoicevoxTTSConfig(BaseModel):
    enabled: bool = False
    url: str
    manager_script: str
    auto_start: bool = False
    speakers: Dict[str, int]
    voice_parameters: Dict[str, Dict] = Field(default_factory=dict)


class TTSProvidersConfig(BaseModel):
    voicevox: VoicevoxTTSConfig


class PerplexityNewsConfig(BaseModel):
    enabled: bool = False
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048
    search_recency_filter: str = "week"


class NewsProvidersConfig(BaseModel):
    perplexity: PerplexityNewsConfig


class ProvidersConfig(BaseModel):
    llm: LLMProvidersConfig
    tts: TTSProvidersConfig
    news: NewsProvidersConfig


class ToneConfig(BaseModel):
    enabled: bool = True
    title_forbidden_terms: list[str] = Field(default_factory=list)
    description_forbidden_terms: list[str] = Field(default_factory=list)
    replacements: Dict[str, str] = Field(default_factory=dict)
    description_footer: str = ""
    failure_transparency_marker: str = ""


class LoggingConfig(BaseModel):
    level: str
    format: str


class AutomationServiceConfig(BaseModel):
    name: str
    command: str
    healthcheck: str | None = None
    required: bool = True
    timeout_seconds: int = 30


class AutomationScheduleConfig(BaseModel):
    name: str
    command: str
    cron: str
    enabled: bool = True


class AutomationConfig(BaseModel):
    enabled: bool = False
    venv_activate: str = ".venv/bin/activate"
    log_dir: str = "logs/automation"
    services: list[AutomationServiceConfig] = Field(default_factory=list)
    schedules: list[AutomationScheduleConfig] = Field(default_factory=list)


class Config(BaseModel):
    workflow: WorkflowConfig
    steps: StepsConfig
    providers: ProvidersConfig
    tone: ToneConfig = Field(default_factory=ToneConfig)
    logging: LoggingConfig
    automation: AutomationConfig = Field(default_factory=AutomationConfig)

    @classmethod
    def load(cls, path: Path | str = "config/default.yaml") -> "Config":
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)


def load_prompts(path: Path | str = "config/prompts.yaml") -> Dict:
    path = Path(path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_secrets() -> Dict[str, str]:
    return load_secret_values()
