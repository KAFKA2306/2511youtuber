import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.append(str(Path(__file__).resolve().parents[2]))

if TYPE_CHECKING:
    from src.steps.script import ScriptGenerator

aim_module = types.ModuleType("aim")


class _Run:
    def __init__(self, *args, **kwargs):
        pass


aim_module.Run = _Run
sys.modules.setdefault("aim", aim_module)


def _parser() -> "ScriptGenerator":
    from src.steps.script import ScriptGenerator

    parser = ScriptGenerator.__new__(ScriptGenerator)
    parser.speakers = {
        "analyst": "春日部つむぎ",
        "reporter": "ずんだもん",
        "narrator": "玄野武宏",
    }
    return parser


def test_parse_handles_colon_in_text() -> None:
    raw = """
segments:
  - speaker: 春日部つむぎ
    text: ずんだもん: その視点おもしろいね
  - speaker: ずんだもん
    text: つむぎちゃん: 詳しく教えてなのだ
"""
    result = _parser()._parse_and_validate(raw)
    assert [seg.text for seg in result.segments][:2] == [
        "ずんだもん: その視点おもしろいね",
        "つむぎちゃん: 詳しく教えてなのだ",
    ]


def test_parse_normalises_fullwidth_delimiters() -> None:
    raw = """
segments：
  - speaker： 春日部つむぎ
    text： 金利：驚きのサプライズ
"""
    result = _parser()._parse_and_validate(raw)
    assert result.segments[0].speaker == "春日部つむぎ"
    assert ":" in result.segments[0].text
    assert "金利" in result.segments[0].text


def test_parse_recovers_from_plain_dialogue() -> None:
    raw = """
春日部つむぎ: 今夜の銅市況は荒れてるよ
ずんだもん: どう影響が出るのだ？
玄野武宏: 市場の揺らぎを整理します
"""
    result = _parser()._parse_and_validate(raw)
    assert [seg.speaker for seg in result.segments] == [
        "春日部つむぎ",
        "ずんだもん",
        "玄野武宏",
    ]
