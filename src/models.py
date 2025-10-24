from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Mapping

from pydantic import BaseModel, Field


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
    recent_topics_note: str = ""
    next_theme_note: str = ""


@dataclass
class ScriptContextNotes:
    recent_topics_note: str = ""
    next_theme_note: str = ""

    def to_mapping(self) -> dict[str, str]:
        return {"recent_topics_note": self.recent_topics_note, "next_theme_note": self.next_theme_note}

    def merge_missing(self, other: "ScriptContextNotes") -> "ScriptContextNotes":
        if not other:
            return self
        return ScriptContextNotes(
            recent_topics_note=self.recent_topics_note or other.recent_topics_note,
            next_theme_note=self.next_theme_note or other.next_theme_note,
        )

    def is_empty(self) -> bool:
        return not (self.recent_topics_note or self.next_theme_note)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "ScriptContextNotes":
        if not data:
            return cls()
        recent = str(data.get("recent_topics_note") or data.get("recent_topic_note") or "").strip()
        next_note = str(data.get("next_theme_note") or "").strip()
        return cls(recent_topics_note=recent, next_theme_note=next_note)
