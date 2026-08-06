import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Mapping

from pydantic import BaseModel, Field


_CONTEXT_PLACEHOLDERS = {
    "金融ニュース速報：日本経済の最新動向",
    "市場は急激な変動を見せています",
    "今日のテーマから派生する新しい視点や発見の余地",
    "直近テーマ情報なし",
}


def sanitize_context_note(value: Any) -> str:
    """Return an empty string for known generated placeholders.

    Context notes are persisted and reused by later runs, so accepting a canned
    fallback once would otherwise amplify it indefinitely. Whitespace and common
    punctuation are normalized before exact placeholder comparison; real titles
    and summaries are preserved unchanged apart from outer whitespace.
    """

    text = str(value or "").strip()
    if not text:
        return ""
    normalized = re.sub(r"\s+", "", text).rstrip("。.!！")
    placeholders = {re.sub(r"\s+", "", item).rstrip("。.!！") for item in _CONTEXT_PLACEHOLDERS}
    if normalized in placeholders:
        return ""
    return text


class NewsItem(BaseModel):
    title: str
    summary: str
    url: str = ""
    published_at: datetime = Field(default_factory=datetime.now)


class ScriptSegment(BaseModel):
    speaker: str
    text: str


class SocialPlatformContent(BaseModel):
    post_text: str
    image_prompt: str = ""
    slide_content: List[str] = Field(default_factory=list)


class SocialContent(BaseModel):
    twitter: SocialPlatformContent
    linkedin: SocialPlatformContent
    hatena_blog: SocialPlatformContent


class Script(BaseModel):
    segments: List[ScriptSegment]
    social_content: SocialContent | None = None
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
        recent = sanitize_context_note(data.get("recent_topics_note") or data.get("recent_topic_note"))
        next_note = sanitize_context_note(data.get("next_theme_note"))
        return cls(recent_topics_note=recent, next_theme_note=next_note)
