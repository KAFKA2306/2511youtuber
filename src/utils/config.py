from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel
import yaml
from dotenv import load_dotenv

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


class VideoStepConfig(BaseModel):
    resolution: str
    fps: int
    codec: str
    preset: str
    crf: int


class StepsConfig(BaseModel):
    news: NewsStepConfig
    script: ScriptStepConfig
    audio: AudioStepConfig
    video: VideoStepConfig


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


class DummyNewsProviderConfig(BaseModel):
    enabled: bool


class NewsProvidersConfig(BaseModel):
    dummy: DummyNewsProviderConfig


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

        load_dotenv(Path(__file__).parent.parent.parent / "config" / ".env")

        return cls(**data)

    def get_gemini_api_keys(self) -> list[str]:
        return load_secret_values("GEMINI_API_KEY")
