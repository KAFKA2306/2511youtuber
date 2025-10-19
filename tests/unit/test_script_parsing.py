import sys
import types
from pathlib import Path

aim_module = types.ModuleType("aim")


class _Run:
    def __init__(self, *args, **kwargs):
        pass


aim_module.Run = _Run
sys.modules.setdefault("aim", aim_module)

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.steps.script import ScriptGenerator


def _parser() -> ScriptGenerator:
    return ScriptGenerator.__new__(ScriptGenerator)


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
