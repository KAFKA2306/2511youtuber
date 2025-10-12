from datetime import datetime
from typing import List

from pydantic import BaseModel, Field
from src.core.state import WorkflowResult, WorkflowState


class NewsItem(BaseModel):
    title: str
    summary: str
    url: str = ""
    published_at: datetime = Field(default_factory=datetime.now)


class ScriptSegment(BaseModel):
    speaker: str
    text: str


class Script(BaseModel):
    segments: List[ScriptSegment]
    total_duration_estimate: float = 0.0
